from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lizzie.db import Base, TimestampMixin

if TYPE_CHECKING:
    from lizzie.models.student import Student
    from lizzie.models.user import User


# Lowercase to match the outbound-webhook payload shape documented in CLAUDE.md.
ALERT_SEVERITIES: tuple[str, ...] = ("low", "medium", "high", "critical")
ALERT_STATUSES: tuple[str, ...] = ("OPEN", "ACKNOWLEDGED", "RESOLVED")

_SEVERITIES_LIST = ", ".join(f"'{s}'" for s in ALERT_SEVERITIES)
_STATUSES_LIST = ", ".join(f"'{s}'" for s in ALERT_STATUSES)


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"
    __table_args__ = (
        # At most one OPEN alert per (student, rule_key). ACK'd / RESOLVED rows
        # accumulate as history; a re-trigger only happens after the prior
        # alert is closed.
        Index(
            "uq_alerts_student_rule_open",
            "student_id",
            "rule_key",
            unique=True,
            postgresql_where="status = 'OPEN'",
        ),
        CheckConstraint(f"severity IN ({_SEVERITIES_LIST})", name="severity_valid"),
        CheckConstraint(f"status IN ({_STATUSES_LIST})", name="status_valid"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    rule_key: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="OPEN")
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    acknowledged_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    student: Mapped[Student] = relationship()
    acknowledger: Mapped[User | None] = relationship()

    def __repr__(self) -> str:
        return f"<Alert {self.severity} {self.status} {self.rule_key} student={self.student_id}>"
