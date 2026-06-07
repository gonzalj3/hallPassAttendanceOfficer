from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lizzie.cli.seed import SCHOOL_NAME, TEACHER_EMAIL, seed
from lizzie.models import Class, ClassEnrollment, ClassSession, School, Student, User

pytestmark = pytest.mark.integration


async def test_seed_adds_today_sessions_when_demo_school_already_exists(
    async_session: AsyncSession,
) -> None:
    today_utc = datetime.now(tz=UTC).date()
    yesterday = today_utc - timedelta(days=1)

    school = School(name=SCHOOL_NAME)
    async_session.add(school)
    await async_session.flush()

    teacher = User(
        school_id=school.id,
        email=TEACHER_EMAIL,
        role="TEACHER",
        first_name="Demo",
        last_name="Teacher",
    )
    async_session.add(teacher)
    await async_session.flush()

    student = Student(
        school_id=school.id,
        student_number="S001",
        grade_level="10",
        first_name="Sarah",
        last_name="Jenkins",
        enrolled_at=yesterday,
    )
    async_session.add(student)
    await async_session.flush()

    cls = Class(
        school_id=school.id,
        teacher_id=teacher.id,
        name="Algebra I",
        subject="Mathematics",
        period="Period 1",
        room="101",
    )
    async_session.add(cls)
    await async_session.flush()

    async_session.add(
        ClassEnrollment(class_id=cls.id, student_id=student.id, enrolled_at=yesterday)
    )
    async_session.add(
        ClassSession(
            class_id=cls.id,
            date=yesterday,
            scheduled_start=time(8, 30),
            scheduled_end=time(9, 20),
        )
    )
    await async_session.flush()

    await seed(async_session)

    today_sessions = (
        (await async_session.execute(select(ClassSession).where(ClassSession.date == today_utc)))
        .scalars()
        .all()
    )

    assert len(today_sessions) == 3
