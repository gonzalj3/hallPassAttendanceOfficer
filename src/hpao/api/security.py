"""HMAC-SHA256 signing + verification for the agent boundary.

Both directions of the boundary use the same scheme:
header `X-HPAO-Signature: <hex(hmac_sha256(secret, raw_body))>`. The
verifier compares with `hmac.compare_digest` to avoid timing leaks.
"""

from __future__ import annotations

import hashlib
import hmac

SIGNATURE_HEADER = "X-HPAO-Signature"


def sign(secret: str, body: bytes) -> str:
    """Produce the hex digest sent in `X-HPAO-Signature`."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify(secret: str, body: bytes, signature_header: str | None) -> bool:
    """Constant-time check of an incoming signature against the body."""
    if not signature_header:
        return False
    expected = sign(secret, body)
    return hmac.compare_digest(expected, signature_header)
