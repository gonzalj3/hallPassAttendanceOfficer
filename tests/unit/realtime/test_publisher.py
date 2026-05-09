from datetime import UTC, datetime
from uuid import uuid4

import pytest

from hpao.realtime import (
    AttendanceRecorded,
    HallpassReturned,
    InMemoryPublisher,
    RealtimePublisher,
)


def _attendance() -> AttendanceRecorded:
    return AttendanceRecorded(
        event_id=uuid4(),
        occurred_at=datetime(2026, 5, 9, 12, 0, tzinfo=UTC),
        school_id=uuid4(),
        student_id=uuid4(),
        class_id=uuid4(),
        class_session_id=uuid4(),
        status="PRESENT",
        source="teacher",
        recorded_by=uuid4(),
    )


class TestInMemoryPublisher:
    def test_satisfies_protocol(self) -> None:
        assert isinstance(InMemoryPublisher(), RealtimePublisher)

    @pytest.mark.asyncio
    async def test_records_event_on_each_derived_channel(self) -> None:
        pub = InMemoryPublisher()
        event = _attendance()

        await pub.publish(event)

        assert pub.published[f"school:{event.school_id}"] == [event]
        assert pub.published[f"student:{event.student_id}"] == [event]
        assert pub.published[f"class:{event.class_id}"] == [event]

    @pytest.mark.asyncio
    async def test_appends_in_order_per_channel(self) -> None:
        pub = InMemoryPublisher()
        first = _attendance()
        second = _attendance().model_copy(update={"school_id": first.school_id})

        await pub.publish(first)
        await pub.publish(second)

        assert pub.published[f"school:{first.school_id}"] == [first, second]

    @pytest.mark.asyncio
    async def test_does_not_create_class_channel_when_absent(self) -> None:
        pub = InMemoryPublisher()
        event = HallpassReturned(
            event_id=uuid4(),
            occurred_at=datetime(2026, 5, 9, 12, 14, tzinfo=UTC),
            school_id=uuid4(),
            student_id=uuid4(),
            hall_pass_id=uuid4(),
            checked_in_at=datetime(2026, 5, 9, 12, 14, tzinfo=UTC),
        )

        await pub.publish(event)

        assert not any(ch.startswith("class:") for ch in pub.published)

    @pytest.mark.asyncio
    async def test_clear_resets_recorded_events(self) -> None:
        pub = InMemoryPublisher()
        await pub.publish(_attendance())
        pub.clear()
        assert pub.published == {}
