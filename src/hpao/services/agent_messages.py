from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.models import AgentMessage


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def find_by_correlation(
    db: AsyncSession, *, direction: str, correlation_id: UUID
) -> AgentMessage | None:
    stmt = select(AgentMessage).where(
        AgentMessage.direction == direction,
        AgentMessage.correlation_id == correlation_id,
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def log_inbound(
    db: AsyncSession,
    *,
    counterparty: str,
    correlation_id: UUID,
    payload: dict[str, Any],
    student_id: UUID | None = None,
    alert_id: UUID | None = None,
) -> tuple[AgentMessage, bool]:
    """Idempotent INBOUND log. Returns (message, duplicate).

    If a message with this (INBOUND, correlation_id) already exists, returns
    it unchanged with duplicate=True. Lets the parent-comms agent retry
    without creating duplicates.
    """
    existing = await find_by_correlation(db, direction="INBOUND", correlation_id=correlation_id)
    if existing is not None:
        return existing, True

    msg = AgentMessage(
        direction="INBOUND",
        counterparty=counterparty,
        correlation_id=correlation_id,
        student_id=student_id,
        alert_id=alert_id,
        payload=payload,
        status="RECEIVED",
    )
    db.add(msg)
    await db.flush()
    return msg, False


async def record_outbound_pending(
    db: AsyncSession,
    *,
    counterparty: str,
    correlation_id: UUID,
    payload: dict[str, Any],
    student_id: UUID | None = None,
    alert_id: UUID | None = None,
) -> AgentMessage:
    """Create an OUTBOUND row in PENDING state before HTTP delivery."""
    msg = AgentMessage(
        direction="OUTBOUND",
        counterparty=counterparty,
        correlation_id=correlation_id,
        student_id=student_id,
        alert_id=alert_id,
        payload=payload,
        status="PENDING",
    )
    db.add(msg)
    await db.flush()
    return msg


async def mark_sent(
    db: AsyncSession, *, message_id: UUID, now: datetime | None = None
) -> AgentMessage:
    msg = await db.get(AgentMessage, message_id)
    if msg is None:
        raise ValueError(f"agent_message {message_id} not found")
    msg.status = "SENT"
    msg.sent_at = now or _utcnow()
    await db.flush()
    return msg


async def mark_failed(db: AsyncSession, *, message_id: UUID, error: str) -> AgentMessage:
    msg = await db.get(AgentMessage, message_id)
    if msg is None:
        raise ValueError(f"agent_message {message_id} not found")
    msg.status = "FAILED"
    msg.error = error
    await db.flush()
    return msg
