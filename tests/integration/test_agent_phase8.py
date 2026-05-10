"""Integration tests for Phase 8: agent boundary endpoints + outbound webhook.

Covers the round-trip with HMAC verification, idempotency on correlation_id,
and the outbound dispatch happy path against an httpx MockTransport (no
real network, but real httpx + real DB write through the service).
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.api.agent import mount
from hpao.api.security import SIGNATURE_HEADER, sign
from hpao.integrations.parent_comms import dispatch_alert
from hpao.models import AgentMessage, ClassSession, Student, User
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


SECRET = "test-shared-secret"


# ---------- fixtures ----------


@pytest_asyncio.fixture
async def app(async_session: AsyncSession) -> FastAPI:
    """A FastAPI app with the agent router mounted and dependencies wired
    to the transactional async_session fixture."""
    app = FastAPI()

    async def session_provider() -> AsyncSession:
        return async_session

    mount(app, session_provider=session_provider, secret=SECRET)
    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncClient:
    """Async HTTP client over ASGI -- avoids the asyncpg + sync-TestClient
    cross-loop mismatch (TestClient runs in an anyio worker thread, asyncpg
    binds to the test's own loop)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


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


async def _signed_post(
    client: AsyncClient, path: str, payload: dict[str, object]
) -> httpx.Response:
    body = json.dumps(payload).encode("utf-8")
    sig = sign(SECRET, body)
    return await client.post(
        path,
        content=body,
        headers={"Content-Type": "application/json", SIGNATURE_HEADER: sig},
    )


async def _signed_get(client: AsyncClient, path: str) -> httpx.Response:
    sig = sign(SECRET, b"")
    return await client.get(path, headers={SIGNATURE_HEADER: sig})


# ---------- inbound: parent-message ----------


async def test_inbound_parent_message_accepts_signed_payload(
    client: AsyncClient, async_session: AsyncSession
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    correlation_id = str(uuid4())
    payload: dict[str, object] = {
        "correlation_id": correlation_id,
        "student_id": str(student.id),
        "channel": "sms",
        "received_at": datetime.now(UTC).isoformat(),
        "body": "Marcus will be late, traffic on 130.",
        "metadata": {},
    }
    resp = await _signed_post(client, "/v1/agent/inbound/parent-message", payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["accepted"] is True
    assert data["duplicate"] is False
    assert data["correlation_id"] == correlation_id


async def test_inbound_parent_message_rejects_unsigned(
    client: AsyncClient, async_session: AsyncSession
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    payload = {
        "correlation_id": str(uuid4()),
        "student_id": str(student.id),
        "channel": "sms",
        "received_at": datetime.now(UTC).isoformat(),
        "body": "x",
        "metadata": {},
    }
    resp = await client.post("/v1/agent/inbound/parent-message", json=payload)
    assert resp.status_code == 401


async def test_inbound_parent_message_rejects_bad_signature(
    client: AsyncClient, async_session: AsyncSession
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    payload = {
        "correlation_id": str(uuid4()),
        "student_id": str(student.id),
        "channel": "sms",
        "received_at": datetime.now(UTC).isoformat(),
        "body": "x",
        "metadata": {},
    }
    resp = await client.post(
        "/v1/agent/inbound/parent-message",
        json=payload,
        headers={SIGNATURE_HEADER: "deadbeef"},
    )
    assert resp.status_code == 401


async def test_inbound_parent_message_idempotent_on_correlation_id(
    client: AsyncClient, async_session: AsyncSession
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    correlation_id = str(uuid4())
    payload: dict[str, object] = {
        "correlation_id": correlation_id,
        "student_id": str(student.id),
        "channel": "sms",
        "received_at": datetime.now(UTC).isoformat(),
        "body": "x",
        "metadata": {},
    }
    first = await _signed_post(client, "/v1/agent/inbound/parent-message", payload)
    second = await _signed_post(client, "/v1/agent/inbound/parent-message", payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["agent_message_id"] == second.json()["agent_message_id"]
    assert second.json()["duplicate"] is True


# ---------- inbound: parent-response ----------


async def test_inbound_parent_response_logs_with_in_reply_to(
    client: AsyncClient, async_session: AsyncSession
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    correlation_id = uuid4()
    in_reply_to = uuid4()
    payload: dict[str, object] = {
        "correlation_id": str(correlation_id),
        "student_id": str(student.id),
        "in_reply_to": str(in_reply_to),
        "channel": "sms",
        "received_at": datetime.now(UTC).isoformat(),
        "body": "He was at the doctor; I have a note.",
        "metadata": {},
    }
    resp = await _signed_post(client, "/v1/agent/inbound/parent-response", payload)
    assert resp.status_code == 200, resp.text

    msg = (
        await async_session.execute(
            select(AgentMessage).where(AgentMessage.correlation_id == correlation_id)
        )
    ).scalar_one()
    assert msg.direction == "INBOUND"
    assert msg.payload["in_reply_to"] == str(in_reply_to)


# ---------- GET student-context ----------


async def test_student_context_returns_full_snapshot(
    client: AsyncClient, async_session: AsyncSession
) -> None:
    teacher, student, cs = await _scaffold(async_session)
    # Some attendance history
    await record_attendance(
        async_session,
        class_session_id=cs.id,
        student_id=student.id,
        status="PRESENT",
        source="TEACHER",
        recorded_by=teacher.id,
    )
    # An active hall pass
    await issue_pass(
        async_session,
        student_id=student.id,
        originating_class_session_id=cs.id,
        destination="RESTROOM",
        issued_by=teacher.id,
    )
    # An open alert
    await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="hallpass.restroom.duration_exceeded",
        severity="high",
        context={"minutes_elapsed": 17.0},
    )

    resp = await _signed_get(client, f"/v1/agent/student-context/{student.id}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["student_id"] == str(student.id)
    assert data["attendance_summary"]["days_present"] == 1
    assert data["attendance_summary"]["days_total"] == 1
    assert len(data["active_hall_passes"]) == 1
    assert data["active_hall_passes"][0]["destination"] == "RESTROOM"
    assert len(data["open_alerts"]) == 1
    assert data["open_alerts"][0]["severity"] == "high"


async def test_student_context_404_for_unknown_student(
    client: AsyncClient, async_session: AsyncSession
) -> None:
    await _scaffold(async_session)
    resp = await _signed_get(client, f"/v1/agent/student-context/{uuid4()}")
    assert resp.status_code == 404


async def test_student_context_rejects_unsigned(
    client: AsyncClient, async_session: AsyncSession
) -> None:
    _, student, _cs = await _scaffold(async_session)
    resp = await client.get(f"/v1/agent/student-context/{student.id}")
    assert resp.status_code == 401


async def test_student_context_filters_by_since(
    client: AsyncClient, async_session: AsyncSession
) -> None:
    teacher, student, cs1 = await _scaffold(async_session)
    # Attendance on session 1 (date 2025-09-04 from factory)
    await record_attendance(
        async_session,
        class_session_id=cs1.id,
        student_id=student.id,
        status="ABSENT",
        source="TEACHER",
        recorded_by=teacher.id,
    )
    # New session at later date, with PRESENT
    cs2 = ClassSessionFactory.build(class_id=cs1.class_id, date=date(2025, 9, 10))
    async_session.add(cs2)
    await async_session.flush()
    await record_attendance(
        async_session,
        class_session_id=cs2.id,
        student_id=student.id,
        status="PRESENT",
        source="TEACHER",
        recorded_by=teacher.id,
    )

    # Without since: both rows counted
    resp_all = await _signed_get(client, f"/v1/agent/student-context/{student.id}")
    assert resp_all.json()["attendance_summary"]["days_total"] == 2

    # With since=2025-09-10: only the PRESENT row
    resp_filtered = await _signed_get(
        client, f"/v1/agent/student-context/{student.id}?since=2025-09-10"
    )
    summary = resp_filtered.json()["attendance_summary"]
    assert summary["days_total"] == 1
    assert summary["days_present"] == 1
    assert summary["days_absent"] == 0


# ---------- outbound: dispatch_alert ----------


async def test_dispatch_alert_sends_signed_webhook(
    async_session: AsyncSession,
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    alert = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="hallpass.restroom.duration_exceeded",
        severity="high",
        context={
            "hall_pass_id": str(uuid4()),
            "destination": "RESTROOM",
            "minutes_elapsed": 17.0,
        },
    )

    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = request.content
        seen["sig"] = request.headers.get(SIGNATURE_HEADER)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        msg = await dispatch_alert(
            async_session,
            alert=alert,
            base_url="https://parent-comms.example",
            secret="dispatch-secret",
            http_client=client,
        )

    assert msg.status == "SENT"
    assert msg.direction == "OUTBOUND"
    assert msg.alert_id == alert.id
    assert seen["url"] == "https://parent-comms.example/notifications"
    assert seen["sig"] == sign("dispatch-secret", seen["body"])  # type: ignore[arg-type]
    body_json = json.loads(seen["body"])  # type: ignore[arg-type]
    assert body_json["event"] == "alert.raised"
    assert body_json["severity"] == "high"


async def test_dispatch_alert_marks_failed_on_5xx(
    async_session: AsyncSession,
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    alert = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.x",
        severity="medium",
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server is sad")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        msg = await dispatch_alert(
            async_session,
            alert=alert,
            base_url="https://parent-comms.example",
            secret="dispatch-secret",
            http_client=client,
        )

    assert msg.status == "FAILED"
    assert msg.error  # populated with the HTTPStatusError str


async def test_dispatch_alert_records_outbound_log_row(
    async_session: AsyncSession,
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    alert = await raise_alert(
        async_session,
        student_id=student.id,
        rule_key="rule.x",
        severity="medium",
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        msg = await dispatch_alert(
            async_session,
            alert=alert,
            base_url="https://parent-comms.example",
            secret="s",
            http_client=client,
        )

    fetched = (
        await async_session.execute(select(AgentMessage).where(AgentMessage.id == msg.id))
    ).scalar_one()
    assert fetched.status == "SENT"
    assert fetched.payload["event"] == "alert.raised"
    assert fetched.alert_id == alert.id
    assert fetched.sent_at is not None


# ---------- inbound: voice-call ----------


def _voice_call_payload(student_id: str, alert_id: str | None = None) -> dict[str, object]:
    started = datetime.now(UTC)
    body: dict[str, object] = {
        "correlation_id": str(uuid4()),
        "student_id": student_id,
        "alert_id": alert_id,
        "scenario": "absentee",
        "call_started_at": started.isoformat(),
        "call_ended_at": started.isoformat(),
        "transcript": [
            {
                "speaker": "agent",
                "text": "Hi, this is the school calling.",
                "occurred_at": started.isoformat(),
            },
            {"speaker": "guardian", "text": "Hello, yes — Marcus is sick today."},
        ],
        "excuse_summary": "Doctor appointment, returning Wednesday.",
        "parent_confirmed": True,
        "language": "en",
        "metadata": {"call_id": "EXC-1"},
    }
    return body


async def test_inbound_voice_call_accepts_signed_payload(
    client: AsyncClient, async_session: AsyncSession
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    payload = _voice_call_payload(str(student.id))
    resp = await _signed_post(client, "/v1/agent/inbound/voice-call", payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["accepted"] is True
    assert body["duplicate"] is False


async def test_inbound_voice_call_rejects_unsigned(
    client: AsyncClient, async_session: AsyncSession
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    payload = _voice_call_payload(str(student.id))
    resp = await client.post("/v1/agent/inbound/voice-call", json=payload)
    assert resp.status_code == 401


async def test_inbound_voice_call_idempotent_on_correlation_id(
    client: AsyncClient, async_session: AsyncSession
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    payload = _voice_call_payload(str(student.id))
    first = await _signed_post(client, "/v1/agent/inbound/voice-call", payload)
    second = await _signed_post(client, "/v1/agent/inbound/voice-call", payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["agent_message_id"] == second.json()["agent_message_id"]
    assert second.json()["duplicate"] is True


async def test_inbound_voice_call_persists_with_voice_agent_counterparty(
    client: AsyncClient, async_session: AsyncSession
) -> None:
    _teacher, student, _cs = await _scaffold(async_session)
    payload = _voice_call_payload(str(student.id))
    resp = await _signed_post(client, "/v1/agent/inbound/voice-call", payload)
    msg_id = resp.json()["agent_message_id"]

    fetched = (
        await async_session.execute(select(AgentMessage).where(AgentMessage.id == msg_id))
    ).scalar_one()
    assert fetched.counterparty == "voice_agent"
    assert fetched.direction == "INBOUND"
    assert fetched.student_id == student.id
    assert fetched.payload["scenario"] == "absentee"
    assert fetched.payload["excuse_summary"] == "Doctor appointment, returning Wednesday."
    assert fetched.payload["parent_confirmed"] is True
    assert len(fetched.payload["transcript"]) == 2
