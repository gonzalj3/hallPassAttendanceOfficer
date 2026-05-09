"""Pure unit tests for the outbound payload builder.

Network I/O is integration-tested separately; this just verifies that an
Alert row gets translated into the OutboundNotification shape documented
in CLAUDE.md.
"""

from datetime import UTC, datetime
from uuid import uuid4

from hpao.integrations.parent_comms import build_alert_notification
from hpao.models import Alert
from hpao.schemas.agent import OutboundGuardianHint


def _make_alert(**overrides: object) -> Alert:
    defaults: dict[str, object] = {
        "student_id": uuid4(),
        "rule_key": "hallpass.restroom.duration_exceeded",
        "severity": "high",
        "status": "OPEN",
        "context": {
            "hall_pass_id": str(uuid4()),
            "destination": "RESTROOM",
            "checked_out_at": "2026-05-09T14:00:00+00:00",
            "expected_return_at": "2026-05-09T14:15:00+00:00",
            "minutes_elapsed": 17.0,
        },
    }
    defaults.update(overrides)
    a = Alert(**defaults)
    a.id = uuid4()  # type: ignore[assignment]
    a.created_at = datetime.now(UTC)  # type: ignore[assignment]
    return a


def test_build_alert_notification_event_is_alert_raised() -> None:
    n = build_alert_notification(_make_alert())
    assert n.event == "alert.raised"


def test_build_alert_notification_propagates_severity() -> None:
    n = build_alert_notification(_make_alert(severity="medium"))
    assert n.severity == "medium"


def test_build_alert_notification_default_intent_is_notify() -> None:
    n = build_alert_notification(_make_alert())
    assert n.intent == "notify"


def test_build_alert_notification_accepts_custom_intent() -> None:
    n = build_alert_notification(_make_alert(), intent="request_info")
    assert n.intent == "request_info"


def test_build_alert_notification_includes_rule_key_in_context() -> None:
    n = build_alert_notification(_make_alert(rule_key="rule.example.x"))
    assert n.context.rule_key == "rule.example.x"


def test_build_alert_notification_summary_for_restroom_includes_minutes() -> None:
    n = build_alert_notification(_make_alert())
    assert "17" in n.context.summary
    assert "restroom" in n.context.summary.lower()


def test_build_alert_notification_evidence_carries_alert_context() -> None:
    n = build_alert_notification(_make_alert())
    assert n.context.evidence["destination"] == "RESTROOM"
    assert "hall_pass_id" in n.context.evidence


def test_build_alert_notification_passes_through_guardian_hints() -> None:
    g = OutboundGuardianHint(
        id=uuid4(), name="Maria Garcia", preferred_channel="sms", preferred_language="es"
    )
    n = build_alert_notification(_make_alert(), guardians=[g])
    assert len(n.guardians) == 1
    assert n.guardians[0].name == "Maria Garcia"


def test_build_alert_notification_generates_correlation_id_when_omitted() -> None:
    n = build_alert_notification(_make_alert())
    assert n.correlation_id is not None


def test_build_alert_notification_uses_provided_correlation_id() -> None:
    cid = uuid4()
    n = build_alert_notification(_make_alert(), correlation_id=cid)
    assert n.correlation_id == cid


def test_build_alert_notification_summary_for_unknown_rule() -> None:
    n = build_alert_notification(_make_alert(rule_key="totally.new.rule"))
    assert "totally.new.rule" in n.context.summary
