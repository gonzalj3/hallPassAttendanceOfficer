import pytest

from hpao.config import Settings


def test_settings_accepts_kwargs() -> None:
    s = Settings(database_url="postgresql+asyncpg://localhost/test")
    assert s.database_url == "postgresql+asyncpg://localhost/test"
    assert s.app_env == "dev"


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://example/db")
    monkeypatch.setenv("APP_ENV", "test")
    s = Settings()
    assert s.database_url == "postgresql+asyncpg://example/db"
    assert s.app_env == "test"


def test_settings_app_env_defaults_to_dev() -> None:
    s = Settings(database_url="postgresql+asyncpg://x/y")
    assert s.app_env == "dev"


def test_settings_normalizes_bare_postgres_url() -> None:
    """`fly postgres attach` writes `postgres://` — coerce to asyncpg form."""
    s = Settings(database_url="postgres://user:pw@host:5432/db")
    assert s.database_url == "postgresql+asyncpg://user:pw@host:5432/db"


def test_settings_normalizes_postgresql_without_driver() -> None:
    s = Settings(database_url="postgresql://user:pw@host:5432/db")
    assert s.database_url == "postgresql+asyncpg://user:pw@host:5432/db"


def test_settings_passes_through_explicit_driver() -> None:
    s = Settings(database_url="postgresql+asyncpg://user:pw@host:5432/db")
    assert s.database_url == "postgresql+asyncpg://user:pw@host:5432/db"


def test_settings_passes_through_other_explicit_driver() -> None:
    """Don't second-guess callers who picked a different driver on purpose."""
    s = Settings(database_url="postgresql+psycopg://user:pw@host:5432/db")
    assert s.database_url == "postgresql+psycopg://user:pw@host:5432/db"


def test_settings_renames_sslmode_to_ssl() -> None:
    """`fly postgres attach` writes ?sslmode=disable; asyncpg expects ?ssl=."""
    s = Settings(database_url="postgres://user:pw@host.flycast:5432/db?sslmode=disable")
    assert s.database_url == "postgresql+asyncpg://user:pw@host.flycast:5432/db?ssl=disable"


def test_settings_renames_sslmode_require_to_ssl_require() -> None:
    s = Settings(database_url="postgres://u:p@h:5432/d?sslmode=require")
    assert s.database_url == "postgresql+asyncpg://u:p@h:5432/d?ssl=require"


def test_settings_keeps_other_query_params_alongside_ssl_rename() -> None:
    """Don't drop unrelated query params while renaming sslmode."""
    s = Settings(database_url="postgres://u:p@h:5432/d?sslmode=disable&application_name=hpao")
    # urlencode preserves insertion order; sslmode was first.
    assert s.database_url == "postgresql+asyncpg://u:p@h:5432/d?ssl=disable&application_name=hpao"
