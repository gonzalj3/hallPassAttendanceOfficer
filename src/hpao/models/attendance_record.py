from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hpao.db import Base, TimestampMixin

if TYPE_CHECKING:
    from hpao.models.class_session import ClassSession
    from hpao.models.student import Student
    from hpao.models.user import User


ATTENDANCE_STATUSES: tuple[str, ...] = (
    "PRESENT",
    "ABSENT",
    "TARDY",
    "EXCUSED",
    "UNEXCUSED",
)
ATTENDANCE_SOURCES: tuple[str, ...] = ("TEACHER", "AGENT", "IMPORT")

_STATUSES_LIST = ", ".join(f"'{s}'" for s in ATTENDANCE_STATUSES)
_SOURCES_LIST = ", ".join(f"'{s}'" for s in ATTENDANCE_SOURCES)


class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint(
            "class_session_id",
            "student_id",
            name="uq_attendance_records_session_student",
        ),
        CheckConstraint(f"status IN ({_STATUSES_LIST})", name="status_valid"),
        CheckConstraint(f"source IN ({_SOURCES_LIST})", name="source_valid"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    class_session_id: Mapped[UUID] = mapped_column(ForeignKey("class_sessions.id"), nullable=False)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    source: Mapped[str] = mapped_column(String(12), nullable=False)
    recorded_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    class_session: Mapped[ClassSession] = relationship()
    student: Mapped[Student] = relationship()
    recorder: Mapped[User | None] = relationship()

    def __repr__(self) -> str:
        return (
            f"<AttendanceRecord {self.status} student={self.student_id} "
            f"session={self.class_session_id}>"
        )
