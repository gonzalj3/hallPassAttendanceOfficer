"""audit log + user last_sign_in_at

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-05

MVP-cut cleanup migration:
- Adds ``users.last_sign_in_at`` so the role-picker login flow can record
  when a session was last established (used for the "Signed in just now"
  hint in the principal dashboard).
- Adds an append-only ``audit_log`` table. Even in demo mode it records
  every hall-pass mutation and every admin roster read; a future pilot
  upgrade enables FERPA disclosure logging without a schema change.

DB-level renames (hpao -> lizzie) are NOT in this migration -- a database
rename happens outside the migration chain (fresh ``CREATE DATABASE
lizzie`` in docker-compose and Railway).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_sign_in_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_role", sa.String(length=20), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "context",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_audit_log_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index(
        op.f("ix_audit_log_occurred_at"),
        "audit_log",
        ["occurred_at"],
    )
    op.create_index(
        op.f("ix_audit_log_target"),
        "audit_log",
        ["target_type", "target_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_log_target"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_occurred_at"), table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_column("users", "last_sign_in_at")
