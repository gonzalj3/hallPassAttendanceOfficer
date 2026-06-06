"""The monitor loop: detect overdue hall passes and raise alerts.

One iteration calls `detect_overdue_passes`, which marks any ACTIVE pass
past its expected_return as OVERDUE and inserts an Alert row. The
realtime layer (pg_notify) fans the resulting `alert.raised` event out
to subscribed dashboards.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lizzie.models import Alert
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
    """One cycle of the monitor loop. Caller manages the transaction."""
    new_alerts = await detect_overdue_passes(db, now=now)
    return DispatchCycleResult(new_alerts=new_alerts)


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
