from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from hpao.realtime.events import (
    AlertRaised,
    HallpassIssued,
    HallpassOverdue,
    HallpassReturned,
    RealtimeEvent,
    channels_for,
)

_adapter: TypeAdapter[RealtimeEvent] = TypeAdapter(RealtimeEvent)


def _base_kwargs() -> dict[str, object]:
    return {
        "event_id": uuid4(),
        "occurred_at": datetime(2026, 5, 9, 12, 0, tzinfo=UTC),
        "school_id": uuid4(),
        "student_id": uuid4(),
    }


class TestHallpassEvents:
    def test_issued_round_trips_through_discriminated_union(self) -> None:
        event = HallpassIssued(
            **_base_kwargs(),
            hall_pass_id=uuid4(),
            class_id=uuid4(),
            class_session_id=uuid4(),
            destination="RESTROOM",
            expected_return_at=datetime(2026, 5, 9, 12, 15, tzinfo=UTC),
            issued_by=uuid4(),
        )
        decoded = _adapter.validate_python(event.model_dump(mode="json"))
        assert isinstance(decoded, HallpassIssued)
        assert decoded == event

    def test_issued_requires_destination_enum(self) -> None:
        with pytest.raises(ValidationError):
            HallpassIssued(
                **_base_kwargs(),
                hall_pass_id=uuid4(),
                destination="LIBRARY",  # type: ignore[arg-type]
                expected_return_at=datetime(2026, 5, 9, 12, 15, tzinfo=UTC),
                issued_by=uuid4(),
            )

    def test_returned_allows_no_class_context(self) -> None:
        event = HallpassReturned(
            **_base_kwargs(),
            hall_pass_id=uuid4(),
            checked_in_at=datetime(2026, 5, 9, 12, 14, tzinfo=UTC),
        )
        assert event.class_id is None

    def test_overdue_rejects_negative_minutes(self) -> None:
        with pytest.raises(ValidationError):
            HallpassOverdue(
                **_base_kwargs(),
                hall_pass_id=uuid4(),
                expected_return_at=datetime(2026, 5, 9, 12, 15, tzinfo=UTC),
                minutes_elapsed=-1,
            )


class TestAlertRaised:
    def test_severity_must_be_enum_member(self) -> None:
        with pytest.raises(ValidationError):
            AlertRaised(
                **_base_kwargs(),
                alert_id=uuid4(),
                rule_key="restroom.duration_exceeded",
                severity="extreme",  # type: ignore[arg-type]
                summary="x",
            )

    def test_evidence_defaults_to_empty_dict(self) -> None:
        event = AlertRaised(
            **_base_kwargs(),
            alert_id=uuid4(),
            rule_key="restroom.duration_exceeded",
            severity="high",
            summary="Student out 17 minutes",
        )
        assert event.evidence == {}


class TestChannelsFor:
    def test_hallpass_issued_fans_out_to_school_student_class(self) -> None:
        base = _base_kwargs()
        class_id = uuid4()
        event = HallpassIssued(
            **base,
            hall_pass_id=uuid4(),
            class_id=class_id,
            class_session_id=uuid4(),
            destination="RESTROOM",
            expected_return_at=datetime(2026, 5, 9, 12, 15, tzinfo=UTC),
            issued_by=uuid4(),
        )
        assert channels_for(event) == [
            f"school:{base['school_id']}",
            f"student:{base['student_id']}",
            f"class:{class_id}",
        ]

    def test_hallpass_returned_without_class_skips_class_channel(self) -> None:
        base = _base_kwargs()
        event = HallpassReturned(
            **base,
            hall_pass_id=uuid4(),
            checked_in_at=datetime(2026, 5, 9, 12, 14, tzinfo=UTC),
        )
        assert channels_for(event) == [
            f"school:{base['school_id']}",
            f"student:{base['student_id']}",
        ]

    def test_alert_with_class_context_includes_class_channel(self) -> None:
        base = _base_kwargs()
        class_id = uuid4()
        event = AlertRaised(
            **base,
            alert_id=uuid4(),
            class_id=class_id,
            rule_key="restroom.duration_exceeded",
            severity="high",
            summary="Student out 17 minutes",
        )
        assert f"class:{class_id}" in channels_for(event)
