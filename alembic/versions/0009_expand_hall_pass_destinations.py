"""expand hall pass destinations to include HALLWAY and CLASSROOM

Revision ID: 0009
Revises: 0007
Create Date: 2026-05-09

The frontend roster UX needs short-trip destinations (water-fountain /
locker visits, brief teacher meetings) that the original 5-value enum
couldn't express. Adds HALLWAY and CLASSROOM so the API speaks the
frontend's vocabulary directly without a translation layer.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Wrap in op.f() so the naming convention isn't reapplied on top of the
# already-formatted name we got from migration 0004.
CONSTRAINT_NAME = op.f("ck_hall_passes_destination_valid")
NEW_DESTINATIONS = (
    "'RESTROOM'",
    "'NURSE'",
    "'COUNSELOR'",
    "'OFFICE'",
    "'OTHER'",
    "'HALLWAY'",
    "'CLASSROOM'",
)
OLD_DESTINATIONS = ("'RESTROOM'", "'NURSE'", "'COUNSELOR'", "'OFFICE'", "'OTHER'")


def upgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "hall_passes", type_="check")
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "hall_passes",
        f"destination IN ({', '.join(NEW_DESTINATIONS)})",
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "hall_passes", type_="check")
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "hall_passes",
        f"destination IN ({', '.join(OLD_DESTINATIONS)})",
    )
