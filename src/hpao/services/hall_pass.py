from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.models import HALL_PASS_DESTINATIONS, HallPass

# Per destination, how long until the pass is "overdue" by default. The
# 15-minute restroom default is the trigger for the on-duty admin alert
# in Phase 6.
DEFAULT_DURATION_MINUTES: dict[str, int] = {
    "RESTROOM": 15,
    "NURSE": 30,
    "COUNSELOR": 30,
    "OFFICE": 30,
    "OTHER": 15,
    "HALLWAY": 10,  # water fountain / locker — short trip
    "CLASSROOM": 10,  # delivery / brief teacher meeting
}


class HallPassValidationError(ValueError):
    """Raised when destination or status arg is malformed."""


class HallPassConflictError(RuntimeError):
    """Raised when a student already has an active pass."""


def default_duration_minutes(destination: str) -> int:
    """Look up the default duration for a destination. Unknown -> 15 (safe)."""
    return DEFAULT_DURATION_MINUTES.get(destination, 15)


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def get_active_pass_for_student(db: AsyncSession, *, student_id: UUID) -> HallPass | None:
    stmt = select(HallPass).where(
        HallPass.student_id == student_id,
        HallPass.status == "ACTIVE",
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def issue_pass(
    db: AsyncSession,
    *,
    student_id: UUID,
    originating_class_session_id: UUID,
    destination: str,
    issued_by: UUID,
    reason: str | None = None,
    duration_minutes: int | None = None,
    now: datetime | None = None,
) -> HallPass:
    """Issue a new hall pass. Fails fast if the student already has one ACTIVE."""
    if destination not in HALL_PASS_DESTINATIONS:
        raise HallPassValidationError(
            f"destination {destination!r} not in {HALL_PASS_DESTINATIONS}"
        )

    existing = await get_active_pass_for_student(db, student_id=student_id)
    if existing is not None:
        raise HallPassConflictError(f"student {student_id} already has active pass {existing.id}")

    checked_out_at = now or _utcnow()
    duration = duration_minutes or default_duration_minutes(destination)
    expected_return_at = checked_out_at + timedelta(minutes=duration)

    pass_ = HallPass(
        student_id=student_id,
        originating_class_session_id=originating_class_session_id,
        destination=destination,
        reason=reason,
        checked_out_at=checked_out_at,
        expected_return_at=expected_return_at,
        status="ACTIVE",
        issued_by=issued_by,
    )
    db.add(pass_)
    await db.flush()
    return pass_


async def check_in_pass(
    db: AsyncSession,
    *,
    pass_id: UUID,
    now: datetime | None = None,
) -> HallPass:
    """Mark the pass returned. RETURNED if on time, FLAGGED if late."""
    pass_ = await db.get(HallPass, pass_id)
    if pass_ is None:
        raise HallPassValidationError(f"hall pass {pass_id} not found")
    if pass_.status not in {"ACTIVE", "OVERDUE"}:
        raise HallPassValidationError(f"cannot check in pass {pass_id}: status is {pass_.status}")

    arrival = now or _utcnow()
    pass_.checked_in_at = arrival
    pass_.status = "FLAGGED" if arrival > pass_.expected_return_at else "RETURNED"
    await db.flush()
    return pass_


async def mark_overdue(
    db: AsyncSession,
    *,
    pass_id: UUID,
    now: datetime | None = None,
) -> HallPass:
    """Transition an ACTIVE pass past its expected return into OVERDUE.

    Idempotent: a pass already RETURNED / FLAGGED / OVERDUE is left alone.
    """
    pass_ = await db.get(HallPass, pass_id)
    if pass_ is None:
        raise HallPassValidationError(f"hall pass {pass_id} not found")
    if pass_.status != "ACTIVE":
        return pass_
    if (now or _utcnow()) <= pass_.expected_return_at:
        return pass_
    pass_.status = "OVERDUE"
    await db.flush()
    return pass_


async def find_overdue_active_passes(
    db: AsyncSession,
    *,
    now: datetime | None = None,
) -> list[HallPass]:
    """Return ACTIVE passes whose expected_return_at is in the past.

    Phase 6 wraps this in a periodic check that triggers alerts for the
    15-min restroom case (and any other destination's default duration).
    """
    cutoff = now or _utcnow()
    stmt = select(HallPass).where(
        HallPass.status == "ACTIVE",
        HallPass.expected_return_at < cutoff,
    )
    return list((await db.execute(stmt)).scalars().all())
