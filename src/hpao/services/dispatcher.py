"""The demo loop: detect overdue hall passes and fire outbound alerts.

This is the glue between Phase 6 (alerts) and Phase 8 (parent-comms
boundary). One iteration:

1. detect_overdue_passes -- mark any ACTIVE pass past its expected_return
   as OVERDUE and raise an alert (Phase 6).
2. Find OPEN alerts that haven't yet been dispatched as OUTBOUND
   agent_messages, including ones from previous cycles whose dispatch
   failed (so transient parent-comms outages auto-recover).
3. POST each as a signed webhook to parent-comms (Phase 8).

If `parent_comms_base_url` or `parent_comms_secret` is missing, step 1
still runs so passes get OVERDUE'd correctly, but step 3 is skipped
(useful for dev / demo without a parent-comms agent up).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hpao.integrations.parent_comms import dispatch_alert
from hpao.models import AgentMessage, Alert
from hpao.services.alerts import detect_overdue_passes

logger = logging.getLogger(__name__)


@dataclass
class DispatchCycleResult:
    """Returned from one cycle so callers (and tests) can see what happened."""

    new_alerts: list[Alert] = field(default_factory=list)
    dispatched: list[AgentMessage] = field(default_factory=list)
    skipped_no_config: bool = False


async def find_pending_dispatch_alerts(db: AsyncSession) -> list[Alert]:
    """OPEN alerts that don't yet have an OUTBOUND agent_message in
    SENT or PENDING state.

    Includes alerts from previous failed cycles -- a transient
    parent-comms 5xx leaves the agent_message in FAILED, which is
    excluded here, so the next cycle picks the alert up and retries.
    """
    sent_or_pending = select(AgentMessage.alert_id).where(
        AgentMessage.direction == "OUTBOUND",
        AgentMessage.status.in_(("SENT", "PENDING")),
        AgentMessage.alert_id.is_not(None),
    )
    stmt = (
        select(Alert)
        .where(
            Alert.status == "OPEN",
            Alert.id.notin_(sent_or_pending),
        )
        .order_by(Alert.created_at.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def run_alert_dispatch_cycle(
    db: AsyncSession,
    *,
    parent_comms_base_url: str | None,
    parent_comms_secret: str | None,
    now: datetime | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> DispatchCycleResult:
    """One cycle of the demo loop. Caller manages the transaction."""
    new_alerts = await detect_overdue_passes(db, now=now)

    if not parent_comms_base_url or not parent_comms_secret:
        return DispatchCycleResult(new_alerts=new_alerts, dispatched=[], skipped_no_config=True)

    pending = await find_pending_dispatch_alerts(db)
    dispatched: list[AgentMessage] = []
    for alert in pending:
        msg = await dispatch_alert(
            db,
            alert=alert,
            base_url=parent_comms_base_url,
            secret=parent_comms_secret,
            http_client=http_client,
        )
        dispatched.append(msg)
    return DispatchCycleResult(new_alerts=new_alerts, dispatched=dispatched)


async def run_periodic_dispatcher(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    parent_comms_base_url: str | None,
    parent_comms_secret: str | None,
    interval_seconds: float = 30.0,
    max_iterations: int | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> int:
    """Run cycles forever, sleeping `interval_seconds` between them.

    Returns the number of iterations completed. `max_iterations` exists for
    tests; production callers leave it None and cancel the task on shutdown.

    Exceptions in a cycle are logged and the loop continues -- a single bad
    cycle (DB blip, parent-comms outage) shouldn't kill the demo.
    """
    if not parent_comms_base_url or not parent_comms_secret:
        logger.warning(
            "dispatcher: parent_comms_url or parent_comms_secret unset; "
            "outbound webhooks will be skipped, only state hygiene runs"
        )

    iterations = 0
    while True:
        try:
            async with session_factory() as db, db.begin():
                await run_alert_dispatch_cycle(
                    db,
                    parent_comms_base_url=parent_comms_base_url,
                    parent_comms_secret=parent_comms_secret,
                    http_client=http_client,
                )
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
