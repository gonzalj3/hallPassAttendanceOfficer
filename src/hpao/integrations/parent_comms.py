"""Outbound webhook client to the parent-comms agent.

HPAO emits structured intents (rule_key + severity + evidence + intent
enum) -- never message bodies. The parent-comms agent picks wording,
language, channel, opt-outs, quiet hours.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from hpao.api.security import SIGNATURE_HEADER, sign
from hpao.models import Alert
from hpao.schemas.agent import (
    OutboundContext,
    OutboundGuardianHint,
    OutboundNotification,
)
from hpao.services.agent_messages import (
    mark_failed,
    mark_sent,
    record_outbound_pending,
)

COUNTERPARTY = "parent_comms"


def build_alert_notification(
    alert: Alert,
    *,
    correlation_id: UUID | None = None,
    intent: str = "notify",
    guardians: list[OutboundGuardianHint] | None = None,
) -> OutboundNotification:
    """Translate an Alert row into the OutboundNotification payload shape.

    The summary field is intentionally short and structural -- it's a hook
    for the parent-comms agent to choose wording from, not the message itself.
    """
    summary = _summary_for_alert(alert)
    return OutboundNotification(
        correlation_id=correlation_id or uuid4(),
        event="alert.raised",
        severity=alert.severity,
        student_id=alert.student_id,
        guardians=guardians or [],
        context=OutboundContext(
            rule_key=alert.rule_key,
            summary=summary,
            evidence=dict(alert.context),
        ),
        intent=intent,
    )


def _summary_for_alert(alert: Alert) -> str:
    if alert.rule_key.startswith("hallpass.") and alert.rule_key.endswith(".duration_exceeded"):
        destination = alert.context.get("destination", "destination unknown")
        minutes = alert.context.get("minutes_elapsed", "?")
        return f"Student out of class {minutes} min ({destination.lower()})"
    return f"Rule {alert.rule_key} triggered"


async def dispatch_alert(
    db: AsyncSession,
    *,
    alert: Alert,
    base_url: str,
    secret: str,
    intent: str = "notify",
    guardians: list[OutboundGuardianHint] | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> Any:
    """Build payload, sign, POST to {base_url}/notifications, log result.

    Returns the AgentMessage row reflecting the outcome (SENT or FAILED).
    Network errors are caught and recorded; the function does not raise so
    a single dispatch failure can't poison a batched detect_overdue_passes
    pipeline.

    `http_client` is injectable for tests.
    """
    notification = build_alert_notification(alert, intent=intent, guardians=guardians)
    payload_dict = notification.model_dump(mode="json")
    msg = await record_outbound_pending(
        db,
        counterparty=COUNTERPARTY,
        correlation_id=notification.correlation_id,
        payload=payload_dict,
        student_id=alert.student_id,
        alert_id=alert.id,
    )

    body_bytes = json.dumps(payload_dict, sort_keys=True).encode("utf-8")
    signature = sign(secret, body_bytes)
    headers = {
        "Content-Type": "application/json",
        SIGNATURE_HEADER: signature,
    }

    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=10.0)
    try:
        response = await client.post(
            f"{base_url.rstrip('/')}/notifications",
            content=body_bytes,
            headers=headers,
        )
        response.raise_for_status()
        return await mark_sent(db, message_id=msg.id)
    except httpx.HTTPError as exc:
        return await mark_failed(db, message_id=msg.id, error=str(exc))
    finally:
        if owns_client:
            await client.aclose()
