"""Integration tests for Phase 3: hall pass model + service.

Covers DB-level invariants (partial unique index for one ACTIVE pass per
student, status / destination CHECK, FK enforcement) and service behaviors
(issue, check-in on-time vs late, mark_overdue, find_overdue) against
real Postgres.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from lizzie.models import ClassSession, Student, User
from lizzie.services.hall_pass import (
    HallPassConflictError,
    check_in_pass,
    find_overdue_active_passes,
    issue_pass,
    mark_overdue,
)
from tests.factories import (
    ClassFactory,
    ClassSessionFactory,
    HallPassFactory,
    SchoolFactory,
    StudentFactory,
    UserFactory,
)

pytestmark = pytest.mark.integration


async def _scaffold(db: AsyncSession) -> tuple[User, Student, ClassSession]:
    """school -> teacher + student -> class -> session."""
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


# ---------- issue_pass ----------


async def test_issue_pass_creates_active_pass(async_session: AsyncSession) -> None:
    teacher, student, cs = await _scaffold(async_session)
    p = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    assert p.status == "ACTIVE"
    assert p.destination == "RESTROOM"
    assert p.checked_in_at is None
    # Default 15-minute restroom window
    assert (p.expected_return_at - p.checked_out_at) == timedelta(minutes=15)


async def test_issue_pass_uses_destination_default_duration(
    async_session: AsyncSession,
) -> None:
    teacher, student, cs = await _scaffold(async_session)
    p = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="NURSE",
        issued_by=teacher.id,
    )
    assert (p.expected_return_at - p.checked_out_at) == timedelta(minutes=30)


async def test_issue_pass_accepts_custom_duration(
    async_session: AsyncSession,
) -> None:
    teacher, student, cs = await _scaffold(async_session)
    p = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
        duration_minutes=5,
    )
    assert (p.expected_return_at - p.checked_out_at) == timedelta(minutes=5)


async def test_one_active_pass_per_student_via_service(
    async_session: AsyncSession,
) -> None:
    teacher, student, cs = await _scaffold(async_session)
    await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    with pytest.raises(HallPassConflictError):
        await issue_pass(
            async_session,
            student_id=student.id,
            originating_class_session_id=cs.id,
            destination="NURSE",
            issued_by=teacher.id,
        )


async def test_active_pass_invariant_db_enforced(async_session: AsyncSession) -> None:
    """Even a direct INSERT bypassing the service hits the partial unique index."""
    teacher, student, cs = await _scaffold(async_session)
    now = datetime.now(UTC)
    p1 = HallPassFactory.build(
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        checked_out_at=now,
        expected_return_at=now + timedelta(minutes=15),
        issued_by=teacher.id,
    )
    p2 = HallPassFactory.build(
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="NURSE",
        checked_out_at=now,
        expected_return_at=now + timedelta(minutes=30),
        issued_by=teacher.id,
    )
    async_session.add_all([p1, p2])
    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_returned_pass_does_not_block_next_pass(
    async_session: AsyncSession,
) -> None:
    teacher, student, cs = await _scaffold(async_session)
    p1 = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    await check_in_pass(async_session, pass_id=p1.id)

    p2 = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    assert p2.id != p1.id
    assert p2.status == "ACTIVE"


# ---------- check_in_pass ----------


async def test_check_in_on_time_marks_returned(async_session: AsyncSession) -> None:
    teacher, student, cs = await _scaffold(async_session)
    p = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    on_time = p.checked_out_at + timedelta(minutes=5)
    p2 = await check_in_pass(async_session, pass_id=p.id, now=on_time)
    assert p2.status == "RETURNED"
    assert p2.checked_in_at == on_time


async def test_check_in_late_flags_pass(async_session: AsyncSession) -> None:
    teacher, student, cs = await _scaffold(async_session)
    p = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    # 5 min past the 15-min expected return
    late = p.checked_out_at + timedelta(minutes=20)
    p2 = await check_in_pass(async_session, pass_id=p.id, now=late)
    assert p2.status == "FLAGGED"


# ---------- mark_overdue / find_overdue_active_passes ----------


async def test_mark_overdue_sets_status(async_session: AsyncSession) -> None:
    teacher, student, cs = await _scaffold(async_session)
    p = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    later = p.expected_return_at + timedelta(minutes=1)
    p2 = await mark_overdue(async_session, pass_id=p.id, now=later)
    assert p2.status == "OVERDUE"


async def test_mark_overdue_idempotent(async_session: AsyncSession) -> None:
    teacher, student, cs = await _scaffold(async_session)
    p = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    later = p.expected_return_at + timedelta(minutes=1)
    await mark_overdue(async_session, pass_id=p.id, now=later)
    p3 = await mark_overdue(async_session, pass_id=p.id, now=later)
    assert p3.status == "OVERDUE"


async def test_mark_overdue_respects_clock(async_session: AsyncSession) -> None:
    """Calling before expected_return_at is a no-op."""
    teacher, student, cs = await _scaffold(async_session)
    p = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    too_early = p.checked_out_at + timedelta(minutes=5)
    p2 = await mark_overdue(async_session, pass_id=p.id, now=too_early)
    assert p2.status == "ACTIVE"


async def test_find_overdue_active_passes_returns_only_overdue(
    async_session: AsyncSession,
) -> None:
    teacher, student, cs = await _scaffold(async_session)
    p_overdue = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    # Different student, fresh pass, not overdue
    student2 = StudentFactory.build(school_id=student.school_id, student_number="S99999")
    async_session.add(student2)
    await async_session.flush()
    p_fresh = await issue_pass(
        async_session,
        student_id=student2.id,
        originating_class_session_id=cs.id,
        destination="NURSE",
        issued_by=teacher.id,
    )

    cutoff = p_overdue.expected_return_at + timedelta(minutes=1)
    overdue = await find_overdue_active_passes(async_session, now=cutoff)
    overdue_ids = {p.id for p in overdue}
    assert p_overdue.id in overdue_ids
    # NURSE pass has 30-min window; cutoff is 16 min after restroom checkout
    # so the nurse pass is not overdue yet.
    assert p_fresh.id not in overdue_ids


# ---------- DB constraints ----------


async def test_invalid_destination_rejected_at_db(async_session: AsyncSession) -> None:
    teacher, student, cs = await _scaffold(async_session)
    now = datetime.now(UTC)
    bad = HallPassFactory.build(
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="CAFETERIA",
        checked_out_at=now,
        expected_return_at=now + timedelta(minutes=15),
        issued_by=teacher.id,
    )
    async_session.add(bad)
    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_invalid_status_rejected_at_db(async_session: AsyncSession) -> None:
    teacher, student, cs = await _scaffold(async_session)
    now = datetime.now(UTC)
    bad = HallPassFactory.build(
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        status="UNKNOWN",
        checked_out_at=now,
        expected_return_at=now + timedelta(minutes=15),
        issued_by=teacher.id,
    )
    async_session.add(bad)
    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_completed_passes_can_share_student(async_session: AsyncSession) -> None:
    """The partial unique index only applies to ACTIVE rows; a student can
    have many RETURNED / FLAGGED / OVERDUE rows in their history."""
    teacher, student, cs = await _scaffold(async_session)
    now = datetime.now(UTC)
    a = HallPassFactory.build(
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        checked_out_at=now,
        expected_return_at=now + timedelta(minutes=15),
        checked_in_at=now + timedelta(minutes=5),
        status="RETURNED",
        issued_by=teacher.id,
    )
    b = HallPassFactory.build(
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="NURSE",
        checked_out_at=now + timedelta(hours=1),
        expected_return_at=now + timedelta(hours=1, minutes=30),
        checked_in_at=now + timedelta(hours=1, minutes=20),
        status="RETURNED",
        issued_by=teacher.id,
    )
    async_session.add_all([a, b])
    await async_session.flush()  # should not raise
