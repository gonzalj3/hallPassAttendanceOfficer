"""DELETE /api/admin/students/{id} -- cascade + audit + role gating."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.api.admin import _get_session as _admin_get_session
from hpao.api.frontend import _get_session as _frontend_get_session
from hpao.app import make_app
from hpao.auth.dependencies import _get_db_session as _auth_get_session
from hpao.models import (
    Alert,
    AuditLog,
    Class,
    ClassEnrollment,
    ClassSession,
    HallPass,
    School,
    Student,
    User,
)

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def client(
    migrated_database: str, async_session: AsyncSession
) -> AsyncIterator[httpx.AsyncClient]:
    app = make_app(migrated_database, session_secret="admin-test-secret")

    async def session_dep() -> AsyncIterator[AsyncSession]:
        yield async_session

    app.dependency_overrides[_frontend_get_session] = session_dep
    app.dependency_overrides[_admin_get_session] = session_dep
    app.dependency_overrides[_auth_get_session] = session_dep

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _seed(async_session: AsyncSession) -> dict[str, object]:
    """A school with both roles, one class, one student carrying 2 passes + 1 alert."""
    school = School(name="Admin Test School", district="Test ISD")
    async_session.add(school)
    await async_session.flush()

    teacher = User(
        school_id=school.id,
        email="t@a.edu",
        role="TEACHER",
        first_name="Ms.",
        last_name="Rivera",
    )
    admin = User(
        school_id=school.id,
        email="a@a.edu",
        role="ADMIN",
        first_name="Dr.",
        last_name="Chen",
    )
    async_session.add_all([teacher, admin])
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

    today = datetime.now(UTC).date()
    session = ClassSession(
        class_id=cls.id,
        date=today,
        scheduled_start=datetime.now(UTC).time().replace(microsecond=0),
        scheduled_end=(datetime.now(UTC) + timedelta(hours=1)).time().replace(microsecond=0),
    )
    async_session.add(session)
    await async_session.flush()

    student = Student(
        school_id=school.id,
        student_number="S100",
        grade_level="10",
        first_name="Doomed",
        last_name="Student",
        enrolled_at=today - timedelta(days=30),
    )
    async_session.add(student)
    await async_session.flush()

    async_session.add(ClassEnrollment(class_id=cls.id, student_id=student.id, enrolled_at=today))
    async_session.add(
        HallPass(
            student_id=student.id,
            originating_class_session_id=session.id,
            destination="RESTROOM",
            checked_out_at=datetime.now(UTC),
            expected_return_at=datetime.now(UTC) + timedelta(minutes=15),
            status="ACTIVE",
            issued_by=teacher.id,
        )
    )
    async_session.add(
        Alert(
            student_id=student.id,
            rule_key="hallpass.restroom.duration_exceeded",
            severity="high",
            status="OPEN",
            context={"minutes_elapsed": 17},
        )
    )
    await async_session.flush()
    return {"student": student, "teacher": teacher, "admin": admin}


async def _sign_in(client: httpx.AsyncClient, role: str) -> None:
    r = await client.post("/auth/role-pick", json={"role": role})
    assert r.status_code == 200, r.text


async def test_delete_student_cascades_passes_alerts_enrollments(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    seeded = await _seed(async_session)
    student = seeded["student"]  # type: ignore[assignment]
    await _sign_in(client, "ADMIN")

    r = await client.delete(f"/api/admin/students/{student.id}")  # type: ignore[attr-defined]
    assert r.status_code == 204, r.text

    # Student gone
    assert (
        await async_session.execute(
            select(Student).where(Student.id == student.id)  # type: ignore[attr-defined]
        )
    ).scalar_one_or_none() is None
    # Passes gone
    assert (
        await async_session.execute(
            select(HallPass).where(HallPass.student_id == student.id)  # type: ignore[attr-defined]
        )
    ).first() is None
    # Alerts gone
    assert (
        await async_session.execute(
            select(Alert).where(Alert.student_id == student.id)  # type: ignore[attr-defined]
        )
    ).first() is None
    # Enrollments gone
    assert (
        await async_session.execute(
            select(ClassEnrollment).where(
                ClassEnrollment.student_id == student.id  # type: ignore[attr-defined]
            )
        )
    ).first() is None
    # Audit row written
    audit = (
        await async_session.execute(select(AuditLog).where(AuditLog.action == "student.delete"))
    ).scalar_one()
    assert audit.target_id == student.id  # type: ignore[attr-defined]
    assert audit.actor_role == "ADMIN"
    assert audit.context["student_number"] == "S100"


async def test_delete_student_returns_404_for_unknown(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    await _seed(async_session)
    await _sign_in(client, "ADMIN")
    r = await client.delete(f"/api/admin/students/{uuid4()}")
    assert r.status_code == 404


async def test_delete_student_requires_admin_role(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    seeded = await _seed(async_session)
    student = seeded["student"]  # type: ignore[assignment]
    await _sign_in(client, "TEACHER")
    r = await client.delete(f"/api/admin/students/{student.id}")  # type: ignore[attr-defined]
    assert r.status_code == 403


async def test_delete_student_requires_session(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    seeded = await _seed(async_session)
    student = seeded["student"]  # type: ignore[assignment]
    # No sign-in.
    r = await client.delete(f"/api/admin/students/{student.id}")  # type: ignore[attr-defined]
    assert r.status_code == 401


async def test_issue_hall_pass_writes_audit_row(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    seeded = await _seed(async_session)
    student = seeded["student"]  # type: ignore[assignment]
    await _sign_in(client, "TEACHER")

    # Need a fresh session since the seed already gave the doomed student
    # an ACTIVE pass; use a different student to avoid the partial-unique
    # constraint.
    new_student = Student(
        school_id=student.school_id,  # type: ignore[attr-defined]
        student_number="S200",
        grade_level="10",
        first_name="Fresh",
        last_name="Kid",
        enrolled_at=datetime.now(UTC).date(),
    )
    async_session.add(new_student)
    await async_session.flush()

    # Find the class_session_id from the existing seed
    existing_pass = (await async_session.execute(select(HallPass).limit(1))).scalar_one()
    session_id = existing_pass.originating_class_session_id

    response = await client.post(
        "/api/hall-passes",
        json={
            "studentId": str(new_student.id),
            "sessionId": str(session_id),
            "destination": "RESTROOM",
        },
    )
    assert response.status_code == 201, response.text

    audits = (
        (await async_session.execute(select(AuditLog).where(AuditLog.action == "hall_pass.issue")))
        .scalars()
        .all()
    )
    assert len(audits) == 1
    assert audits[0].actor_role == "TEACHER"
    assert audits[0].context["destination"] == "RESTROOM"
