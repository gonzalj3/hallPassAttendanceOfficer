from typing import Protocol, runtime_checkable

from hpao.realtime.events import RealtimeEvent, channels_for


@runtime_checkable
class RealtimePublisher(Protocol):
    """Publishes a RealtimeEvent to its derived channels.

    Implementations: InMemoryPublisher (tests/dev), PgNotifyPublisher (Phase 4b).
    """

    async def publish(self, event: RealtimeEvent) -> None: ...


class InMemoryPublisher:
    """Records published events per channel. For tests and local dev only.

    Each event is appended once per channel returned by `channels_for`, so
    asserting on `published[chan]` mirrors what a real subscriber to that
    channel would see.
    """

    def __init__(self) -> None:
        self.published: dict[str, list[RealtimeEvent]] = {}

    async def publish(self, event: RealtimeEvent) -> None:
        for channel in channels_for(event):
            self.published.setdefault(channel, []).append(event)

    def clear(self) -> None:
        self.published.clear()
