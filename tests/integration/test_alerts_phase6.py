"""Integration tests for Phase 6: alerts model + service + overdue detection.

The 15-min restroom alert is the headline demo flow: a hall pass goes past
its expected_return_at, detect_overdue_passes is called, the pass flips to
OVERDUE, and an alert is raised with rule_key='hallpass.restroom.duration_exceeded'
and severity='high'.
"""

from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.models import ClassSession, HallPass, Student, User
from hpao.services.alerts import (
    acknowledge_alert,
    detect_overdue_passes,
    list_alerts_for_student,
    list_open_alerts,
    raise_alert,
    resolve_alert,
)
from hpao.services.hall_pass import issue_pass
from tests.factories import (
    AlertFactory,
    ClassFactory,
    ClassSessionFactory,
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


# ---------- raise_alert ----------


async def test_raise_alert_creates_open_row(async_session: AsyncSession) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    a = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="hallpass.restroom.duration_exceeded",
        severity="high",
        context={"minutes_elapsed": 17},
    )
    assert a.status == "OPEN"
    assert a.severity == "high"
    assert a.context["minutes_elapsed"] == 17


async def test_raise_alert_idempotent_while_open(
    async_session: AsyncSession,
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    first = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="hallpass.restroom.duration_exceeded",
        severity="high",
    )
    second = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="hallpass.restroom.duration_exceeded",
        severity="high",
    )
    assert first.id == second.id


async def test_raise_alert_allows_different_rule_keys(
    async_session: AsyncSession,
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    a = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.a",
        severity="medium",
    )
    b = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.b",
        severity="medium",
    )
    assert a.id != b.id


async def test_raise_alert_allows_same_rule_for_different_students(
    async_session: AsyncSession,
) -> None:
    _teacher, student_a, _cs = await _scaffold(async_session)
    student_b = StudentFactory.build(school_id=student_a.school_id, student_number="S99999")
    async_session.add(student_b)
    await async_session.flush()

    a = await raise_alert(
        async_session,
        student_id=student_a.id,
        rule_key="rule.shared",
        severity="medium",
    )
    b = await raise_alert(
        async_session,
        student_id=student_b.id,
        rule_key="rule.shared",
        severity="medium",
    )
    assert a.id != b.id


async def test_raise_alert_after_resolved_creates_new_row(
    async_session: AsyncSession,
) -> None:
    """The partial unique index only applies while status='OPEN'. Once an
    alert is resolved, the same student + rule can re-trigger as a new alert."""
    _teacher, student, _cs = await _scaffold(async_session)
    first = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.x",
        severity="medium",
    )
    await resolve_alert(async_session, alert_id=first.id)

    second = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.x",
        severity="medium",
    )
    assert second.id != first.id
    assert second.status == "OPEN"


# ---------- acknowledge / resolve ----------


async def test_acknowledge_alert(async_session: AsyncSession) -> None:
    teacher, student, _cs = await _scaffold(async_session)
    a = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.x",
        severity="medium",
    )
    a2 = await acknowledge_alert(async_session, alert_id=a.id, user_id=teacher.id)
    assert a2.status == "ACKNOWLEDGED"
    assert a2.acknowledged_by == teacher.id
    assert a2.acknowledged_at is not None


async def test_resolve_alert(async_session: AsyncSession) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    a = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.x",
        severity="medium",
    )
    a2 = await resolve_alert(async_session, alert_id=a.id)
    assert a2.status == "RESOLVED"
    assert a2.resolved_at is not None


async def test_resolve_alert_idempotent(async_session: AsyncSession) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    a = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.x",
        severity="medium",
    )
    await resolve_alert(async_session, alert_id=a.id)
    a3 = await resolve_alert(async_session, alert_id=a.id)
    assert a3.status == "RESOLVED"


# ---------- list queries ----------


async def test_list_open_alerts(async_session: AsyncSession) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    a = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.a",
        severity="high",
    )
    b = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.b",
        severity="medium",
    )
    await resolve_alert(async_session, alert_id=b.id)

    open_alerts = await list_open_alerts(async_session)
    open_ids = {x.id for x in open_alerts}
    assert a.id in open_ids
    assert b.id not in open_ids


async def test_list_alerts_for_student(async_session: AsyncSession) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.a",
        severity="medium",
    )
    await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.b",
        severity="low",
    )
    rows = await list_alerts_for_student(async_session, student_id=student.id)
    assert len(rows) == 2


