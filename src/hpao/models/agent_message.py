from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hpao.db import Base, TimestampMixin

if TYPE_CHECKING:
    from hpao.models.alert import Alert
    from hpao.models.student import Student


AGENT_MESSAGE_DIRECTIONS: tuple[str, ...] = ("INBOUND", "OUTBOUND")
AGENT_MESSAGE_STATUSES: tuple[str, ...] = (
    "PENDING",  # outbound, not yet sent
    "SENT",  # outbound, delivered to counterparty
    "FAILED",  # outbound, delivery failed
    "RECEIVED",  # inbound, accepted and logged
)

_DIRECTIONS_LIST = ", ".join(f"'{d}'" for d in AGENT_MESSAGE_DIRECTIONS)
_STATUSES_LIST = ", ".join(f"'{s}'" for s in AGENT_MESSAGE_STATUSES)


class AgentMessage(Base, TimestampMixin):
    """Append-only log of every cross-agent boundary call.

    INBOUND: parent-comms agent called us (parent-message, parent-response).
    OUTBOUND: we called parent-comms (alert.raised notifications).

    The actual SMS / email / phone transcript lives in parent-comms; this
    table stores the structured intent / response that crossed the wire.
    """

    __tablename__ = "agent_messages"
    __table_args__ = (
        # Idempotency: same correlation_id from the same direction returns
        # the existing row instead of duplicating. Lets the parent-comms
        # agent retry safely.
        UniqueConstraint(
            "direction",
            "correlation_id",
            name="uq_agent_messages_direction_correlation",
        ),
        CheckConstraint(f"direction IN ({_DIRECTIONS_LIST})", name="direction_valid"),
        CheckConstraint(f"status IN ({_STATUSES_LIST})", name="status_valid"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    counterparty: Mapped[str] = mapped_column(String(50), nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(nullable=False)
    student_id: Mapped[UUID | None] = mapped_column(ForeignKey("students.id"), nullable=True)
    alert_id: Mapped[UUID | None] = mapped_column(ForeignKey("alerts.id"), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    student: Mapped[Student | None] = relationship()
    alert: Mapped[Alert | None] = relationship()

    def __repr__(self) -> str:
        return (
            f"<AgentMessage {self.direction} {self.counterparty} "
            f"corr={self.correlation_id} status={self.status}>"
        )
