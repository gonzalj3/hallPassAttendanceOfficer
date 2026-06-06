"""End-to-end tests for the role-picker auth flow."""

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from lizzie.api.frontend import _get_session as _frontend_get_session
from lizzie.app import make_app
from lizzie.auth.dependencies import _get_db_session as _auth_get_session
from lizzie.models import School, User

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def client(
    migrated_database: str, async_session: AsyncSession
) -> AsyncIterator[httpx.AsyncClient]:
    app = make_app(migrated_database, session_secret="integration-test-secret")

    async def session_dep() -> AsyncIterator[AsyncSession]:
        yield async_session

    app.dependency_overrides[_frontend_get_session] = session_dep
    app.dependency_overrides[_auth_get_session] = session_dep

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _seed_two_users(async_session: AsyncSession) -> tuple[User, User]:
    school = School(name="Auth Test School", district="Test ISD")
    async_session.add(school)
    await async_session.flush()
    teacher = User(
        school_id=school.id,
        email="t@auth-test.edu",
        role="TEACHER",
        first_name="Ms.",
        last_name="Rivera",
    )
    admin = User(
        school_id=school.id,
        email="a@auth-test.edu",
        role="ADMIN",
        first_name="Dr.",
        last_name="Chen",
    )
    async_session.add_all([teacher, admin])
    await async_session.flush()
    return teacher, admin


async def test_role_pick_returns_user_and_sets_cookie(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    teacher, _ = await _seed_two_users(async_session)
    response = await client.post("/auth/role-pick", json={"role": "TEACHER"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "TEACHER"
    assert body["name"] == "Ms. Rivera"
    assert body["user_id"] == str(teacher.id)
    assert "lizzie_session" in response.cookies


async def test_role_pick_admin_path(client: httpx.AsyncClient, async_session: AsyncSession) -> None:
    _, admin = await _seed_two_users(async_session)
    response = await client.post("/auth/role-pick", json={"role": "ADMIN"})
    assert response.status_code == 200
    assert response.json()["user_id"] == str(admin.id)


async def test_role_pick_rejects_unknown_role(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    await _seed_two_users(async_session)
    response = await client.post("/auth/role-pick", json={"role": "PRINCIPAL"})
    assert response.status_code == 400


async def test_role_pick_404_when_no_user_seeded(client: httpx.AsyncClient) -> None:
    response = await client.post("/auth/role-pick", json={"role": "TEACHER"})
    assert response.status_code == 404


async def test_me_returns_401_without_cookie(client: httpx.AsyncClient) -> None:
    response = await client.get("/auth/me")
    assert response.status_code == 401


async def test_full_login_then_me_cycle(
    client: httpx.AsyncClient, async_session: AsyncSession
) -> None:
    await _seed_two_users(async_session)
    pick = await client.post("/auth/role-pick", json={"role": "ADMIN"})
    assert pick.status_code == 200

    me = await client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "ADMIN"
    assert me.json()["name"] == "Dr. Chen"


async def test_logout_clears_cookie(client: httpx.AsyncClient, async_session: AsyncSession) -> None:
    await _seed_two_users(async_session)
    await client.post("/auth/role-pick", json={"role": "TEACHER"})
    assert (await client.get("/auth/me")).status_code == 200

    logout = await client.post("/auth/logout")
    assert logout.status_code == 204

    client.cookies.clear()
    assert (await client.get("/auth/me")).status_code == 401
