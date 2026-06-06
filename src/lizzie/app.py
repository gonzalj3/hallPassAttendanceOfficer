"""Top-level FastAPI app composing every HTTP / WebSocket surface.

  - `/v1/realtime` (WS)   — pg_notify fan-out
  - `/api/*`              — browser-facing REST surface
  - `/auth/*`             — role-picker session
  - `/healthz`            — liveness check

Run locally:

    uvicorn --factory lizzie.app:app_factory --reload --port 8000
"""

from __future__ import annotations

import contextlib
import secrets
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from lizzie.api import admin as admin_api
from lizzie.api import frontend as frontend_api
from lizzie.auth import mount as mount_auth
from lizzie.config import Settings, get_settings
from lizzie.realtime.postgres import RealtimeListener, asyncpg_dsn
from lizzie.realtime.websocket import make_realtime_router

LOCALHOST_ORIGIN_REGEX = r"http://(localhost|127\.0\.0\.1)(:\d+)?"


def make_app(
    database_url: str,
    *,
    session_secret: str | None = None,
    is_production: bool = False,
    allowed_origins: list[str] | None = None,
    allowed_origin_regex: str | None = LOCALHOST_ORIGIN_REGEX,
) -> FastAPI:
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    listener = RealtimeListener(asyncpg_dsn(database_url))

    # If no session secret was supplied (dev / tests), generate a per-process
    # random one. Sessions die on restart, which is fine for dev. Production
    # MUST set SESSION_COOKIE_SECRET so cookies survive a redeploy.
    resolved_secret = session_secret or secrets.token_urlsafe(32)

    @contextlib.asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await listener.start()
        try:
            yield
        finally:
            await listener.stop()
            await engine.dispose()

    app = FastAPI(lifespan=lifespan, title="Monitor Lizzie", version="0.2.0")

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
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            else:
                await session.commit()

    frontend_api.mount(app, session_provider=session_dep)
    admin_api.mount(app, session_provider=session_dep)
    mount_auth(
        app,
        session_provider=session_dep,
        session_secret=resolved_secret,
        is_production=is_production,
    )

    return app


def app_factory() -> FastAPI:
    """No-arg factory wired for `uvicorn --factory lizzie.app:app_factory`."""
    return _make_app_from_settings(get_settings())


def _make_app_from_settings(settings: Settings) -> FastAPI:
    return make_app(
        settings.database_url,
        session_secret=settings.session_cookie_secret,
        is_production=settings.app_env == "prod",
        allowed_origins=_parse_origins(settings.frontend_origin),
    )


def _parse_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
