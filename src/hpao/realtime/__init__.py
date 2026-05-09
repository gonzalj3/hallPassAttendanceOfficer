"""Realtime layer: event taxonomy, pub/sub abstractions, WebSocket fan-out.

- Phase 4a: `RealtimeEvent` discriminated union, `channels_for()`,
  `RealtimePublisher` Protocol, `InMemoryPublisher`.
- Phase 4b: Postgres LISTEN/NOTIFY transport (`PgNotifyPublisher`,
  `RealtimeListener`).
- Phase 4c: FastAPI WebSocket endpoint and `make_app()` factory.
"""

from hpao.realtime.app import make_app
from hpao.realtime.events import (
    AlertRaised,
    AttendanceRecorded,
    AttendanceStatus,
    Destination,
    HallpassIssued,
    HallpassOverdue,
    HallpassReturned,
    RealtimeEvent,
    Severity,
    channels_for,
)
from hpao.realtime.postgres import (
    PgNotifyPublisher,
    RealtimeListener,
    asyncpg_dsn,
)
from hpao.realtime.publisher import InMemoryPublisher, RealtimePublisher
from hpao.realtime.websocket import make_realtime_router

__all__ = [
    "AlertRaised",
    "AttendanceRecorded",
    "AttendanceStatus",
    "Destination",
    "HallpassIssued",
    "HallpassOverdue",
    "HallpassReturned",
    "InMemoryPublisher",
    "PgNotifyPublisher",
    "RealtimeEvent",
    "RealtimeListener",
    "RealtimePublisher",
    "Severity",
    "asyncpg_dsn",
    "channels_for",
    "make_app",
    "make_realtime_router",
]
