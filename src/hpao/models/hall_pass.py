from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hpao.db import Base, TimestampMixin

if TYPE_CHECKING:
    from hpao.models.class_session import ClassSession
    from hpao.models.student import Student
    from hpao.models.user import User


HALL_PASS_STATUSES: tuple[str, ...] = ("ACTIVE", "RETURNED", "OVERDUE", "FLAGGED")
HALL_PASS_DESTINATIONS: tuple[str, ...] = (
    "RESTROOM",
    "NURSE",
    "COUNSELOR",
    "OFFICE",
    "OTHER",
)

_STATUSES_LIST = ", ".join(f"'{s}'" for s in HALL_PASS_STATUSES)
_DESTINATIONS_LIST = ", ".join(f"'{d}'" for d in HALL_PASS_DESTINATIONS)


class HallPass(Base, TimestampMixin):
    __tablename__ = "hall_passes"
    __table_args__ = (
        # Partial unique index: only one ACTIVE pass per student. RETURNED /
        # OVERDUE / FLAGGED rows for the same student are allowed to accumulate
        # as a history.
        Index(
            "uq_hall_passes_student_active",
            "student_id",
            unique=True,
            postgresql_where="status = 'ACTIVE'",
        ),
        CheckConstraint(f"status IN ({_STATUSES_LIST})", name="status_valid"),
        CheckConstraint(f"destination IN ({_DESTINATIONS_LIST})", name="destination_valid"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    originating_class_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("class_sessions.id"), nullable=False
    )
    destination: Mapped[str] = mapped_column(String(12), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    checked_out_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_return_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="ACTIVE")
    issued_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    student: Mapped[Student] = relationship()
    originating_class_session: Mapped[ClassSession] = relationship()
    issuer: Mapped[User] = relationship()

    def __repr__(self) -> str:
        return f"<HallPass {self.status} {self.destination} student={self.student_id}>"
