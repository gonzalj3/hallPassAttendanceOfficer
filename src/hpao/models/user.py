from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hpao.db import Base, TimestampMixin

if TYPE_CHECKING:
    from hpao.models.class_ import Class
    from hpao.models.school import School


USER_ROLES: tuple[str, ...] = ("TEACHER", "ADMIN", "COUNSELOR", "NURSE")
_ROLES_LIST = ", ".join(f"'{r}'" for r in USER_ROLES)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint(f"role IN ({_ROLES_LIST})", name="role_valid"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    school_id: Mapped[UUID] = mapped_column(ForeignKey("schools.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    school: Mapped[School] = relationship()
    classes_taught: Mapped[list[Class]] = relationship(back_populates="teacher")

    def __repr__(self) -> str:
        return f"<User {self.role} {self.last_name!r}, {self.first_name!r}>"
