"""Realtime layer: event taxonomy + pub/sub abstractions.

Phase 4a defined the contract: `RealtimeEvent` discriminated union, the
`channels_for()` school/class/student fan-out, and a `RealtimePublisher`
Protocol with an in-memory implementation.

Phase 4b adds the Postgres LISTEN/NOTIFY transport (`PgNotifyPublisher`,
`RealtimeListener`). Phase 4c will plug a WebSocket endpoint into the
listener.
"""

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
]