# ---------- detect_overdue_passes (the 15-min restroom flow) ----------


async def test_detect_overdue_marks_pass_and_raises_alert(
    async_session: AsyncSession,
) -> None:
    """End-to-end demo flow: student gets restroom pass, time passes, detect
    runs, pass flips to OVERDUE, alert raised with high severity for on-duty
    admin to consume."""
    teacher, student, cs = await _scaffold(async_session)
    pass_ = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    cutoff = pass_.expected_return_at + timedelta(minutes=2)

    alerts = await detect_overdue_passes(async_session, now=cutoff)
    assert len(alerts) == 1
    a = alerts[0]
    assert a.severity == "high"
    assert a.rule_key == "hallpass.restroom.duration_exceeded"
    assert a.context["destination"] == "RESTROOM"
    assert a.context["hall_pass_id"] == str(pass_.id)
    assert a.context["minutes_elapsed"] >= 15

    # Pass flipped to OVERDUE
    refreshed = (
        await async_session.execute(select(HallPass).where(HallPass.id == pass_.id))
    ).scalar_one()
    assert refreshed.status == "OVERDUE"


async def test_detect_overdue_idempotent(async_session: AsyncSession) -> None:
    teacher, student, cs = await _scaffold(async_session)
    pass_ = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    cutoff = pass_.expected_return_at + timedelta(minutes=2)

    first = await detect_overdue_passes(async_session, now=cutoff)
    second = await detect_overdue_passes(async_session, now=cutoff)
    # First call surfaces the newly-overdue pass; second call has nothing new
    # to surface because the pass is now OVERDUE (not ACTIVE), so the inner
    # find_overdue_active_passes query returns []. That is the correct
    # idempotency semantic: re-running doesn't duplicate state, doesn't
    # require the function to return identical lists.
    assert len(first) == 1
    assert second == []

    # End state: still exactly one OPEN alert for this student + rule, and
    # the pass is still OVERDUE.
    student_alerts = await list_alerts_for_student(async_session, student_id=student.id)
    open_for_rule = [
        a
        for a in student_alerts
        if a.status == "OPEN" and a.rule_key == "hallpass.restroom.duration_exceeded"
    ]
    assert len(open_for_rule) == 1
    assert open_for_rule[0].id == first[0].id

    refreshed_pass = await async_session.get(HallPass, pass_.id)
    assert refreshed_pass is not None
    assert refreshed_pass.status == "OVERDUE"


async def test_detect_overdue_skips_fresh_passes(
    async_session: AsyncSession,
) -> None:
    teacher, student, cs = await _scaffold(async_session)
    fresh = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    cutoff = fresh.checked_out_at + timedelta(minutes=5)

    alerts = await detect_overdue_passes(async_session, now=cutoff)
    assert alerts == []


async def test_detect_overdue_nurse_has_medium_severity(
    async_session: AsyncSession,
) -> None:
    teacher, student, cs = await _scaffold(async_session)
    pass_ = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="NURSE",
        issued_by=teacher.id,
    )
    cutoff = pass_.expected_return_at + timedelta(minutes=2)

    alerts = await detect_overdue_passes(async_session, now=cutoff)
    assert len(alerts) == 1
    assert alerts[0].severity == "medium"
    assert alerts[0].rule_key == "hallpass.nurse.duration_exceeded"


# ---------- DB constraints ----------


async def test_invalid_severity_rejected_at_db(
    async_session: AsyncSession,
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    bad = AlertFactory.build(
        student_id=student.id,
        severity="urgent",  # not in enum
    )
    async_session.add(bad)
    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_invalid_status_rejected_at_db(async_session: AsyncSession) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    bad = AlertFactory.build(
        student_id=student.id,
        status="WHATEVER",
    )
    async_session.add(bad)
    with pytest.raises(IntegrityError):
        await async_session.flush()


async def test_partial_unique_open_alerts_db_enforced(
    async_session: AsyncSession,
) -> None:
    """Direct INSERTs that bypass the service should still hit the partial unique."""
    _teacher, student, _cs = await _scaffold(async_session)
    a = AlertFactory.build(student_id=student.id, rule_key="rule.x", severity="high")
    b = AlertFactory.build(student_id=student.id, rule_key="rule.x", severity="high")
    async_session.add_all([a, b])
    with pytest.raises(IntegrityError):
        await async_session.flush()
