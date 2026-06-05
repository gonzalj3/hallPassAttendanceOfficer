"""Realtime layer: event taxonomy, pub/sub abstractions, WebSocket fan-out."""

from hpao.realtime.app import make_app
from hpao.realtime.events import (
    AlertRaised,
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
