"""Stateless signed-cookie sessions.

Token format: ``base64url(json) + "." + base64url(hmac_sha256(secret, body))``.
No padding chars (URL-safe). The payload is a small JSON object: user_id,
school_id, role, name, exp (unix seconds). Verification re-computes the
MAC in constant time and rejects expired payloads. There's no server-side
session store -- if the cookie verifies, the request is authenticated.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

SESSION_COOKIE = "lizzie_session"
MAX_AGE_SECONDS = 8 * 60 * 60  # 8 hours; one school day


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def sign_session(
    payload: dict[str, Any],
    *,
    secret: str,
    now: int | None = None,
    max_age_seconds: int = MAX_AGE_SECONDS,
) -> str:
    p = dict(payload)
    p["exp"] = (now if now is not None else int(time.time())) + max_age_seconds
    raw = json.dumps(p, separators=(",", ":"), sort_keys=True).encode("utf-8")
    body = _b64url_encode(raw)
    sig = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64url_encode(sig)}"


def verify_session(
    token: str,
    *,
    secret: str,
    now: int | None = None,
) -> dict[str, Any] | None:
    """Return the decoded payload, or None if the token is invalid or expired."""
    if "." not in token:
        return None
    body, sig = token.split(".", 1)
    try:
        expected = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        actual = _b64url_decode(sig)
    except (ValueError, TypeError):
        return None
    if not hmac.compare_digest(expected, actual):
        return None
    try:
        payload = json.loads(_b64url_decode(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    exp = payload.get("exp")
    if not isinstance(exp, int):
        return None
    if exp < (now if now is not None else int(time.time())):
        return None
    return dict(payload)
