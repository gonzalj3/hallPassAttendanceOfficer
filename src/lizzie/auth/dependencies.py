"""FastAPI dependencies for the role-picker auth layer."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from lizzie.auth.session import verify_session


class CurrentUser(BaseModel):
    user_id: UUID
    school_id: UUID
    role: str
    name: str


# Placeholder providers; app wiring overrides via app.dependency_overrides.


def _get_session_secret() -> str:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="session secret provider not configured",
    )


def _get_db_session() -> AsyncSession:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="DB session provider not configured",
    )


def _is_production() -> bool:
    return False


SecretDep = Annotated[str, Depends(_get_session_secret)]
DbDep = Annotated[AsyncSession, Depends(_get_db_session)]
ProdDep = Annotated[bool, Depends(_is_production)]


def current_user(
    secret: SecretDep,
    lizzie_session: Annotated[str | None, Cookie()] = None,
) -> CurrentUser:
    if not lizzie_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not signed in")
    payload = verify_session(lizzie_session, secret=secret)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="session invalid or expired",
        )
    return CurrentUser(
        user_id=UUID(payload["user_id"]),
        school_id=UUID(payload["school_id"]),
        role=str(payload["role"]),
        name=str(payload["name"]),
    )


CurrentUserDep = Annotated[CurrentUser, Depends(current_user)]


def require_role(*roles: str) -> Callable[[CurrentUser], CurrentUser]:
    allowed = set(roles)

    def _enforce(user: CurrentUserDep) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"role {user.role} not in {sorted(allowed)}",
            )
        return user

    return _enforce


__all__ = [
    "CurrentUser",
    "CurrentUserDep",
    "DbDep",
    "ProdDep",
    "SecretDep",
    "current_user",
    "require_role",
]
