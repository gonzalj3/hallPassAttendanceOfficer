from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.models import School, Student
from tests.factories import SchoolFactory, StudentFactory

pytestmark = pytest.mark.integration


async def test_school_roundtrip(async_session: AsyncSession) -> None:
    school = SchoolFactory.build(name="Pflugerville HS", district="PfISD")
    async_session.add(school)
    await async_session.flush()

    fetched = (
        await async_session.execute(select(School).where(School.id == school.id))
    ).scalar_one()
    assert fetched.name == "Pflugerville HS"
    assert fetched.district == "PfISD"
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


async def test_student_roundtrip(async_session: AsyncSession) -> None:
    school = SchoolFactory.build(name="Lone Star HS")
    async_session.add(school)
    await async_session.flush()

    student = StudentFactory.build(
        school_id=school.id,
        student_number="S001",
        grade_level="10",
        first_name="Alice",
        last_name="Garcia",
        enrolled_at=date(2025, 8, 15),
    )
    async_session.add(student)
    await async_session.flush()

    fetched = (
        await async_session.execute(select(Student).where(Student.id == student.id))
    ).scalar_one()
    assert fetched.first_name == "Alice"
    assert fetched.school_id == school.id
    assert fetched.grade_level == "10"


async def test_student_number_unique_per_school(async_session: AsyncSession) -> None:
    school = SchoolFactory.build()
    async_session.add(school)
    await async_session.flush()

    s1 = StudentFactory.build(school_id=school.id, student_number="DUP")
    s2 = StudentFactory.build(school_id=school.id, student_number="DUP")
    async_session.add_all([s1, s2])

    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_same_student_number_allowed_across_schools(
    async_session: AsyncSession,
) -> None:
    school_a = SchoolFactory.build(name="A")
    school_b = SchoolFactory.build(name="B")
    async_session.add_all([school_a, school_b])
    await async_session.flush()

    s_a = StudentFactory.build(school_id=school_a.id, student_number="SHARED")
    s_b = StudentFactory.build(school_id=school_b.id, student_number="SHARED")
    async_session.add_all([s_a, s_b])
    await async_session.flush()  # should not raise


async def test_invalid_grade_level_rejected(async_session: AsyncSession) -> None:
    school = SchoolFactory.build()
    async_session.add(school)
    await async_session.flush()

    bad = StudentFactory.build(school_id=school.id, grade_level="13")
    async_session.add(bad)

    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_kindergarten_grade_level_accepted(async_session: AsyncSession) -> None:
    school = SchoolFactory.build()
    async_session.add(school)
    await async_session.flush()

    kindergartener = StudentFactory.build(
        school_id=school.id, student_number="K001", grade_level="K"
    )
    async_session.add(kindergartener)
    await async_session.flush()  # should not raise


async def test_foreign_key_enforced(async_session: AsyncSession) -> None:
    orphan = StudentFactory.build(school_id=uuid4(), student_number="ORPHAN")
    async_session.add(orphan)

    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_school_with_students_relationship(async_session: AsyncSession) -> None:
    school = SchoolFactory.build(name="Relationship Test HS")
    async_session.add(school)
    await async_session.flush()

    students = [
        StudentFactory.build(school_id=school.id, student_number=f"S{i:03d}") for i in range(3)
    ]
    async_session.add_all(students)
    await async_session.flush()

    refreshed = (
        await async_session.execute(select(School).where(School.id == school.id))
    ).scalar_one()
    await async_session.refresh(refreshed, attribute_names=["students"])
    assert len(refreshed.students) == 3
