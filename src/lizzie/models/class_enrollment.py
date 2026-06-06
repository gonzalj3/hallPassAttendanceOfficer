from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lizzie.db import Base, TimestampMixin

if TYPE_CHECKING:
    from lizzie.models.class_ import Class
    from lizzie.models.student import Student


class ClassEnrollment(Base, TimestampMixin):
    __tablename__ = "class_enrollments"
    __table_args__ = (
        UniqueConstraint("class_id", "student_id", name="uq_class_enrollments_class_student"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id"), nullable=False)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("students.id"), nullable=False)
    enrolled_at: Mapped[date] = mapped_column(Date, nullable=False)

    class_: Mapped[Class] = relationship(back_populates="enrollments")
    student: Mapped[Student] = relationship(back_populates="enrollments")
