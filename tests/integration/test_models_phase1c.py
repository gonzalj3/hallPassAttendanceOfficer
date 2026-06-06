from datetime import date, time
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lizzie.models import Class, ClassEnrollment, ClassSession, User
from tests.factories import (
    ClassEnrollmentFactory,
    ClassFactory,
    ClassSessionFactory,
    SchoolFactory,
    StudentFactory,
    UserFactory,
)

pytestmark = pytest.mark.integration


# ---------- User ----------


async def test_user_roundtrip(async_session: AsyncSession) -> None:
    school = SchoolFactory.build()
    async_session.add(school)
    await async_session.flush()

    user = UserFactory.build(
        school_id=school.id,
        email="ms.garcia@school.edu",
        role="TEACHER",
        first_name="Maria",
        last_name="Garcia",
    )
    async_session.add(user)
    await async_session.flush()

    fetched = (await async_session.execute(select(User).where(User.id == user.id))).scalar_one()
    assert fetched.email == "ms.garcia@school.edu"
    assert fetched.role == "TEACHER"
    assert fetched.last_name == "Garcia"


async def test_user_email_unique(async_session: AsyncSession) -> None:
    school = SchoolFactory.build()
    async_session.add(school)
    await async_session.flush()

    a = UserFactory.build(school_id=school.id, email="dup@school.edu")
    b = UserFactory.build(school_id=school.id, email="dup@school.edu")
    async_session.add_all([a, b])

    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_invalid_user_role_rejected(async_session: AsyncSession) -> None:
    school = SchoolFactory.build()
    async_session.add(school)
    await async_session.flush()

    bad = UserFactory.build(school_id=school.id, role="JANITOR")
    async_session.add(bad)
    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_admin_role_accepted(async_session: AsyncSession) -> None:
    school = SchoolFactory.build()
    async_session.add(school)
    await async_session.flush()

    admin = UserFactory.build(school_id=school.id, role="ADMIN")
    async_session.add(admin)
    await async_session.flush()  # should not raise


# ---------- Class ----------


async def test_class_roundtrip_with_teacher(async_session: AsyncSession) -> None:
    school = SchoolFactory.build()
    async_session.add(school)
    await async_session.flush()
    teacher = UserFactory.build(school_id=school.id, role="TEACHER")
    async_session.add(teacher)
    await async_session.flush()

    klass = ClassFactory.build(
        school_id=school.id,
        teacher_id=teacher.id,
        name="Algebra II",
        period="3",
    )
    async_session.add(klass)
    await async_session.flush()

    fetched = (await async_session.execute(select(Class).where(Class.id == klass.id))).scalar_one()
    assert fetched.name == "Algebra II"
    assert fetched.teacher_id == teacher.id


async def test_class_requires_existing_teacher(async_session: AsyncSession) -> None:
    school = SchoolFactory.build()
    async_session.add(school)
    await async_session.flush()

    orphan = ClassFactory.build(school_id=school.id, teacher_id=uuid4())
    async_session.add(orphan)
    with pytest.raises(IntegrityError):
        await async_session.flush()


# ---------- ClassEnrollment ----------


async def test_enrollment_roundtrip(async_session: AsyncSession) -> None:
    school = SchoolFactory.build()
    async_session.add(school)
    await async_session.flush()
    teacher = UserFactory.build(school_id=school.id)
    student = StudentFactory.build(school_id=school.id)
    async_session.add_all([teacher, student])
    await async_session.flush()
    klass = ClassFactory.build(school_id=school.id, teacher_id=teacher.id)
    async_session.add(klass)
    await async_session.flush()

    enrollment = ClassEnrollmentFactory.build(class_id=klass.id, student_id=student.id)
    async_session.add(enrollment)
    await async_session.flush()

    fetched = (
        await async_session.execute(
            select(ClassEnrollment).where(ClassEnrollment.id == enrollment.id)
        )
    ).scalar_one()
    assert fetched.class_id == klass.id
    assert fetched.student_id == student.id


