"""Integration tests for the demo dispatcher loop.

The demo flow end-to-end: create a hall pass, advance time, run the
dispatcher cycle, verify the pass is OVERDUE, an alert was raised, and
a signed webhook was POSTed to a MockTransport standing in for
parent-comms.
"""

from __future__ import annotations

import json
from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.api.security import SIGNATURE_HEADER, sign
from hpao.models import AgentMessage, ClassSession, HallPass, Student, User
from hpao.services.alerts import raise_alert
from hpao.services.dispatcher import (
    find_pending_dispatch_alerts,
    run_alert_dispatch_cycle,
)
from hpao.services.hall_pass import issue_pass
from tests.factories import (
    AgentMessageFactory,
    ClassFactory,
    ClassSessionFactory,
    SchoolFactory,
    StudentFactory,
    UserFactory,
)

pytestmark = pytest.mark.integration


PARENT_COMMS_URL = "https://parent-comms.example"
PARENT_COMMS_SECRET = "demo-loop-secret"


async def _scaffold(db: AsyncSession) -> tuple[User, Student, ClassSession]:
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


def _ok_handler(seen: list[httpx.Request]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    return httpx.MockTransport(handler)


# ---------- find_pending_dispatch_alerts ----------


async def test_find_pending_returns_open_undispatched_alerts(
    async_session: AsyncSession,
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    # Open + undispatched
    a = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.x",
        severity="medium",
    )
    pending = await find_pending_dispatch_alerts(async_session)
    assert any(p.id == a.id for p in pending)


async def test_find_pending_excludes_already_dispatched(
    async_session: AsyncSession,
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    a = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.x",
        severity="medium",
    )
    # Simulate a successful prior dispatch
    msg = AgentMessageFactory.build(
        direction="OUTBOUND",
        counterparty="parent_comms",
        correlation_id=uuid4(),
        student_id=student.id,
        alert_id=a.id,
        status="SENT",
    )
    async_session.add(msg)
    await async_session.flush()

    pending = await find_pending_dispatch_alerts(async_session)
    assert all(p.id != a.id for p in pending)


async def test_find_pending_includes_alerts_after_failed_dispatch(
    async_session: AsyncSession,
) -> None:
    """Transient failures must be re-tried -- don't strand an alert in
    perpetually-FAILED state with no second chance."""
    _teacher, student, _cs = await _scaffold(async_session)
    a = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.x",
        severity="medium",
    )
    failed = AgentMessageFactory.build(
        direction="OUTBOUND",
        correlation_id=uuid4(),
        student_id=student.id,
        alert_id=a.id,
        status="FAILED",
        error="parent-comms 503",
    )
    async_session.add(failed)
    await async_session.flush()

    pending = await find_pending_dispatch_alerts(async_session)
    assert any(p.id == a.id for p in pending)


# ---------- run_alert_dispatch_cycle ----------


async def test_demo_loop_end_to_end(async_session: AsyncSession) -> None:
    """The headline demo: pass goes overdue -> alert raised -> webhook fired."""
    teacher, student, cs = await _scaffold(async_session)
    pass_ = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    cutoff = pass_.expected_return_at + timedelta(minutes=2)

    seen: list[httpx.Request] = []
    transport = _ok_handler(seen)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await run_alert_dispatch_cycle(
            async_session,
            parent_comms_base_url=PARENT_COMMS_URL,
            parent_comms_secret=PARENT_COMMS_SECRET,
            now=cutoff,
            http_client=client,
        )

    # Phase 6: detect_overdue_passes ran
    assert len(result.new_alerts) == 1
    new = result.new_alerts[0]
    assert new.severity == "high"
    assert new.rule_key == "hallpass.restroom.duration_exceeded"

    # Phase 8: webhook fired with signed payload
    assert len(result.dispatched) == 1
    assert result.dispatched[0].status == "SENT"
    assert len(seen) == 1
    sent_request = seen[0]
    assert str(sent_request.url) == f"{PARENT_COMMS_URL}/notifications"
    body = sent_request.content
    assert sent_request.headers[SIGNATURE_HEADER] == sign(PARENT_COMMS_SECRET, body)
    payload = json.loads(body)
    assert payload["event"] == "alert.raised"
    assert payload["severity"] == "high"
    assert payload["context"]["rule_key"] == "hallpass.restroom.duration_exceeded"


