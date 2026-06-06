"""Seed the demo data the frontend needs to render anything on first run.

Idempotent: if a school named ``Lincoln High`` already exists, the seed
exits immediately so re-runs are a no-op (you can also tear the DB down
with ``docker compose down -v`` to start over).

Usage:
    python -m lizzie.cli.seed
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, time, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lizzie.config import get_settings
from lizzie.db import make_engine, make_session_factory
from lizzie.models import (
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
TEACHER_EMAIL = "ms.rivera@lincoln.edu"
TEACHER_FIRST = "Ms."
TEACHER_LAST = "Rivera"
ADMIN_EMAIL = "dr.chen@lincoln.edu"
ADMIN_FIRST = "Dr."
ADMIN_LAST = "Chen"

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
    school = (
        await db.execute(select(School).where(School.name == SCHOOL_NAME))
    ).scalar_one_or_none()

    today = date.today()

    if school is None:
        school = School(name=SCHOOL_NAME, district=SCHOOL_DISTRICT)
        db.add(school)
        await db.flush()
    elif school.district is None:
        school.district = SCHOOL_DISTRICT

    teacher = (
        await db.execute(select(User).where(User.email == TEACHER_EMAIL))
    ).scalar_one_or_none()
    if teacher is None:
        teacher = User(
            school_id=school.id,
            email=TEACHER_EMAIL,
            role="TEACHER",
            first_name=TEACHER_FIRST,
            last_name=TEACHER_LAST,
        )
        db.add(teacher)
        await db.flush()

    admin = (await db.execute(select(User).where(User.email == ADMIN_EMAIL))).scalar_one_or_none()
    if admin is None:
        admin = User(
            school_id=school.id,
            email=ADMIN_EMAIL,
            role="ADMIN",
            first_name=ADMIN_FIRST,
            last_name=ADMIN_LAST,
        )
        db.add(admin)
        await db.flush()

    students: list[Student] = []
    for idx, (first, last) in enumerate(DEMO_STUDENTS):
        student_number = f"S{idx + 1:03d}"
        student = (
            await db.execute(
                select(Student).where(
                    Student.school_id == school.id,
                    Student.student_number == student_number,
                )
            )
        ).scalar_one_or_none()
        if student is None:
            student = Student(
                school_id=school.id,
                student_number=student_number,
                grade_level="10",
                first_name=first,
                last_name=last,
                enrolled_at=today - timedelta(days=60),
            )
            db.add(student)
            await db.flush()
        students.append(student)

    classes: list[Class] = []
    for spec in DEMO_CLASSES:
        cls = (
            await db.execute(
                select(Class).where(
                    Class.school_id == school.id,
                    Class.period == str(spec["period"]),
                    Class.name == str(spec["name"]),
                )
            )
        ).scalar_one_or_none()
        if cls is None:
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
        classes.append(cls)

        session = (
            await db.execute(
                select(ClassSession).where(
                    ClassSession.class_id == cls.id,
                    ClassSession.date == today,
                )
            )
        ).scalar_one_or_none()
        if session is None:
            db.add(
                ClassSession(
                    class_id=cls.id,
                    date=today,
                    scheduled_start=spec["start"],
                    scheduled_end=spec["end"],
                )
            )

        for student in students:
            enrollment = (
                await db.execute(
                    select(ClassEnrollment).where(
                        ClassEnrollment.class_id == cls.id,
                        ClassEnrollment.student_id == student.id,
                    )
                )
            ).scalar_one_or_none()
            if enrollment is None:
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
        "seed: ensured school=%s teacher=%s classes=%d students=%d sessions_date=%s",
        school.id,
        teacher.id,
        len(classes),
        len(students),
        today.isoformat(),
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
