"""Integration tests for Phase 2: attendance model + service.

Covers DB-level invariants (UNIQUE on (session, student), CHECK status,
CHECK source, FK enforcement) and service idempotency / list semantics
against real Postgres.
"""

from datetime import date, time
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.models import AttendanceRecord, ClassSession, Student, User
from hpao.services.attendance import (
    list_attendance_for_session,
    list_attendance_for_student,
    record_attendance,
)
from tests.factories import (
    AttendanceRecordFactory,
    ClassFactory,
    ClassSessionFactory,
    SchoolFactory,
    StudentFactory,
    UserFactory,
)

pytestmark = pytest.mark.integration


# ---------- Fixture helpers ----------


async def _scaffold_class(db: AsyncSession) -> tuple[User, Student, ClassSession]:
    """Create the FK chain attendance needs: school -> teacher + student -> class -> session."""
    school = SchoolFactory.build()
    db.add(school)
    await db.flush()
    teacher = UserFactory.build(school_id=school.id)
    student = StudentFactory.build(school_id=school.id)
    db.add_all([teacher, student])
    await db.flush()
    klass = ClassFactory.build(school_id=school.id, teacher_id=teacher.id)
    db.add(klass)
    await db.flush()
    cs = ClassSessionFactory.build(class_id=klass.id)
    db.add(cs)
    await db.flush()
    return teacher, student, cs


# ---------- Model-level (DB constraints) ----------


async def test_attendance_unique_per_session_student(async_session: AsyncSession) -> None:
    teacher, student, cs = await _scaffold_class(async_session)
    a = AttendanceRecordFactory.build(
        class_session_id=cs.id,
        student_id=student.id,
        recorded_by=teacher.id,
    )
    b = AttendanceRecordFactory.build(
        class_session_id=cs.id,
        student_id=student.id,
        recorded_by=teacher.id,
    )
    async_session.add_all([a, b])
    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_invalid_status_rejected_at_db(async_session: AsyncSession) -> None:
    teacher, student, cs = await _scaffold_class(async_session)
    bad = AttendanceRecordFactory.build(
        class_session_id=cs.id,
        student_id=student.id,
        status="HUNGRY",
        recorded_by=teacher.id,
    )
    async_session.add(bad)
    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_invalid_source_rejected_at_db(async_session: AsyncSession) -> None:
    teacher, student, cs = await _scaffold_class(async_session)
    bad = AttendanceRecordFactory.build(
        class_session_id=cs.id,
        student_id=student.id,
        source="ROBOT",
        recorded_by=teacher.id,
    )
    async_session.add(bad)
    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_session_fk_enforced(async_session: AsyncSession) -> None:
    teacher, student, _cs = await _scaffold_class(async_session)
    orphan = AttendanceRecordFactory.build(
        class_session_id=uuid4(),  # nonexistent
        student_id=student.id,
        recorded_by=teacher.id,
    )
    async_session.add(orphan)
    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_recorded_by_optional(async_session: AsyncSession) -> None:
    """AGENT and IMPORT sources may not have a teacher attached."""
    _teacher, student, cs = await _scaffold_class(async_session)
    agent_record = AttendanceRecordFactory.build(
        class_session_id=cs.id,
        student_id=student.id,
        source="AGENT",
        recorded_by=None,
    )
    async_session.add(agent_record)
    await async_session.flush()  # should not raise


# ---------- Service: record_attendance ----------


async def test_record_attendance_inserts_when_new(async_session: AsyncSession) -> None:
    teacher, student, cs = await _scaffold_class(async_session)
    record = await record_attendance(
        async_session,
        class_session_id=cs.id,
        student_id=student.id,
        status="PRESENT",
        source="TEACHER",
        recorded_by=teacher.id,
    )
    assert record.status == "PRESENT"
    assert record.recorded_by == teacher.id

    # confirm it persisted
    fetched = (
        await async_session.execute(
            select(AttendanceRecord).where(AttendanceRecord.id == record.id)
        )
    ).scalar_one()
    assert fetched.status == "PRESENT"


