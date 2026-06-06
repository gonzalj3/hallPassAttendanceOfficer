from uuid import uuid4

from lizzie.models import ALERT_SEVERITIES, ALERT_STATUSES, Alert


def test_alert_construction() -> None:
    student_id = uuid4()
    a = Alert(
        student_id=student_id,
        rule_key="hallpass.restroom.duration_exceeded",
        severity="high",
        status="OPEN",
        context={"hall_pass_id": "abc", "minutes_elapsed": 17},
    )
    assert a.student_id == student_id
    assert a.rule_key == "hallpass.restroom.duration_exceeded"
    assert a.severity == "high"
    assert a.status == "OPEN"
    assert a.context["minutes_elapsed"] == 17


def test_alert_severities_match_webhook_spec() -> None:
    """CLAUDE.md outbound webhook payload uses lowercase severity values."""
    assert ALERT_SEVERITIES == ("low", "medium", "high", "critical")


def test_alert_statuses() -> None:
    assert ALERT_STATUSES == ("OPEN", "ACKNOWLEDGED", "RESOLVED")


def test_alert_repr_includes_severity_and_rule() -> None:
    a = Alert(
        student_id=uuid4(),
        rule_key="hallpass.restroom.duration_exceeded",
        severity="high",
        status="OPEN",
    )
    rep = repr(a)
    assert "high" in rep
    assert "hallpass.restroom.duration_exceeded" in rep