async def test_demo_loop_idempotent_no_duplicate_dispatch(
    async_session: AsyncSession,
) -> None:
    teacher, student, cs = await _scaffold(async_session)
    pass_ = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    cutoff = pass_.expected_return_at + timedelta(minutes=2)

    seen: list[httpx.Request] = []
    transport = _ok_handler(seen)
    async with httpx.AsyncClient(transport=transport) as client:
        await run_alert_dispatch_cycle(
            async_session,
            parent_comms_base_url=PARENT_COMMS_URL,
            parent_comms_secret=PARENT_COMMS_SECRET,
            now=cutoff,
            http_client=client,
        )
        # Second cycle: same time, same state. Should not redispatch.
        second = await run_alert_dispatch_cycle(
            async_session,
            parent_comms_base_url=PARENT_COMMS_URL,
            parent_comms_secret=PARENT_COMMS_SECRET,
            now=cutoff,
            http_client=client,
        )

    assert second.dispatched == []
    assert len(seen) == 1  # only the first cycle's POST


async def test_demo_loop_skips_dispatch_when_no_parent_comms_config(
    async_session: AsyncSession,
) -> None:
    teacher, student, cs = await _scaffold(async_session)
    pass_ = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    cutoff = pass_.expected_return_at + timedelta(minutes=2)

    result = await run_alert_dispatch_cycle(
        async_session,
        parent_comms_base_url=None,
        parent_comms_secret=None,
        now=cutoff,
    )

    # State hygiene: pass marked OVERDUE, alert raised...
    assert len(result.new_alerts) == 1
    assert result.skipped_no_config is True
    assert result.dispatched == []

    # ...but no agent_message OUTBOUND row.
    from sqlalchemy import select

    out_count = (
        await async_session.execute(
            select(AgentMessage).where(AgentMessage.direction == "OUTBOUND")
        )
    ).all()
    assert out_count == []


async def test_demo_loop_retries_after_failed_dispatch(
    async_session: AsyncSession,
) -> None:
    teacher, student, cs = await _scaffold(async_session)
    pass_ = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    cutoff = pass_.expected_return_at + timedelta(minutes=2)

    # First cycle: parent-comms is down (5xx).
    def fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="down")

    async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
        first = await run_alert_dispatch_cycle(
            async_session,
            parent_comms_base_url=PARENT_COMMS_URL,
            parent_comms_secret=PARENT_COMMS_SECRET,
            now=cutoff,
            http_client=client,
        )
    assert first.dispatched[0].status == "FAILED"

    # Second cycle: parent-comms is back up. Same alert should re-dispatch.
    seen: list[httpx.Request] = []
    transport = _ok_handler(seen)
    async with httpx.AsyncClient(transport=transport) as client:
        second = await run_alert_dispatch_cycle(
            async_session,
            parent_comms_base_url=PARENT_COMMS_URL,
            parent_comms_secret=PARENT_COMMS_SECRET,
            now=cutoff,
            http_client=client,
        )
    assert len(second.dispatched) == 1
    assert second.dispatched[0].status == "SENT"
    assert len(seen) == 1


# ---------- pass-through state checks ----------


async def test_demo_loop_marks_pass_overdue(
    async_session: AsyncSession,
) -> None:
    teacher, student, cs = await _scaffold(async_session)
    pass_ = await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    cutoff = pass_.expected_return_at + timedelta(minutes=2)

    seen: list[httpx.Request] = []
    transport = _ok_handler(seen)
    async with httpx.AsyncClient(transport=transport) as client:
        await run_alert_dispatch_cycle(
            async_session,
            parent_comms_base_url=PARENT_COMMS_URL,
            parent_comms_secret=PARENT_COMMS_SECRET,
            now=cutoff,
            http_client=client,
        )

    refreshed = await async_session.get(HallPass, pass_.id)
    assert refreshed is not None
    assert refreshed.status == "OVERDUE"
