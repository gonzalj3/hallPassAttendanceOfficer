"""Integration tests for Phase 7 agent tools.

The OpenAI agent loop itself is a network-bound smoke test we don't run
in the gate; instead we test each `tool_*` async function as a plain
callable with a synthesised RunContextWrapper. That gives full DB-backed
coverage of the same code path the agent invokes -- without an OpenAI
API key.
"""

from __future__ import annotations

from typing import Any

import pytest
from agents import RunContextWrapper
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.agent.context import HpaoContext
from hpao.agent.tools import (
    tool_dispatch_pending_alerts,
    tool_get_active_hall_pass,
    tool_get_open_alerts_for_student,
    tool_get_student_attendance,
    tool_lookup_student_by_number,
    tool_raise_alert_for_student,
    tool_record_attendance_as_agent,
)
from hpao.models import ClassSession, Student, User
from hpao.policy.embeddings import StubEmbedder
from hpao.services.alerts import raise_alert
from hpao.services.attendance import record_attendance
from hpao.services.hall_pass import issue_pass
from tests.factories import (
    ClassFactory,
    ClassSessionFactory,
    SchoolFactory,
    StudentFactory,
    UserFactory,
)

pytestmark = pytest.mark.integration


def _make_ctx(db: AsyncSession, **overrides: Any) -> RunContextWrapper[HpaoContext]:
    """Synthesise the SDK's RunContextWrapper for direct tool invocation."""
    hpao_ctx = HpaoContext(
        db=db,
        embedder=StubEmbedder({}),
        parent_comms_url=overrides.get("parent_comms_url"),
        parent_comms_secret=overrides.get("parent_comms_secret"),
    )
    return RunContextWrapper(context=hpao_ctx)


async def _scaffold(db: AsyncSession) -> tuple[User, Student, ClassSession]:
    school = SchoolFactory.build()
    db.add(school)
    await db.flush()
    teacher = UserFactory.build(school_id=school.id)
    student = StudentFactory.build(school_id=school.id, student_number="S00042")
    db.add_all([teacher, student])
    await db.flush()
    klass = ClassFactory.build(school_id=school.id, teacher_id=teacher.id)
    db.add(klass)
    await db.flush()
    cs = ClassSessionFactory.build(class_id=klass.id)
    db.add(cs)
    await db.flush()
    return teacher, student, cs


# ---------- read tools ----------


async def test_lookup_student_by_number_returns_identity(
    async_session: AsyncSession,
) -> None:
    _, student, _cs = await _scaffold(async_session)
    ctx = _make_ctx(async_session)
    result = await tool_lookup_student_by_number(ctx, "S00042")
    assert result is not None
    assert result["id"] == str(student.id)
    assert result["student_number"] == "S00042"
    assert result["first_name"] == student.first_name


async def test_lookup_student_by_number_returns_none_when_missing(
    async_session: AsyncSession,
) -> None:
    await _scaffold(async_session)
    ctx = _make_ctx(async_session)
    assert await tool_lookup_student_by_number(ctx, "S99999") is None


async def test_get_student_attendance_returns_records(
    async_session: AsyncSession,
) -> None:
    teacher, student, cs = await _scaffold(async_session)
    await record_attendance(
        async_session,
        class_session_id=cs.id,
        student_id=student.id,
        status="PRESENT",
        source="TEACHER",
        recorded_by=teacher.id,
    )
    ctx = _make_ctx(async_session)

    result = await tool_get_student_attendance(ctx, str(student.id))
    assert result["count"] == 1
    assert result["records"][0]["status"] == "PRESENT"


