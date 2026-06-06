"""Role-picker auth: signed-cookie sessions for the demo MVP.

A landing page in each frontend lets the user pick "Teacher" or
"Principal"; the backend resolves that to a seeded User row, sets an
HMAC-signed session cookie, and downstream routes read the cookie via
the `current_user` dependency. There is no password store -- the demo
runs against synthetic data, and the seam (`current_user`) is the
single swap point when a real pilot needs Google OIDC instead.
"""

from hpao.auth.dependencies import (
    CurrentUser,
    current_user,
    require_role,
)
from hpao.auth.router import mount
from hpao.auth.session import SESSION_COOKIE, sign_session, verify_session

__all__ = [
    "SESSION_COOKIE",
    "CurrentUser",
    "current_user",
    "mount",
    "require_role",
    "sign_session",
    "verify_session",
]
