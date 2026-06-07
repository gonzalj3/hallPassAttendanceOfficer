"""GET /api/stats — real dashboard KPIs."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, time, timedelta

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from lizzie.api.admin import _get_session as _admin_get_session
from lizzie.api.frontend import _get_session as _frontend_get_session
from lizzie.app import make_app
from lizzie.auth.dependencies import _get_db_session as _auth_get_session
from lizzie.models import Class, ClassSession, HallPass, School, Student, User

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def client(
    migrated_database: str, async_session: AsyncSession
) -> AsyncIterator[httpx.AsyncClient]:
    app = make_app(migrated_database, session_secret="stats-test-secret")

    async def session_dep() -> AsyncIterator[AsyncSession]:
        yield async_session

    app.dependency_overrides[_frontend_get_session] = session_dep
    app.dependency_overrides[_admin_get_session] = session_dep
    app.dependency_overrides[_auth_get_session] = session_dep

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _seed_with_passes(async_session: AsyncSession) -> dict[str, object]:
    school = School(name="Stats School", district="ISD")
    async_session.add(school)
    await async_session.flush()

    teacher = User(
        school_id=school.id,
        email="t@stats.edu",
        role="TEACHER",
        first_name="Ms.",
        last_name="Rivera",
    )
    async_session.add(teacher)
    await async_session.flush()

    cls = Class(
        school_id=school.id,
        teacher_id=teacher.id,
        name="Math",
        subject="Mathematics",
        period="1",
        room="101",
    )
    async_session.add(cls)
    await async_session.flush()

    today = datetime.now(tz=UTC).date()
    session = ClassSession(
        class_id=cls.id,
        date=today,
        scheduled_start=time(8, 0),
        scheduled_end=time(9, 0),
    )
    async_session.add(session)
    await async_session.flush()

    students = []
    for i, (fn, ln) in enumerate(
        [("Alice", "A"), ("Bob", "B"), ("Carol", "C"), ("Dan", "D")], start=1
    ):
        s = Student(
            school_id=school.id,
            student_number=f"S{i:03d}",
            grade_level="10",
            first_name=fn,
            last_name=ln,
            enrolled_at=today,
        )
        async_session.add(s)
        students.append(s)
    await async_session.flush()

    now = datetime.now(tz=UTC)
    # One currently ACTIVE (counts toward out_now + total_issued today).
    async_session.add(
        HallPass(
            student_id=students[0].id,
            originating_class_session_id=session.id,
            destination="RESTROOM",
            status="ACTIVE",
            checked_out_at=now - timedelta(minutes=5),
            expected_return_at=now + timedelta(minutes=10),
            issued_by=teacher.id,
        )
    )
    # One OVERDUE (counts toward overdue_now + total_issued today).
    async_session.add(
        HallPass(
            student_id=students[1].id,
            originating_class_session_id=session.id,
            destination="RESTROOM",
            status="OVERDUE",
            checked_out_at=now - timedelta(minutes=30),
            expected_return_at=now - timedelta(minutes=15),
            issued_by=teacher.id,
        )
    )
    # One RETURNED today (total_issued today + returned_in_window + avg_duration).
    out = now - timedelta(minutes=20)
    inn = now - timedelta(minutes=15)  # 5 min trip
    async_session.add(
        HallPass(
            student_id=students[2].id,
            originating_class_session_id=session.id,
            destination="NURSE",
            status="RETURNED",
            checked_out_at=out,
            expected_return_at=out + timedelta(minutes=30),
            checked_in_at=inn,
            issued_by=teacher.id,
        )
    )
    # One issued yesterday (NOT today's total_issued).
    yesterday = now - timedelta(days=1)
    async_session.add(
        HallPass(
            student_id=students[3].id,
            originating_class_session_id=session.id,
            destination="OFFICE",
            status="RETURNED",
            checked_out_at=yesterday,
            expected_return_at=yesterday + timedelta(minutes=30),
            checked_in_at=yesterday + timedelta(minutes=10),
            issued_by=teacher.id,
        )
    )
    await async_session.flush()
    return {"students": students}


async def test_stats_today(client: httpx.AsyncClient, async_session: AsyncSession) -> None:
    await _seed_with_passes(async_session)
    r = await client.get("/api/stats", params={"range": "today"})
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["range"] == "today"
    assert body["outNow"] == 1  # the ACTIVE pass
    assert body["overdueNow"] == 1  # the OVERDUE pass
    assert body["totalIssued"] == 3  # active + overdue + returned today
    assert body["returnedInWindow"] == 1  # only the one checked in today
    # 5-minute trip = 300 seconds. Single sample, so avg == that.
    assert 280 <= body["avgDurationSeconds"] <= 320


async def test_stats_week_includes_yesterday(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    await _seed_with_passes(async_session)
    r = await client.get("/api/stats", params={"range": "week"})
    assert r.status_code == 200
    body = r.json()
    # 4 passes total over the last week (3 today + 1 yesterday).
    assert body["totalIssued"] == 4
    assert body["returnedInWindow"] == 2


async def test_stats_defaults_to_today(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/stats")
    assert r.status_code == 200
    assert r.json()["range"] == "today"


async def test_stats_empty_db(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["outNow"] == 0
    assert body["totalIssued"] == 0
    assert body["avgDurationSeconds"] == 0
