import pytest

from lizzie.auth.session import sign_session, verify_session

SECRET = "test-secret-please-rotate"


def test_round_trips_payload() -> None:
    token = sign_session({"user_id": "u1", "role": "TEACHER"}, secret=SECRET, now=1000)
    payload = verify_session(token, secret=SECRET, now=1001)
    assert payload is not None
    assert payload["user_id"] == "u1"
    assert payload["role"] == "TEACHER"
    assert payload["exp"] == 1000 + 8 * 60 * 60


def test_rejects_tampered_body() -> None:
    token = sign_session({"role": "TEACHER"}, secret=SECRET, now=1000)
    body, sig = token.split(".", 1)
    # Re-encode the body with role flipped; the sig no longer matches.
    import base64
    import json

    tampered_raw = json.dumps({"role": "ADMIN", "exp": 5000}, sort_keys=True).encode()
    tampered_body = base64.urlsafe_b64encode(tampered_raw).rstrip(b"=").decode()
    assert verify_session(f"{tampered_body}.{sig}", secret=SECRET, now=1001) is None


def test_rejects_wrong_secret() -> None:
    token = sign_session({"role": "TEACHER"}, secret=SECRET, now=1000)
    assert verify_session(token, secret="different-secret", now=1001) is None


def test_rejects_expired() -> None:
    token = sign_session({"role": "TEACHER"}, secret=SECRET, now=1000, max_age_seconds=60)
    assert verify_session(token, secret=SECRET, now=1061) is None


def test_rejects_malformed() -> None:
    assert verify_session("not-a-token", secret=SECRET) is None
    assert verify_session("abc.def.ghi", secret=SECRET) is None
    assert verify_session("", secret=SECRET) is None


@pytest.mark.parametrize("role", ["TEACHER", "ADMIN"])
def test_carries_role(role: str) -> None:
    token = sign_session({"role": role}, secret=SECRET, now=1000)
    payload = verify_session(token, secret=SECRET, now=1001)
    assert payload is not None
    assert payload["role"] == role
