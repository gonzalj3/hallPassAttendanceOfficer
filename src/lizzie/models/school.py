from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lizzie.db import Base, TimestampMixin

if TYPE_CHECKING:
    from lizzie.models.student import Student


class School(Base, TimestampMixin):
    __tablename__ = "schools"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    district: Mapped[str | None] = mapped_column(String(200), nullable=True)

    students: Mapped[list[Student]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<School {self.name!r}>"
