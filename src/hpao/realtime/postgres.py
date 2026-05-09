import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable, Coroutine, Iterable
from typing import Any

import asyncpg
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncConnection

from hpao.realtime.events import RealtimeEvent, channels_for

Handler = Callable[[str], Coroutine[Any, Any, None]]
"""Async callback invoked with a NOTIFY payload string."""


def asyncpg_dsn(sqlalchemy_url: str) -> str:
    """Strip the SQLAlchemy `+asyncpg` driver suffix so asyncpg.connect accepts the URL."""
    url = make_url(sqlalchemy_url)
    if url.drivername == "postgresql+asyncpg":
        url = url.set(drivername="postgresql")
    return url.render_as_string(hide_password=False)


class PgNotifyPublisher:
    """RealtimePublisher backed by `pg_notify`.

    Pass an `AsyncConnection` already inside the same transaction that wrote
    the underlying row. NOTIFY payloads are queued by Postgres until COMMIT,
    so events fire only when the data is durable.
    """

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def publish(self, event: RealtimeEvent) -> None:
        payload = event.model_dump_json()
        for channel in channels_for(event):
            await self._conn.execute(
                text("SELECT pg_notify(:channel, :payload)"),
                {"channel": channel, "payload": payload},
            )


class RealtimeListener:
    """Owns one long-lived asyncpg connection and dispatches NOTIFY messages.

    Multiple subscribers can register on the same channel; the first triggers
    a real `LISTEN`, the last to leave triggers `UNLISTEN`. A single connection
    multiplexes every channel — Phase 4c (WebSocket fan-out) shares this one
    listener across all connected clients.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn: asyncpg.Connection | None = None
        self._handlers: dict[str, list[Handler]] = {}
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        if self._conn is not None:
            return
        self._conn = await asyncpg.connect(self._dsn)
        self._loop = asyncio.get_running_loop()

    async def stop(self) -> None:
        conn, self._conn = self._conn, None
        self._loop = None
        if conn is None:
            return
        for channel in list(self._handlers):
            with contextlib.suppress(Exception):
                await conn.remove_listener(channel, self._on_notify)
        self._handlers.clear()
        await conn.close()

    @contextlib.asynccontextmanager
    async def subscribe(
        self, channels: Iterable[str]
    ) -> AsyncIterator[asyncio.Queue[tuple[str, str]]]:
        """Yield a queue that receives `(channel, payload)` tuples for the given channels."""
        queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
        bound: list[tuple[str, Handler]] = []
        try:
            for channel in channels:
                handler = self._make_queue_handler(queue, channel)
                await self._add(channel, handler)
                bound.append((channel, handler))
            yield queue
        finally:
            for channel, handler in bound:
                await self._remove(channel, handler)

    @staticmethod
    def _make_queue_handler(queue: asyncio.Queue[tuple[str, str]], channel: str) -> Handler:
        async def handler(payload: str) -> None:
            await queue.put((channel, payload))

        return handler

    async def _add(self, channel: str, handler: Handler) -> None:
        if self._conn is None:
            raise RuntimeError("Listener not started")
        async with self._lock:
            handlers = self._handlers.setdefault(channel, [])
            handlers.append(handler)
            if len(handlers) == 1:
                await self._conn.add_listener(channel, self._on_notify)

    async def _remove(self, channel: str, handler: Handler) -> None:
        if self._conn is None:
            return
        async with self._lock:
            handlers = self._handlers.get(channel, [])
            try:
                handlers.remove(handler)
            except ValueError:
                return
            if not handlers:
                self._handlers.pop(channel, None)
                with contextlib.suppress(Exception):
                    await self._conn.remove_listener(channel, self._on_notify)

    def _on_notify(
        self,
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str,
    ) -> None:
        # asyncpg fires this synchronously from its read loop. Schedule each
        # async handler so a slow consumer can't block dispatch.
        loop = self._loop
        if loop is None:
            return
        for handler in list(self._handlers.get(channel, [])):
            loop.create_task(handler(payload))
