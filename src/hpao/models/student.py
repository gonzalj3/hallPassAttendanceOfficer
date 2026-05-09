from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hpao.db import Base, TimestampMixin

if TYPE_CHECKING:
    from hpao.models.class_enrollment import ClassEnrollment
    from hpao.models.school import School


GRADE_LEVELS: tuple[str, ...] = (
    "K",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11",
    "12",
)

_GRADE_IN_LIST = ", ".join(f"'{g}'" for g in GRADE_LEVELS)


class Student(Base, TimestampMixin):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("school_id", "student_number", name="uq_students_school_student_number"),
        CheckConstraint(
            f"grade_level IN ({_GRADE_IN_LIST})",
            name="grade_level_valid",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    school_id: Mapped[UUID] = mapped_column(ForeignKey("schools.id"), nullable=False)
    student_number: Mapped[str] = mapped_column(String(50), nullable=False)
    grade_level: Mapped[str] = mapped_column(String(2), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    enrolled_at: Mapped[date] = mapped_column(Date, nullable=False)

    school: Mapped[School] = relationship(back_populates="students")
    enrollments: Mapped[list[ClassEnrollment]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Student {self.last_name!r}, {self.first_name!r} ({self.grade_level})>"