async def test_get_active_hall_pass_returns_active_when_present(
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
    ctx = _make_ctx(async_session)

    result = await tool_get_active_hall_pass(ctx, str(student.id))
    assert result is not None
    assert result["id"] == str(pass_.id)
    assert result["destination"] == "RESTROOM"


async def test_get_active_hall_pass_returns_none_when_no_active(
    async_session: AsyncSession,
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    ctx = _make_ctx(async_session)
    assert await tool_get_active_hall_pass(ctx, str(student.id)) is None


async def test_get_open_alerts_for_student_filters_to_open(
    async_session: AsyncSession,
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.demo",
        severity="medium",
    )
    ctx = _make_ctx(async_session)

    result = await tool_get_open_alerts_for_student(ctx, str(student.id))
    assert len(result) == 1
    assert result[0]["rule_key"] == "rule.demo"


# ---------- write tools ----------


async def test_record_attendance_as_agent_marks_source_AGENT(
    async_session: AsyncSession,
) -> None:
    _teacher, student, cs = await _scaffold(async_session)
    ctx = _make_ctx(async_session)

    result = await tool_record_attendance_as_agent(
        ctx,
        class_session_id=str(cs.id),
        student_id=str(student.id),
        status="EXCUSED",
        notes="Parent reported doctor's appointment",
    )
    assert result["status"] == "EXCUSED"
    assert result["source"] == "AGENT"
    assert result["notes"] == "Parent reported doctor's appointment"


async def test_record_attendance_as_agent_is_idempotent(
    async_session: AsyncSession,
) -> None:
    _teacher, student, cs = await _scaffold(async_session)
    ctx = _make_ctx(async_session)

    first = await tool_record_attendance_as_agent(
        ctx,
        class_session_id=str(cs.id),
        student_id=str(student.id),
        status="ABSENT",
    )
    second = await tool_record_attendance_as_agent(
        ctx,
        class_session_id=str(cs.id),
        student_id=str(student.id),
        status="EXCUSED",
        notes="excuse received",
    )
    assert first["id"] == second["id"]
    assert second["status"] == "EXCUSED"


async def test_raise_alert_for_student_creates_alert(
    async_session: AsyncSession,
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    ctx = _make_ctx(async_session)

    result = await tool_raise_alert_for_student(
        ctx,
        student_id=str(student.id),
        rule_key="agent.test.alert",
        severity="medium",
        summary="agent thought this was worth raising",
        evidence={"foo": "bar"},
    )
    assert result["rule_key"] == "agent.test.alert"
    assert result["severity"] == "medium"
    assert result["status"] == "OPEN"


# ---------- dispatch ----------


async def test_dispatch_pending_alerts_skips_when_unconfigured(
    async_session: AsyncSession,
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.demo",
        severity="medium",
    )
    ctx = _make_ctx(async_session)  # no parent_comms config

    result = await tool_dispatch_pending_alerts(ctx)
    assert result["dispatched"] == 0
    assert "skipped" in result


async def test_dispatch_pending_alerts_sends_when_configured(
    async_session: AsyncSession,
) -> None:
    import httpx

    _teacher, student, _cs = await _scaffold(async_session)
    await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.demo",
        severity="medium",
    )

    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    # Tool uses a default httpx.AsyncClient internally -- patch the global
    # so it picks up our MockTransport.
    import hpao.integrations.parent_comms as pc

    original = httpx.AsyncClient

    class _Patched(httpx.AsyncClient):  # type: ignore[misc]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    pc.httpx.AsyncClient = _Patched  # type: ignore[misc, assignment]
    try:
        ctx = _make_ctx(
            async_session,
            parent_comms_url="https://parent-comms.example",
            parent_comms_secret="s",
        )
        result = await tool_dispatch_pending_alerts(ctx)
    finally:
        pc.httpx.AsyncClient = original  # type: ignore[misc]

    assert result["sent"] == 1
    assert result["failed"] == 0
    assert len(seen) == 1


# ---------- ALL_TOOLS sanity ----------


async def test_all_tools_have_clean_names_for_the_llm() -> None:
    """Names the LLM sees should be the public ones, not the `tool_*` ones."""
    from hpao.agent.tools import ALL_TOOLS

    expected = {
        "get_student_attendance",
        "get_active_hall_pass",
        "get_open_alerts_for_student",
        "lookup_student_by_number",
        "query_policy",
        "record_attendance_as_agent",
        "raise_alert_for_student",
        "dispatch_pending_alerts",
    }
    actual = {t.name for t in ALL_TOOLS}
    assert actual == expected
