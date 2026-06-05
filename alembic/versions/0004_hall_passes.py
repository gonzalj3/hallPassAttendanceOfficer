"""hall passes

Revision ID: 0004
Revises: 0002
Create Date: 2026-05-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hall_passes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "originating_class_session_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("destination", sa.String(length=12), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_return_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("issued_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_hall_passes_student_id_students"),
        ),
        sa.ForeignKeyConstraint(
            ["originating_class_session_id"],
            ["class_sessions.id"],
            name=op.f("fk_hall_passes_originating_class_session_id_class_sessions"),
        ),
        sa.ForeignKeyConstraint(
            ["issued_by"],
            ["users.id"],
            name=op.f("fk_hall_passes_issued_by_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hall_passes")),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'RETURNED', 'OVERDUE', 'FLAGGED')",
            name=op.f("ck_hall_passes_status_valid"),
        ),
        sa.CheckConstraint(
            "destination IN ('RESTROOM', 'NURSE', 'COUNSELOR', 'OFFICE', 'OTHER')",
            name=op.f("ck_hall_passes_destination_valid"),
        ),
    )
    # Partial unique index: at most one ACTIVE pass per student.
    op.create_index(
        "uq_hall_passes_student_active",
        "hall_passes",
        ["student_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index("uq_hall_passes_student_active", table_name="hall_passes")
    op.drop_table("hall_passes")