async def test_enrollment_unique_per_class_student(async_session: AsyncSession) -> None:
    school = SchoolFactory.build()
    async_session.add(school)
    await async_session.flush()
    teacher = UserFactory.build(school_id=school.id)
    student = StudentFactory.build(school_id=school.id)
    async_session.add_all([teacher, student])
    await async_session.flush()
    klass = ClassFactory.build(school_id=school.id, teacher_id=teacher.id)
    async_session.add(klass)
    await async_session.flush()

    e1 = ClassEnrollmentFactory.build(class_id=klass.id, student_id=student.id)
    e2 = ClassEnrollmentFactory.build(class_id=klass.id, student_id=student.id)
    async_session.add_all([e1, e2])

    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_student_can_enroll_in_multiple_classes(async_session: AsyncSession) -> None:
    school = SchoolFactory.build()
    async_session.add(school)
    await async_session.flush()
    teacher = UserFactory.build(school_id=school.id)
    student = StudentFactory.build(school_id=school.id)
    async_session.add_all([teacher, student])
    await async_session.flush()
    class_a = ClassFactory.build(school_id=school.id, teacher_id=teacher.id, period="1")
    class_b = ClassFactory.build(school_id=school.id, teacher_id=teacher.id, period="2")
    async_session.add_all([class_a, class_b])
    await async_session.flush()

    e_a = ClassEnrollmentFactory.build(class_id=class_a.id, student_id=student.id)
    e_b = ClassEnrollmentFactory.build(class_id=class_b.id, student_id=student.id)
    async_session.add_all([e_a, e_b])
    await async_session.flush()  # should not raise


# ---------- ClassSession ----------


async def test_class_session_roundtrip(async_session: AsyncSession) -> None:
    school = SchoolFactory.build()
    async_session.add(school)
    await async_session.flush()
    teacher = UserFactory.build(school_id=school.id)
    async_session.add(teacher)
    await async_session.flush()
    klass = ClassFactory.build(school_id=school.id, teacher_id=teacher.id)
    async_session.add(klass)
    await async_session.flush()

    cs = ClassSessionFactory.build(
        class_id=klass.id,
        date=date(2025, 9, 4),
        scheduled_start=time(9, 0),
        scheduled_end=time(9, 50),
    )
    async_session.add(cs)
    await async_session.flush()

    fetched = (
        await async_session.execute(select(ClassSession).where(ClassSession.id == cs.id))
    ).scalar_one()
    assert fetched.date == date(2025, 9, 4)
    assert fetched.scheduled_start == time(9, 0)


async def test_class_session_unique_per_class_date(async_session: AsyncSession) -> None:
    school = SchoolFactory.build()
    async_session.add(school)
    await async_session.flush()
    teacher = UserFactory.build(school_id=school.id)
    async_session.add(teacher)
    await async_session.flush()
    klass = ClassFactory.build(school_id=school.id, teacher_id=teacher.id)
    async_session.add(klass)
    await async_session.flush()

    a = ClassSessionFactory.build(class_id=klass.id, date=date(2025, 9, 4))
    b = ClassSessionFactory.build(class_id=klass.id, date=date(2025, 9, 4))
    async_session.add_all([a, b])

    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_same_class_can_have_multiple_dates(async_session: AsyncSession) -> None:
    school = SchoolFactory.build()
    async_session.add(school)
    await async_session.flush()
    teacher = UserFactory.build(school_id=school.id)
    async_session.add(teacher)
    await async_session.flush()
    klass = ClassFactory.build(school_id=school.id, teacher_id=teacher.id)
    async_session.add(klass)
    await async_session.flush()

    sessions = [
        ClassSessionFactory.build(class_id=klass.id, date=date(2025, 9, day))
        for day in (4, 5, 8, 9, 10)
    ]
    async_session.add_all(sessions)
    await async_session.flush()  # should not raise
