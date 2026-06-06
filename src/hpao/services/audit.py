"""Thin audit-log writes.

Every PII-touching action funnels through ``write_audit`` so the audit
trail stays a single insert site to grep for. The function returns the
created row so tests can assert against it; callers usually ignore the
return value.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from hpao.auth.dependencies import CurrentUser
from hpao.models import AuditLog


async def write_audit(
    db: AsyncSession,
    *,
    user: CurrentUser,
    action: str,
    target_type: str,
    target_id: UUID | None = None,
    context: dict[str, Any] | None = None,
) -> AuditLog:
    row = AuditLog(
        user_id=user.user_id,
        actor_role=user.role,
        action=action,
        target_type=target_type,
        target_id=target_id,
        context=context or {},
    )
    db.add(row)
    await db.flush()
    return row
