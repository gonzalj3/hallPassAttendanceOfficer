import asyncio
import threading
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from hpao.realtime import (
    HallpassIssued,
    HallpassReturned,
    PgNotifyPublisher,
    RealtimeEvent,
    channels_for,
    make_app,
)

pytestmark = pytest.mark.integration


def _publish_in_thread(database_url: str, event: RealtimeEvent) -> threading.Thread:
    """Publish on a fresh asyncio loop in a background thread.

    The TestClient's event loop is busy running the WS endpoint inside the
    `with` context, so the publisher needs its own loop. A separate thread
    keeps the loops cleanly isolated.
    """

    def run() -> None:
        async def go() -> None:
            engine = create_async_engine(database_url)
            try:
                async with engine.begin() as conn:
                    await PgNotifyPublisher(conn).publish(event)
            finally:
                await engine.dispose()

        asyncio.run(go())

    thread = threading.Thread(target=run)
    thread.start()
    return thread


def _attendance_event() -> HallpassIssued:
    return HallpassIssued(
        event_id=uuid4(),
        occurred_at=datetime(2026, 5, 9, 12, 0, tzinfo=UTC),
        school_id=uuid4(),
        student_id=uuid4(),
        hall_pass_id=uuid4(),
        class_id=uuid4(),
        class_session_id=uuid4(),
        destination="RESTROOM",
        expected_return_at=datetime(2026, 5, 9, 12, 15, tzinfo=UTC),
        issued_by=uuid4(),
    )


def test_ws_receives_published_event(migrated_database: str) -> None:
    app = make_app(migrated_database)
    event = _attendance_event()
    school_channel = f"school:{event.school_id}"

    with (
        TestClient(app) as client,
        client.websocket_connect(f"/v1/realtime?channel={school_channel}") as ws,
    ):
        thread = _publish_in_thread(migrated_database, event)
        try:
            msg = ws.receive_json()
        finally:
            thread.join(timeout=5.0)

    assert msg["channel"] == school_channel
    assert msg["event"]["event"] == "hallpass.issued"
    assert msg["event"]["event_id"] == str(event.event_id)
    assert msg["event"]["destination"] == "RESTROOM"


def test_ws_multiplexes_multiple_channels(migrated_database: str) -> None:
    app = make_app(migrated_database)
    event = _attendance_event()
    expected = channels_for(event)

    query = "&".join(f"channel={ch}" for ch in expected)
    with TestClient(app) as client, client.websocket_connect(f"/v1/realtime?{query}") as ws:
        thread = _publish_in_thread(migrated_database, event)
        try:
            received = [ws.receive_json() for _ in expected]
        finally:
            thread.join(timeout=5.0)

    assert sorted(m["channel"] for m in received) == sorted(expected)
    assert {m["event"]["event_id"] for m in received} == {str(event.event_id)}


def test_ws_rejects_subscription_with_no_channels(migrated_database: str) -> None:
    app = make_app(migrated_database)

    with (
        TestClient(app) as client,
        pytest.raises(Exception) as excinfo,
        client.websocket_connect("/v1/realtime"),
    ):
        pass

    # Starlette wraps the close in WebSocketDisconnect; assert via the import
    # site to keep the test resilient to message wording changes.
    from starlette.websockets import WebSocketDisconnect

    assert isinstance(excinfo.value, WebSocketDisconnect)


def test_ws_only_receives_subscribed_channels(migrated_database: str) -> None:
    """Publishing to channels we did not subscribe to must not deliver."""
    app = make_app(migrated_database)
    subscribed_event = _attendance_event()
    other_event = HallpassReturned(
        event_id=uuid4(),
        occurred_at=datetime(2026, 5, 9, 12, 14, tzinfo=UTC),
        school_id=uuid4(),  # different school -> different school channel
        student_id=uuid4(),
        hall_pass_id=uuid4(),
        checked_in_at=datetime(2026, 5, 9, 12, 14, tzinfo=UTC),
    )
    school_channel = f"school:{subscribed_event.school_id}"

    with (
        TestClient(app) as client,
        client.websocket_connect(f"/v1/realtime?channel={school_channel}") as ws,
    ):
        # Publish the unrelated event first; it must not surface to our WS.
        thread1 = _publish_in_thread(migrated_database, other_event)
        thread1.join(timeout=5.0)

        thread2 = _publish_in_thread(migrated_database, subscribed_event)
        try:
            msg = ws.receive_json()
        finally:
            thread2.join(timeout=5.0)

    assert msg["channel"] == school_channel
    assert msg["event"]["event_id"] == str(subscribed_event.event_id)
