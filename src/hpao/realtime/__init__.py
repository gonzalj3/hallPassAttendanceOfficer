"""Realtime layer: event taxonomy + pub/sub abstractions.

Phase 4a defines the contract every later phase publishes through:
  - `RealtimeEvent` discriminated union of the 5 event types HPAO emits.
  - `channels_for(event)` derives the `school:`/`class:`/`student:` channels
    each event fans out to.
  - `RealtimePublisher` Protocol + `InMemoryPublisher` for tests and dev.

Phase 4b will add a `PgNotifyPublisher` (LISTEN/NOTIFY transport) and
Phase 4c will add the WebSocket fan-out endpoint.
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
    "RealtimeEvent",
    "RealtimePublisher",
    "Severity",
    "channels_for",
]
