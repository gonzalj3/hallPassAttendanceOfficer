import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine

from hpao.realtime import (
    AttendanceRecorded,
    HallpassReturned,
    PgNotifyPublisher,
    RealtimeListener,
    asyncpg_dsn,
    channels_for,
)

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def listener(migrated_database: str) -> AsyncIterator[RealtimeListener]:
    listener = RealtimeListener(asyncpg_dsn(migrated_database))
    await listener.start()
    try:
        yield listener
    finally:
        await listener.stop()


def _attendance_event() -> AttendanceRecorded:
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


async def _publish_committed(
    engine: AsyncEngine, event: AttendanceRecorded | HallpassReturned
) -> None:
    async with engine.begin() as conn:
        await PgNotifyPublisher(conn).publish(event)


async def test_publish_fans_out_to_each_derived_channel(
    listener: RealtimeListener, async_engine: AsyncEngine
) -> None:
    event = _attendance_event()
    expected = channels_for(event)

    async with listener.subscribe(expected) as queue:
        await _publish_committed(async_engine, event)

        received: list[tuple[str, str]] = []
        for _ in expected:
            received.append(await asyncio.wait_for(queue.get(), timeout=2.0))

    assert sorted(ch for ch, _ in received) == sorted(expected)
    decoded = AttendanceRecorded.model_validate_json(received[0][1])
    assert decoded == event


async def test_unsubscribe_stops_delivery(
    listener: RealtimeListener, async_engine: AsyncEngine
) -> None:
    event = _attendance_event()
    school_channel = f"school:{event.school_id}"

    async with listener.subscribe([school_channel]) as queue:
        await _publish_committed(async_engine, event)
        await asyncio.wait_for(queue.get(), timeout=2.0)

    # After the context exits the channel has zero subscribers, so the next
    # publish must not enqueue anything (there's no queue to enqueue into,
    # and the underlying LISTEN was dropped).
    second = _attendance_event().model_copy(update={"school_id": event.school_id})
    await _publish_committed(async_engine, second)
    await asyncio.sleep(0.2)  # give any stray dispatch a chance to land

    async with listener.subscribe([school_channel]) as queue:
        # Only events published while subscribed should arrive. The second
        # event was published during the gap and should be lost.
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue.get(), timeout=0.5)


async def test_uncommitted_publish_does_not_notify(
    listener: RealtimeListener, async_engine: AsyncEngine
) -> None:
    """pg_notify is buffered until COMMIT; rolling back must drop the event."""
    event = _attendance_event()
    school_channel = f"school:{event.school_id}"

    async with listener.subscribe([school_channel]) as queue:
        async with async_engine.connect() as conn:
            await PgNotifyPublisher(conn).publish(event)
            await conn.rollback()

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue.get(), timeout=0.5)
