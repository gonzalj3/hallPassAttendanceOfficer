"""Top-level FastAPI app composing every HTTP / WebSocket surface HPAO ships.

  - `/v1/realtime` (WS) — Phase 4c fan-out of pg_notify events.
  - `/v1/agent/*`        — Phase 8 inter-agent boundary, HMAC-signed for the
                           parent-comms agent. Browsers will 401 / 500 on
                           these by design.
  - `/healthz`           — liveness check for uvicorn / Netlify / monitors.

A single uvicorn process owns one SQLAlchemy engine pool plus one dedicated
asyncpg LISTEN connection (the realtime listener) — both are spun up inside
the lifespan and torn down on shutdown.

Run locally:

    uvicorn --factory hpao.app:app_factory --reload --port 8000
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from hpao.api import agent as agent_api
from hpao.api import frontend as frontend_api
from hpao.config import Settings, get_settings
from hpao.realtime.postgres import RealtimeListener, asyncpg_dsn
from hpao.realtime.websocket import make_realtime_router

# Localhost on any port is always allowed for dev — Vite default is 3000,
# `npm run dev` may use 5173 if 3000 is busy, browsers may rewrite to
# 127.0.0.1, etc. Tightening this never improved a hackathon's life.
LOCALHOST_ORIGIN_REGEX = r"http://(localhost|127\.0\.0\.1)(:\d+)?"


def make_app(
    database_url: str,
    *,
    hmac_secret: str | None = None,
    allowed_origins: list[str] | None = None,
    allowed_origin_regex: str | None = LOCALHOST_ORIGIN_REGEX,
) -> FastAPI:
    """Build the top-level FastAPI app.

    Tests pass a `database_url` from a testcontainer; production composes
    via `app_factory()`. `hmac_secret` is the parent-comms shared secret;
    when unset, `/v1/agent/*` POSTs respond 500 (no secret configured) —
    expected behavior for browser callers, which shouldn't hit those.
    """
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    listener = RealtimeListener(asyncpg_dsn(database_url))

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await listener.start()
        try:
            yield
        finally:
            await listener.stop()
            await engine.dispose()

    app = FastAPI(lifespan=lifespan, title="HPAO", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or [],
        allow_origin_regex=allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(make_realtime_router(listener))

    async def session_dep() -> AsyncIterator[AsyncSession]:
        # Commit on success, roll back on exception. Without this, every
        # write endpoint would silently drop its work when the session
        # closed at request end.
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            else:
                await session.commit()

    agent_api.mount(app, session_provider=session_dep, secret=hmac_secret)
    frontend_api.mount(app, session_provider=session_dep)

    return app


def app_factory() -> FastAPI:
    """No-arg factory wired for `uvicorn --factory hpao.app:app_factory`."""
    return _make_app_from_settings(get_settings())


def _make_app_from_settings(settings: Settings) -> FastAPI:
    return make_app(
        settings.database_url,
        hmac_secret=settings.parent_comms_secret,
        allowed_origins=_parse_origins(settings.frontend_origin),
    )


def _parse_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
