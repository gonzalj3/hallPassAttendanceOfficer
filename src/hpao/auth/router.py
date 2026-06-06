"""POST /auth/role-pick, GET /auth/me, POST /auth/logout."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, FastAPI, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select

from hpao.auth.dependencies import (
    CurrentUserDep,
    DbDep,
    ProdDep,
    SecretDep,
    _get_db_session,
    _get_session_secret,
    _is_production,
)
from hpao.auth.session import MAX_AGE_SECONDS, SESSION_COOKIE, sign_session
from hpao.models import User

DEMO_ROLES = ("TEACHER", "ADMIN")


class RolePickIn(BaseModel):
    role: str


class CurrentUserOut(BaseModel):
    user_id: UUID
    school_id: UUID
    role: str
    name: str


router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str, *, prod: bool) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=MAX_AGE_SECONDS,
        httponly=True,
        secure=prod,
        samesite="none" if prod else "lax",
        path="/",
    )


@router.post("/role-pick", response_model=CurrentUserOut)
async def role_pick(
    payload: RolePickIn,
    response: Response,
    db: DbDep,
    secret: SecretDep,
    prod: ProdDep,
) -> CurrentUserOut:
    role = payload.role.upper()
    if role not in DEMO_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"role must be one of {list(DEMO_ROLES)}",
        )

    user = (await db.execute(select(User).where(User.role == role).limit(1))).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"no demo user seeded with role {role}",
        )

    user.last_sign_in_at = datetime.now(UTC)
    await db.flush()

    name = f"{user.first_name} {user.last_name}"
    token = sign_session(
        {
            "user_id": str(user.id),
            "school_id": str(user.school_id),
            "role": user.role,
            "name": name,
        },
        secret=secret,
    )
    _set_session_cookie(response, token, prod=prod)
    return CurrentUserOut(
        user_id=user.id,
        school_id=user.school_id,
        role=user.role,
        name=name,
    )


@router.get("/me", response_model=CurrentUserOut)
async def me(user: CurrentUserDep) -> CurrentUserOut:
    return CurrentUserOut(**user.model_dump())


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> Response:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


def mount(
    app: FastAPI,
    *,
    session_provider: Callable[[], Any] | None = None,
    session_secret: str,
    is_production: bool = False,
) -> None:
    """Wire the auth router and its dependency providers into a FastAPI app."""
    app.include_router(router)
    if session_provider is not None:
        app.dependency_overrides[_get_db_session] = session_provider
    app.dependency_overrides[_get_session_secret] = lambda: session_secret
    app.dependency_overrides[_is_production] = lambda: is_production
