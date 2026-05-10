"""End-to-end tests for the browser-facing REST surface.

Drives the same shape the React app will use: GET sessions -> GET roster
-> POST hall-passes -> POST .../return.

Uses httpx.AsyncClient + ASGITransport (not FastAPI TestClient) so the
test, the seed, and the route handlers all run on the same asyncio loop
and can share a single transactional `async_session`. The fixture's
outer-transaction rollback cleans up between tests.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, time, timedelta
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.api.agent import _get_session as _agent_get_session
from hpao.api.frontend import _get_session as _frontend_get_session
from hpao.app import make_app
from hpao.cli.seed import seed
from hpao.models import (
    Class,
    ClassEnrollment,
    ClassSession,
    School,
    Student,
    User,
)

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def client(
    migrated_database: str, async_session: AsyncSession
) -> AsyncIterator[httpx.AsyncClient]:
    app = make_app(migrated_database, allowed_origins=["http://localhost:3000"])

    async def session_dep() -> AsyncIterator[AsyncSession]:
        # Share the test's transactional session so setup writes are
        # visible to the route handlers and a single rollback at fixture
        # teardown undoes everything.
        yield async_session

    app.dependency_overrides[_frontend_get_session] = session_dep
    app.dependency_overrides[_agent_get_session] = session_dep
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _seed_school(async_session: AsyncSession) -> dict[str, object]:
    """Build a school with one class, today's session, three students.

    Flushes only — caller's outer transaction owns the commit/rollback so
    test isolation is preserved.
    """
    today = date.today()

    school = School(name="Test High")
    async_session.add(school)
    await async_session.flush()

    teacher = User(
        school_id=school.id,
        email="t@test.edu",
        role="TEACHER",
        first_name="Test",
        last_name="Teacher",
    )
    async_session.add(teacher)
    await async_session.flush()

    cls = Class(
        school_id=school.id,
        teacher_id=teacher.id,
        name="Biology",
        subject="Science",
        period="Period 3",
        room="204",
    )
    async_session.add(cls)
    await async_session.flush()

    session = ClassSession(
        class_id=cls.id,
        date=today,
        scheduled_start=time(10, 20),
        scheduled_end=time(11, 10),
    )
    async_session.add(session)
    await async_session.flush()

    students = [
        Student(
            school_id=school.id,
            student_number=f"S{i:03d}",
            grade_level="10",
            first_name=fn,
            last_name=ln,
            enrolled_at=today - timedelta(days=30),
        )
        for i, (fn, ln) in enumerate(
            [("Alice", "Garcia"), ("Bob", "Lee"), ("Carlos", "Mendez")], start=1
        )
    ]
    async_session.add_all(students)
    await async_session.flush()

    for s in students:
        async_session.add(
            ClassEnrollment(
                class_id=cls.id,
                student_id=s.id,
                enrolled_at=today - timedelta(days=30),
            )
        )
    await async_session.flush()

    return {
        "school_id": school.id,
        "teacher_id": teacher.id,
        "class_id": cls.id,
        "session_id": session.id,
        "students": students,
    }


async def test_list_sessions_returns_today(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    seeded = await _seed_school(async_session)

    response = await client.get("/api/sessions")

    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    period = next(p for p in body if p["id"] == str(seeded["session_id"]))
    assert period["name"] == "Biology"
    assert period["period"] == "Period 3"
    assert period["room"] == "204"
    assert period["studentCount"] == 3
    assert period["startTime"] == "10:20 AM"
    assert period["endTime"] == "11:10 AM"
    assert period["type"] in {"suggested", "regular", "lunch", "advisory"}


async def test_get_roster_returns_students_and_active_passes(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    seeded = await _seed_school(async_session)

    response = await client.get(f"/api/sessions/{seeded['session_id']}/students")

    assert response.status_code == 200
    body = response.json()
    assert body["session"]["id"] == str(seeded["session_id"])
    assert len(body["students"]) == 3
    assert {s["name"] for s in body["students"]} == {
        "Alice Garcia",
        "Bob Lee",
        "Carlos Mendez",
    }
    assert all(s["gradeLevel"] == 10 for s in body["students"])
    assert body["activePasses"] == []


async def test_get_roster_404_for_unknown_session(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/sessions/{uuid4()}/students")
    assert response.status_code == 404


async def test_issue_hall_pass_creates_active_pass(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    seeded = await _seed_school(async_session)
    student_id = seeded["students"][0].id  # type: ignore[index]

    response = await client.post(
        "/api/hall-passes",
        json={
            "studentId": str(student_id),
            "sessionId": str(seeded["session_id"]),
            "destination": "RESTROOM",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["studentId"] == str(student_id)
    assert body["destination"] == "RESTROOM"
    assert body["status"] == "ACTIVE"
    assert body["studentName"] == "Alice Garcia"
    assert body["checkedInAt"] is None


async def test_issue_hall_pass_accepts_new_destinations(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    """Migration 0009 added HALLWAY + CLASSROOM so the frontend's vocabulary
    works without a translation layer."""
    seeded = await _seed_school(async_session)
    student_id = seeded["students"][0].id  # type: ignore[index]

    response = await client.post(
        "/api/hall-passes",
        json={
            "studentId": str(student_id),
            "sessionId": str(seeded["session_id"]),
            "destination": "HALLWAY",
        },
    )
    assert response.status_code == 201
    assert response.json()["destination"] == "HALLWAY"


async def test_issue_hall_pass_rejects_unknown_destination(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    seeded = await _seed_school(async_session)
    student_id = seeded["students"][0].id  # type: ignore[index]

    response = await client.post(
        "/api/hall-passes",
        json={
            "studentId": str(student_id),
            "sessionId": str(seeded["session_id"]),
            "destination": "MARS",
        },
    )
    assert response.status_code == 422  # pydantic Literal validation


async def test_issue_hall_pass_conflicts_when_student_already_active(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    seeded = await _seed_school(async_session)
    student_id = seeded["students"][0].id  # type: ignore[index]

    first = await client.post(
        "/api/hall-passes",
        json={
            "studentId": str(student_id),
            "sessionId": str(seeded["session_id"]),
            "destination": "RESTROOM",
        },
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/hall-passes",
        json={
            "studentId": str(student_id),
            "sessionId": str(seeded["session_id"]),
            "destination": "NURSE",
        },
    )
    assert second.status_code == 409


async def test_return_hall_pass_marks_returned(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    seeded = await _seed_school(async_session)
    student_id = seeded["students"][0].id  # type: ignore[index]

    issued = await client.post(
        "/api/hall-passes",
        json={
            "studentId": str(student_id),
            "sessionId": str(seeded["session_id"]),
            "destination": "RESTROOM",
        },
    )
    pass_id = issued.json()["id"]

    response = await client.post(f"/api/hall-passes/{pass_id}/return")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "RETURNED"
    assert body["checkedInAt"] is not None


async def test_roster_active_passes_include_freshly_issued_pass(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    seeded = await _seed_school(async_session)
    student_id = seeded["students"][0].id  # type: ignore[index]

    await client.post(
        "/api/hall-passes",
        json={
            "studentId": str(student_id),
            "sessionId": str(seeded["session_id"]),
            "destination": "RESTROOM",
        },
    )

    roster = await client.get(f"/api/sessions/{seeded['session_id']}/students")
    assert roster.status_code == 200
    body = roster.json()
    assert len(body["activePasses"]) == 1
    assert body["activePasses"][0]["studentId"] == str(student_id)
    assert body["activePasses"][0]["status"] == "ACTIVE"


async def test_list_hall_passes_filters_by_status(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    seeded = await _seed_school(async_session)
    s0 = seeded["students"][0].id  # type: ignore[index]

    issued = await client.post(
        "/api/hall-passes",
        json={
            "studentId": str(s0),
            "sessionId": str(seeded["session_id"]),
            "destination": "RESTROOM",
        },
    )
    pass_id = issued.json()["id"]

    actives_before = await client.get("/api/hall-passes", params={"status_filter": "ACTIVE"})
    assert actives_before.status_code == 200
    assert len(actives_before.json()) >= 1

    await client.post(f"/api/hall-passes/{pass_id}/return")

    actives_after = await client.get("/api/hall-passes", params={"status_filter": "ACTIVE"})
    assert all(p["id"] != pass_id for p in actives_after.json())
    returned = await client.get("/api/hall-passes", params={"status_filter": "RETURNED"})
    assert any(p["id"] == pass_id for p in returned.json())


async def test_seed_cli_is_idempotent(async_session: AsyncSession) -> None:
    first = await seed(async_session)
    second = await seed(async_session)
    assert first["school_id"] == second["school_id"]


# ---------- voice-call dashboard reads ----------


async def _seed_voice_call(
    async_session: AsyncSession,
    *,
    student_id,
    correlation_id=None,
    excuse_summary="Doctor appointment.",
    parent_confirmed=True,
    scenario="absentee",
) -> str:
    """Insert an INBOUND agent_messages row mirroring what the voice agent posts."""
    from datetime import UTC, datetime
    from uuid import uuid4

    from hpao.models import AgentMessage

    correlation = correlation_id or uuid4()
    started = datetime.now(UTC)
    msg = AgentMessage(
        direction="INBOUND",
        counterparty="voice_agent",
        correlation_id=correlation,
        student_id=student_id,
        payload={
            "scenario": scenario,
            "call_started_at": started.isoformat(),
            "call_ended_at": started.isoformat(),
            "transcript": [
                {"speaker": "agent", "text": "Hi, calling from the school."},
                {"speaker": "guardian", "text": "Hello."},
            ],
            "excuse_summary": excuse_summary,
            "parent_confirmed": parent_confirmed,
            "language": "en",
        },
        status="RECEIVED",
    )
    async_session.add(msg)
    await async_session.flush()
    return str(msg.id)


async def test_list_voice_calls_returns_camelcase_envelope(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    seeded = await _seed_school(async_session)
    student_id = seeded["students"][0].id  # type: ignore[index]
    msg_id = await _seed_voice_call(async_session, student_id=student_id)

    response = await client.get("/api/voice-calls")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    row = body[0]
    assert row["id"] == msg_id
    assert row["studentId"] == str(student_id)
    assert row["studentName"] == "Alice Garcia"
    assert row["scenario"] == "absentee"
    assert row["excuseSummary"] == "Doctor appointment."
    assert row["parentConfirmed"] is True
    assert "transcript" not in row  # summary endpoint excludes transcript


async def test_list_voice_calls_filters_by_student(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    seeded = await _seed_school(async_session)
    s_a = seeded["students"][0].id  # type: ignore[index]
    s_b = seeded["students"][1].id  # type: ignore[index]
    await _seed_voice_call(async_session, student_id=s_a)
    await _seed_voice_call(async_session, student_id=s_b)

    response = await client.get("/api/voice-calls", params={"student_id": str(s_a)})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["studentId"] == str(s_a)


async def test_get_voice_call_returns_full_transcript(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    seeded = await _seed_school(async_session)
    student_id = seeded["students"][0].id  # type: ignore[index]
    msg_id = await _seed_voice_call(async_session, student_id=student_id)

    response = await client.get(f"/api/voice-calls/{msg_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == msg_id
    assert len(body["transcript"]) == 2
    assert body["transcript"][0]["speaker"] == "agent"
    assert body["transcript"][1]["speaker"] == "guardian"


async def test_get_voice_call_404_for_unknown(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/voice-calls/{uuid4()}")
    assert response.status_code == 404


async def test_get_voice_call_404_for_non_voice_agent_message(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    """Looking up a parent-comms message via the voice-call endpoint must 404."""
    from datetime import UTC, datetime

    from hpao.models import AgentMessage

    seeded = await _seed_school(async_session)
    msg = AgentMessage(
        direction="INBOUND",
        counterparty="parent_comms",
        correlation_id=uuid4(),
        student_id=seeded["students"][0].id,  # type: ignore[index]
        payload={"received_at": datetime.now(UTC).isoformat(), "body": "x"},
        status="RECEIVED",
    )
    async_session.add(msg)
    await async_session.flush()

    response = await client.get(f"/api/voice-calls/{msg.id}")
    assert response.status_code == 404


# ---------- alerts ----------


async def test_list_alerts_returns_camelcase_envelope(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    from hpao.services.alerts import raise_alert

    seeded = await _seed_school(async_session)
    student_id = seeded["students"][0].id  # type: ignore[index]
    alert = await raise_alert(
        async_session,
        student_id=student_id,
        rule_key="restroom.duration_exceeded",
        severity="high",
        context={"minutes_elapsed": 17},
    )
    await async_session.flush()

    response = await client.get("/api/alerts")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    row = body[0]
    assert row["id"] == str(alert.id)
    assert row["studentId"] == str(student_id)
    assert row["studentName"] == "Alice Garcia"
    assert row["ruleKey"] == "restroom.duration_exceeded"
    assert row["severity"] == "high"
    assert row["status"] == "OPEN"
    assert row["context"] == {"minutes_elapsed": 17}


async def test_list_alerts_status_filter(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    from hpao.services.alerts import acknowledge_alert, raise_alert

    seeded = await _seed_school(async_session)
    s_a = seeded["students"][0].id  # type: ignore[index]
    s_b = seeded["students"][1].id  # type: ignore[index]
    teacher_id = seeded["teacher_id"]
    a = await raise_alert(
        async_session, student_id=s_a, rule_key="restroom.duration_exceeded", severity="high"
    )
    await raise_alert(async_session, student_id=s_b, rule_key="pfisd.18_day_max", severity="medium")
    await acknowledge_alert(async_session, alert_id=a.id, user_id=teacher_id)
    await async_session.flush()

    open_only = await client.get("/api/alerts", params={"status_filter": "OPEN"})
    ack_only = await client.get("/api/alerts", params={"status_filter": "ACKNOWLEDGED"})

    assert open_only.status_code == 200
    assert {r["studentId"] for r in open_only.json()} == {str(s_b)}
    assert ack_only.status_code == 200
    assert {r["studentId"] for r in ack_only.json()} == {str(s_a)}
