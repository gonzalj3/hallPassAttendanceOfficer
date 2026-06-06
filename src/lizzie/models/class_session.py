from __future__ import annotations

from datetime import date as date_type
from datetime import time
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Date, ForeignKey, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lizzie.db import Base, TimestampMixin

if TYPE_CHECKING:
    from lizzie.models.class_ import Class


class ClassSession(Base, TimestampMixin):
    __tablename__ = "class_sessions"
    __table_args__ = (UniqueConstraint("class_id", "date", name="uq_class_sessions_class_date"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    class_id: Mapped[UUID] = mapped_column(ForeignKey("classes.id"), nullable=False)
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    scheduled_start: Mapped[time] = mapped_column(Time, nullable=False)
    scheduled_end: Mapped[time] = mapped_column(Time, nullable=False)

    class_: Mapped[Class] = relationship(back_populates="sessions")

    def __repr__(self) -> str:
        return f"<ClassSession {self.date.isoformat()} {self.scheduled_start}>"
