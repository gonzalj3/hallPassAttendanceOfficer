from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from lizzie.models import ALERT_SEVERITIES, Alert, HallPass
from lizzie.services.hall_pass import (
    find_overdue_active_passes,
    mark_overdue,
)


class AlertValidationError(ValueError):
    """Raised when severity or status arg is invalid."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _rule_key_for_overdue_pass(destination: str) -> str:
    return f"hallpass.{destination.lower()}.duration_exceeded"


def _severity_for_overdue_pass(destination: str) -> str:
    # RESTROOM going long is the headline demo case -> high. Other destinations
    # default to medium since they have legitimate longer expected durations.
    return "high" if destination == "RESTROOM" else "medium"


async def get_open_alert_for(db: AsyncSession, *, student_id: UUID, rule_key: str) -> Alert | None:
    stmt = select(Alert).where(
        Alert.student_id == student_id,
        Alert.rule_key == rule_key,
        Alert.status == "OPEN",
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def raise_alert(
    db: AsyncSession,
    *,
    student_id: UUID,
    rule_key: str,
    severity: str,
    context: dict[str, Any] | None = None,
) -> Alert:
    """Raise an alert. Idempotent on (student_id, rule_key) while OPEN.

    If an OPEN alert already exists for the same (student, rule_key), returns
    that alert unchanged. The DB partial unique index makes this race-safe:
    even if two concurrent callers both miss the SELECT, the second INSERT
    fails with IntegrityError instead of duplicating.
    """
    if severity not in ALERT_SEVERITIES:
        raise AlertValidationError(f"severity {severity!r} not in {ALERT_SEVERITIES}")

    existing = await get_open_alert_for(db, student_id=student_id, rule_key=rule_key)
    if existing is not None:
        return existing

    alert = Alert(
        student_id=student_id,
        rule_key=rule_key,
        severity=severity,
        status="OPEN",
        context=context or {},
    )
    db.add(alert)
    await db.flush()
    return alert


async def acknowledge_alert(
    db: AsyncSession,
    *,
    alert_id: UUID,
    user_id: UUID,
    now: datetime | None = None,
) -> Alert:
    alert = await db.get(Alert, alert_id)
    if alert is None:
        raise AlertValidationError(f"alert {alert_id} not found")
    if alert.status != "OPEN":
        raise AlertValidationError(f"cannot acknowledge alert {alert_id}: status is {alert.status}")
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_by = user_id
    alert.acknowledged_at = now or _utcnow()
    await db.flush()
    return alert


async def resolve_alert(
    db: AsyncSession,
    *,
    alert_id: UUID,
    now: datetime | None = None,
) -> Alert:
    alert = await db.get(Alert, alert_id)
    if alert is None:
        raise AlertValidationError(f"alert {alert_id} not found")
    if alert.status == "RESOLVED":
        return alert  # idempotent
    alert.status = "RESOLVED"
    alert.resolved_at = now or _utcnow()
    await db.flush()
    return alert


async def list_open_alerts(db: AsyncSession) -> list[Alert]:
    stmt = select(Alert).where(Alert.status == "OPEN").order_by(Alert.created_at.desc())
    return list((await db.execute(stmt)).scalars().all())


async def list_alerts_for_student(db: AsyncSession, *, student_id: UUID) -> list[Alert]:
    stmt = select(Alert).where(Alert.student_id == student_id).order_by(Alert.created_at.desc())
    return list((await db.execute(stmt)).scalars().all())


def _build_overdue_context(hp: HallPass, cutoff: datetime) -> dict[str, Any]:
    elapsed_minutes = (cutoff - hp.checked_out_at).total_seconds() / 60
    return {
        "hall_pass_id": str(hp.id),
        "destination": hp.destination,
        "checked_out_at": hp.checked_out_at.isoformat(),
        "expected_return_at": hp.expected_return_at.isoformat(),
        "minutes_elapsed": round(elapsed_minutes, 1),
    }


async def detect_overdue_passes(
    db: AsyncSession,
    *,
    now: datetime | None = None,
) -> list[Alert]:
    """Find ACTIVE passes past their expected return, mark them OVERDUE, and
    raise a hallpass.<destination>.duration_exceeded alert per pass.

    Idempotent at every step: re-running with the same clock returns the same
    alerts. Phase 7 / app integration will wrap this in a periodic asyncio
    task that wakes every N seconds.
    """
    cutoff = now or _utcnow()
    overdue = await find_overdue_active_passes(db, now=cutoff)

    alerts: list[Alert] = []
    for hp in overdue:
        await mark_overdue(db, pass_id=hp.id, now=cutoff)
        alert = await raise_alert(
            db,
            student_id=hp.student_id,
            rule_key=_rule_key_for_overdue_pass(hp.destination),
            severity=_severity_for_overdue_pass(hp.destination),
            context=_build_overdue_context(hp, cutoff),
        )
        alerts.append(alert)
    return alerts
