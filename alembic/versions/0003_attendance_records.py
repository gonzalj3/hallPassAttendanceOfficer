"""attendance records

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attendance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("source", sa.String(length=12), nullable=False),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
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
            ["class_session_id"],
            ["class_sessions.id"],
            name=op.f("fk_attendance_records_class_session_id_class_sessions"),
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_attendance_records_student_id_students"),
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by"],
            ["users.id"],
            name=op.f("fk_attendance_records_recorded_by_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attendance_records")),
        sa.UniqueConstraint(
            "class_session_id",
            "student_id",
            name="uq_attendance_records_session_student",
        ),
        sa.CheckConstraint(
            "status IN ('PRESENT', 'ABSENT', 'TARDY', 'EXCUSED', 'UNEXCUSED')",
            name=op.f("ck_attendance_records_status_valid"),
        ),
        sa.CheckConstraint(
            "source IN ('TEACHER', 'AGENT', 'IMPORT')",
            name=op.f("ck_attendance_records_source_valid"),
        ),
    )


def downgrade() -> None:
    op.drop_table("attendance_records")
