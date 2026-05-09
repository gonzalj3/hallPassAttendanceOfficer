"""HMAC sign + verify roundtrip."""

from hpao.api.security import sign, verify


def test_sign_then_verify_succeeds() -> None:
    secret = "shared-secret"
    body = b'{"hello":"world"}'
    sig = sign(secret, body)
    assert verify(secret, body, sig) is True


def test_verify_rejects_wrong_signature() -> None:
    body = b'{"hello":"world"}'
    assert verify("shared-secret", body, "deadbeef") is False


def test_verify_rejects_missing_signature() -> None:
    body = b"{}"
    assert verify("shared-secret", body, None) is False


def test_verify_rejects_empty_signature() -> None:
    body = b"{}"
    assert verify("shared-secret", body, "") is False


def test_verify_rejects_when_body_tampered() -> None:
    secret = "shared-secret"
    sig = sign(secret, b'{"a":1}')
    assert verify(secret, b'{"a":2}', sig) is False


def test_verify_rejects_when_secret_differs() -> None:
    body = b"{}"
    sig = sign("alice-secret", body)
    assert verify("bob-secret", body, sig) is False


def test_sign_is_deterministic() -> None:
    """Same body + secret -> same hex digest. Lets the receiver recompute."""
    secret = "s"
    body = b"x"
    assert sign(secret, body) == sign(secret, body)
