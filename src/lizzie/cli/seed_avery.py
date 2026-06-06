"""Seed a demo student "Avery Johnson" with 14 hall passes in the last 10 days.

Idempotent: re-running is safe. If Avery already exists with >= 14 passes
in the trailing 10-day window, the script reports state and exits without
writing.

Used for the rich-student-profile demo path so the agent / dashboard has
someone with a substantial hall-pass history to talk about.

Usage:
    python -m lizzie.cli.seed_avery
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lizzie.cli.seed import SCHOOL_NAME
from lizzie.config import get_settings
from lizzie.db import make_engine, make_session_factory
from lizzie.models import (
    Class,
    ClassEnrollment,
    ClassSession,
    HallPass,
    School,
    Student,
)

logger = logging.getLogger(__name__)

PASS_TARGET = 14
WINDOW_DAYS = 10
DESTINATIONS: tuple[str, ...] = ("RESTROOM", "NURSE", "OFFICE", "HALLWAY", "CLASSROOM")


async def _ensure_avery(db: AsyncSession, school_id: UUID) -> Student:
    existing = (
        await db.execute(
            select(Student).where(
                Student.school_id == school_id,
                Student.first_name == "Avery",
                Student.last_name == "Johnson",
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    # Pick the next free `S###` for this school.
    numbers = (
        (await db.execute(select(Student.student_number).where(Student.school_id == school_id)))
        .scalars()
        .all()
    )
    max_n = max(
        (int(n[1:]) for n in numbers if n.startswith("S") and n[1:].isdigit()),
        default=0,
    )
    avery = Student(
        school_id=school_id,
        student_number=f"S{max_n + 1:03d}",
        grade_level="10",
        first_name="Avery",
        last_name="Johnson",
        enrolled_at=date.today() - timedelta(days=60),
    )
    db.add(avery)
    await db.flush()
    return avery


async def _enroll_in_classes(db: AsyncSession, *, student_id: UUID, classes: list[Class]) -> None:
    already = set(
        (
            await db.execute(
                select(ClassEnrollment.class_id).where(ClassEnrollment.student_id == student_id)
            )
        )
        .scalars()
        .all()
    )
    for cls in classes:
        if cls.id in already:
            continue
        db.add(
            ClassEnrollment(
                class_id=cls.id,
                student_id=student_id,
                enrolled_at=date.today() - timedelta(days=60),
            )
        )
    await db.flush()


async def _ensure_daily_sessions(
    db: AsyncSession, anchor_class: Class, days: int
) -> dict[date, ClassSession]:
    """Make sure there's a ClassSession on each of the last `days` days for
    `anchor_class`. Creates missing ones; returns a date->session map."""
    out: dict[date, ClassSession] = {}
    for offset in range(days):
        d = date.today() - timedelta(days=offset)
        sess = (
            await db.execute(
                select(ClassSession).where(
                    ClassSession.class_id == anchor_class.id, ClassSession.date == d
                )
            )
        ).scalar_one_or_none()
        if sess is None:
            sess = ClassSession(
                class_id=anchor_class.id,
                date=d,
                scheduled_start=time(8, 30),
                scheduled_end=time(9, 20),
            )
            db.add(sess)
            await db.flush()
        out[d] = sess
    return out


async def seed_avery(db: AsyncSession) -> dict[str, object]:
    school = (
        await db.execute(select(School).where(School.name == SCHOOL_NAME))
    ).scalar_one_or_none()
    if school is None:
        raise RuntimeError(
            f"School {SCHOOL_NAME!r} not found. Run `python -m lizzie.cli.seed` first."
        )

    classes = list(
        (await db.execute(select(Class).where(Class.school_id == school.id))).scalars().all()
    )
    if not classes:
        raise RuntimeError("No classes found. Run `python -m lizzie.cli.seed` first.")

    avery = await _ensure_avery(db, school.id)
    await _enroll_in_classes(db, student_id=avery.id, classes=classes)

    cutoff = datetime.now(UTC) - timedelta(days=WINDOW_DAYS)
    existing_pass_count = len(
        (
            await db.execute(
                select(HallPass).where(
                    HallPass.student_id == avery.id,
                    HallPass.checked_out_at >= cutoff,
                )
            )
        )
        .scalars()
        .all()
    )
    if existing_pass_count >= PASS_TARGET:
        logger.info(
            "avery: %d passes already in last %d days, no-op",
            existing_pass_count,
            WINDOW_DAYS,
        )
        await db.commit()
        return {
            "student_id": avery.id,
            "student_number": avery.student_number,
            "passes_existing": existing_pass_count,
            "passes_added": 0,
        }

    anchor = next((c for c in classes if "Algebra" in c.name), classes[0])
    sessions_by_date = await _ensure_daily_sessions(db, anchor, WINDOW_DAYS)

    to_create = PASS_TARGET - existing_pass_count
    # Spread roughly evenly — first `to_create` indices map to days 0..9 cycling.
    for i in range(to_create):
        days_ago = i % WINDOW_DAYS
        d = date.today() - timedelta(days=days_ago)
        sess = sessions_by_date[d]
        # Walk the day in 30-min steps so multiple passes per day don't collide
        # awkwardly in the timeline.
        slot = i // WINDOW_DAYS
        checked_out = datetime.combine(
            d,
            time(hour=9 + slot, minute=15 + (i * 7) % 30),
            tzinfo=UTC,
        )
        # Vary durations 4-12 min so the data looks realistic and stays under
        # the 15-min RESTROOM threshold (everything ends RETURNED, not FLAGGED).
        duration_min = 4 + (i % 9)
        db.add(
            HallPass(
                student_id=avery.id,
                originating_class_session_id=sess.id,
                destination=DESTINATIONS[i % len(DESTINATIONS)],
                checked_out_at=checked_out,
                expected_return_at=checked_out + timedelta(minutes=15),
                checked_in_at=checked_out + timedelta(minutes=duration_min),
                status="RETURNED",
                issued_by=anchor.teacher_id,
            )
        )

    await db.commit()
    logger.info(
        "avery: created %d passes for student %s (S/N %s)",
        to_create,
        avery.id,
        avery.student_number,
    )
    return {
        "student_id": avery.id,
        "student_number": avery.student_number,
        "passes_existing": existing_pass_count,
        "passes_added": to_create,
    }


async def _amain() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = get_settings()
    engine = make_engine(settings.database_url)
    factory = make_session_factory(engine)
    try:
        async with factory() as db:
            result = await seed_avery(db)
            print(result)
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
