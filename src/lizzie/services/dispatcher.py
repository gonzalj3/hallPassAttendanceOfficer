"""The monitor loop: detect overdue hall passes and raise alerts.

One iteration calls `detect_overdue_passes`, which marks any ACTIVE pass
past its expected_return as OVERDUE and inserts an Alert row. Each new
Alert publishes an ``alert.raised`` event over pg_notify so the
principal dashboard's WebSocket subscription updates the moment the
transaction commits.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lizzie.models import Alert, Student
from lizzie.realtime.events import AlertRaised
from lizzie.realtime.postgres import PgNotifyPublisher
from lizzie.services.alerts import detect_overdue_passes

logger = logging.getLogger(__name__)


@dataclass
class DispatchCycleResult:
    new_alerts: list[Alert] = field(default_factory=list)


async def run_alert_dispatch_cycle(
    db: AsyncSession,
    *,
    now: datetime | None = None,
) -> DispatchCycleResult:
    """One cycle of the monitor loop. Caller manages the transaction.

    Publishes one ``alert.raised`` event per new Alert via pg_notify, so
    the principal dashboard's WebSocket subscription wakes up the moment
    the transaction commits. Without this, the dashboard only learns
    about new alerts on its next manual refetch.
    """
    new_alerts = await detect_overdue_passes(db, now=now)

    if new_alerts:
        publisher = PgNotifyPublisher(await db.connection())
        occurred_at = now or datetime.now(tz=new_alerts[0].created_at.tzinfo)
        for alert in new_alerts:
            student = await db.get(Student, alert.student_id)
            if student is None:  # FK guarantees existence; defensive
                continue
            event = AlertRaised(
                event_id=uuid4(),
                occurred_at=occurred_at,
                school_id=student.school_id,
                student_id=alert.student_id,
                alert_id=alert.id,
                rule_key=alert.rule_key,
                severity=alert.severity,
                summary=_summarize_alert(alert),
                evidence=dict(alert.context or {}),
            )
            await publisher.publish(event)

    return DispatchCycleResult(new_alerts=new_alerts)


def _summarize_alert(alert: Alert) -> str:
    """Short human-readable line for the dashboard's live activity card."""
    minutes = alert.context.get("minutes_elapsed") if alert.context else None
    destination = alert.context.get("destination") if alert.context else None
    if minutes is not None and destination:
        return f"Student out of class {minutes} min ({str(destination).lower()})"
    return alert.rule_key


async def run_periodic_dispatcher(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    interval_seconds: float = 30.0,
    max_iterations: int | None = None,
) -> int:
    """Run cycles forever, sleeping `interval_seconds` between them.

    Returns the number of iterations completed. `max_iterations` exists
    for tests; production callers leave it None and cancel the task on
    shutdown. A failed cycle (DB blip) is logged and the loop continues.
    """
    iterations = 0
    while True:
        try:
            async with session_factory() as db, db.begin():
                await run_alert_dispatch_cycle(db)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("dispatcher: cycle failed; continuing")

        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            return iterations
        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise
