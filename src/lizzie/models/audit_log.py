from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from lizzie.db import Base


class AuditLog(Base):
    """Append-only record of PII-touching actions.

    Cheap to insert (single INSERT, no constraints beyond the FK), cheap
    to query (indexed on occurred_at and on the (target_type, target_id)
    pair). Designed to upgrade to FERPA disclosure logging without a
    schema change -- a pilot release just starts requiring rows for read
    paths too.
    """

    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[UUID | None] = mapped_column(nullable=True)
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} on {self.target_type}:{self.target_id}>"
