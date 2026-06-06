import pytest
from fastapi.testclient import TestClient

from lizzie.app import make_app

pytestmark = pytest.mark.integration

NETLIFY_ORIGIN = "https://verdant-pie-1d3c9f.netlify.app"


def test_healthz_returns_ok(migrated_database: str) -> None:
    app = make_app(migrated_database, allowed_origins=[NETLIFY_ORIGIN])
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_preflight_allows_netlify_origin(migrated_database: str) -> None:
    app = make_app(migrated_database, allowed_origins=[NETLIFY_ORIGIN])
    with TestClient(app) as client:
        response = client.options(
            "/healthz",
            headers={
                "Origin": NETLIFY_ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == NETLIFY_ORIGIN


def test_cors_preflight_allows_localhost_dev(migrated_database: str) -> None:
    app = make_app(migrated_database, allowed_origins=[NETLIFY_ORIGIN])
    with TestClient(app) as client:
        response = client.options(
            "/healthz",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_blocks_unlisted_origin(migrated_database: str) -> None:
    """Origins outside the allow-list and the localhost regex must not be
    echoed back, so the browser blocks the actual request."""
    app = make_app(migrated_database, allowed_origins=[NETLIFY_ORIGIN])
    with TestClient(app) as client:
        response = client.options(
            "/healthz",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert "access-control-allow-origin" not in response.headers


def test_realtime_websocket_route_is_mounted(migrated_database: str) -> None:
    """Sanity that the WS route from Phase 4c made it onto this app, not
    a separate one."""
    app = make_app(migrated_database, allowed_origins=[NETLIFY_ORIGIN])
    with TestClient(app) as client:
        # No channel -> server closes with 1008. We just verify the route
        # exists and the handshake reaches our handler.
        from starlette.websockets import WebSocketDisconnect

        with pytest.raises(WebSocketDisconnect), client.websocket_connect("/v1/realtime"):
            pass
