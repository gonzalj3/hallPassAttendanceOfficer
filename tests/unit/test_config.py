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
