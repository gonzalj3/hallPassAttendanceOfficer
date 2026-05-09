"""Seed the demo data the frontend needs to render anything on first run.

Idempotent: if a school named ``Lincoln High`` already exists, the seed
exits immediately so re-runs are a no-op (you can also tear the DB down
with ``docker compose down -v`` to start over).

Usage:
    python -m hpao.cli.seed
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, time, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.config import get_settings
from hpao.db import make_engine, make_session_factory
from hpao.models import (
    Class,
    ClassEnrollment,
    ClassSession,
    School,
    Student,
    User,
)

logger = logging.getLogger(__name__)

SCHOOL_NAME = "Lincoln High"
SCHOOL_DISTRICT = "Pflugerville ISD"
TEACHER_EMAIL = "demo.teacher@lincoln.edu"

# Mock classes the frontend already styles (Biology, Algebra, English).
# Times bracket the school day so the /api/sessions `type` heuristic puts
# whichever period is "now" into the suggested slot for a live demo.
DEMO_CLASSES: tuple[dict[str, object], ...] = (
    {
        "name": "Algebra I",
        "subject": "Mathematics",
        "period": "Period 1",
        "room": "101",
        "start": time(8, 30),
        "end": time(9, 20),
    },
    {
        "name": "English",
        "subject": "Language Arts",
        "period": "Period 2",
        "room": "115",
        "start": time(9, 25),
        "end": time(10, 15),
    },
    {
        "name": "Biology",
        "subject": "Science",
        "period": "Period 3",
        "room": "204",
        "start": time(10, 20),
        "end": time(11, 10),
    },
)

DEMO_STUDENTS: tuple[tuple[str, str], ...] = (
    ("Sarah", "Jenkins"),
    ("Liam", "Wilson"),
    ("Elena", "Rodriguez"),
    ("David", "Kim"),
    ("Jordan", "Smith"),
    ("Maya", "Patel"),
    ("Oliver", "Thompson"),
    ("Sophia", "Garcia"),
    ("Lucas", "Brown"),
    ("Isabella", "Martinez"),
    ("Marcus", "Chen"),
    ("Amara", "Okafor"),
)


async def seed(db: AsyncSession) -> dict[str, UUID]:
    existing = (
        await db.execute(select(School).where(School.name == SCHOOL_NAME))
    ).scalar_one_or_none()
    if existing is not None:
        logger.info("seed: %s already exists, no-op", SCHOOL_NAME)
        return {"school_id": existing.id}

    today = date.today()

    school = School(name=SCHOOL_NAME, district=SCHOOL_DISTRICT)
    db.add(school)
    await db.flush()

    teacher = User(
        school_id=school.id,
        email=TEACHER_EMAIL,
        role="TEACHER",
        first_name="Demo",
        last_name="Teacher",
    )
    db.add(teacher)
    await db.flush()

    students = [
        Student(
            school_id=school.id,
            student_number=f"S{idx + 1:03d}",
            grade_level="10",
            first_name=first,
            last_name=last,
            enrolled_at=today - timedelta(days=60),
        )
        for idx, (first, last) in enumerate(DEMO_STUDENTS)
    ]
    db.add_all(students)
    await db.flush()

    for spec in DEMO_CLASSES:
        cls = Class(
            school_id=school.id,
            teacher_id=teacher.id,
            name=str(spec["name"]),
            subject=str(spec["subject"]),
            period=str(spec["period"]),
            room=str(spec["room"]),
        )
        db.add(cls)
        await db.flush()

        session = ClassSession(
            class_id=cls.id,
            date=today,
            scheduled_start=spec["start"],
            scheduled_end=spec["end"],
        )
        db.add(session)

        # Every demo student is enrolled in every class — keeps the roster
        # full on each session for a more visually populated demo.
        for student in students:
            db.add(
                ClassEnrollment(
                    class_id=cls.id,
                    student_id=student.id,
                    enrolled_at=today - timedelta(days=60),
                )
            )

    await db.flush()
    await db.commit()
    logger.info(
        "seed: created school=%s teacher=%s classes=%d students=%d",
        school.id,
        teacher.id,
        len(DEMO_CLASSES),
        len(students),
    )
    return {"school_id": school.id, "teacher_id": teacher.id}


async def _amain() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = get_settings()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    try:
        async with session_factory() as session:
            await seed(session)
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
