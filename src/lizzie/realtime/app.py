import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI

from lizzie.realtime.postgres import RealtimeListener, asyncpg_dsn
from lizzie.realtime.websocket import make_realtime_router


def make_app(database_url: str) -> FastAPI:
    """Create a FastAPI app whose lifespan owns one shared RealtimeListener.

    The listener handles all WebSocket subscriptions through a single asyncpg
    connection — see RealtimeListener for the LISTEN/UNLISTEN ref-counting.
    Phase 8 will compose this with the REST endpoints; for now this app
    serves only `/v1/realtime`.
    """
    listener = RealtimeListener(asyncpg_dsn(database_url))

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await listener.start()
        try:
            yield
        finally:
            await listener.stop()

    app = FastAPI(lifespan=lifespan)
    app.include_router(make_realtime_router(listener))
    return app