async def test_record_attendance_is_idempotent(async_session: AsyncSession) -> None:
    """Calling twice with the same (session, student) updates the row, not duplicate."""
    teacher, student, cs = await _scaffold_class(async_session)
    first = await record_attendance(
        async_session,
        class_session_id=cs.id,
        student_id=student.id,
        status="PRESENT",
        source="TEACHER",
        recorded_by=teacher.id,
    )
    second = await record_attendance(
        async_session,
        class_session_id=cs.id,
        student_id=student.id,
        status="TARDY",
        source="TEACHER",
        recorded_by=teacher.id,
        notes="arrived 5 min late",
    )
    # Same row -- same id
    assert first.id == second.id
    assert second.status == "TARDY"
    assert second.notes == "arrived 5 min late"

    # Only one row total for (session, student)
    rows = (
        (
            await async_session.execute(
                select(AttendanceRecord).where(
                    AttendanceRecord.class_session_id == cs.id,
                    AttendanceRecord.student_id == student.id,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


async def test_record_attendance_agent_source_no_recorder(
    async_session: AsyncSession,
) -> None:
    _teacher, student, cs = await _scaffold_class(async_session)
    record = await record_attendance(
        async_session,
        class_session_id=cs.id,
        student_id=student.id,
        status="ABSENT",
        source="AGENT",
        recorded_by=None,
    )
    assert record.recorded_by is None
    assert record.source == "AGENT"


async def test_record_attendance_validation_rejects_bad_status(
    async_session: AsyncSession,
) -> None:
    teacher, student, cs = await _scaffold_class(async_session)
    from hpao.services.attendance import AttendanceValidationError

    with pytest.raises(AttendanceValidationError):
        await record_attendance(
            async_session,
            class_session_id=cs.id,
            student_id=student.id,
            status="UNKNOWN",
            source="TEACHER",
            recorded_by=teacher.id,
        )


# ---------- Service: list queries ----------


async def test_list_attendance_for_session(async_session: AsyncSession) -> None:
    teacher, first_student, cs = await _scaffold_class(async_session)
    students = [
        StudentFactory.build(school_id=first_student.school_id, student_number=f"S{i:04d}")
        for i in range(3)
    ]
    async_session.add_all(students)
    await async_session.flush()

    for s, status in zip(students, ["PRESENT", "TARDY", "ABSENT"], strict=True):
        await record_attendance(
            async_session,
            class_session_id=cs.id,
            student_id=s.id,
            status=status,
            source="TEACHER",
            recorded_by=teacher.id,
        )

    rows = await list_attendance_for_session(async_session, class_session_id=cs.id)
    statuses = sorted(r.status for r in rows)
    assert statuses == ["ABSENT", "PRESENT", "TARDY"]


async def test_list_attendance_for_student_descending_by_date(
    async_session: AsyncSession,
) -> None:
    teacher, student, cs1 = await _scaffold_class(async_session)
    klass_id = cs1.class_id

    cs2 = ClassSessionFactory.build(
        class_id=klass_id,
        date=date(2025, 9, 5),
        scheduled_start=time(9, 0),
        scheduled_end=time(9, 50),
    )
    cs3 = ClassSessionFactory.build(
        class_id=klass_id,
        date=date(2025, 9, 8),
        scheduled_start=time(9, 0),
        scheduled_end=time(9, 50),
    )
    async_session.add_all([cs2, cs3])
    await async_session.flush()

    for cs, status in [(cs1, "PRESENT"), (cs2, "ABSENT"), (cs3, "TARDY")]:
        await record_attendance(
            async_session,
            class_session_id=cs.id,
            student_id=student.id,
            status=status,
            source="TEACHER",
            recorded_by=teacher.id,
        )

    rows = await list_attendance_for_student(async_session, student_id=student.id)
    assert len(rows) == 3
    # Newest first
    assert rows[0].status == "TARDY"
    assert rows[-1].status == "PRESENT"


async def test_list_attendance_for_student_filters_by_since(
    async_session: AsyncSession,
) -> None:
    teacher, student, cs1 = await _scaffold_class(async_session)
    klass_id = cs1.class_id

    cs2 = ClassSessionFactory.build(
        class_id=klass_id,
        date=date(2025, 9, 10),
        scheduled_start=time(9, 0),
        scheduled_end=time(9, 50),
    )
    async_session.add(cs2)
    await async_session.flush()

    await record_attendance(
        async_session,
        class_session_id=cs1.id,
        student_id=student.id,
        status="PRESENT",
        source="TEACHER",
        recorded_by=teacher.id,
    )
    await record_attendance(
        async_session,
        class_session_id=cs2.id,
        student_id=student.id,
        status="ABSENT",
        source="TEACHER",
        recorded_by=teacher.id,
    )

    rows = await list_attendance_for_student(
        async_session, student_id=student.id, since=date(2025, 9, 10)
    )
    assert len(rows) == 1
    assert rows[0].status == "ABSENT"
