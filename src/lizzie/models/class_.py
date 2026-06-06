from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lizzie.db import Base, TimestampMixin

if TYPE_CHECKING:
    from lizzie.models.class_enrollment import ClassEnrollment
    from lizzie.models.class_session import ClassSession
    from lizzie.models.school import School
    from lizzie.models.user import User


class Class(Base, TimestampMixin):
    __tablename__ = "classes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    school_id: Mapped[UUID] = mapped_column(ForeignKey("schools.id"), nullable=False)
    teacher_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(100), nullable=True)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    room: Mapped[str | None] = mapped_column(String(50), nullable=True)

    school: Mapped[School] = relationship()
    teacher: Mapped[User] = relationship(back_populates="classes_taught")
    enrollments: Mapped[list[ClassEnrollment]] = relationship(
        back_populates="class_", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[ClassSession]] = relationship(
        back_populates="class_", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Class {self.name!r} period {self.period!r}>"
