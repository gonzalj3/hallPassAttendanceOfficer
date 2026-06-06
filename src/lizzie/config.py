from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(...)
    app_env: str = Field(default="dev")

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        """Coerce ``postgres://...?sslmode=...`` URLs into the
        ``postgresql+asyncpg://...?ssl=...`` form SQLAlchemy 2.0 +
        asyncpg accepts.
        """
        if not v.startswith("postgresql+"):
            if v.startswith("postgres://"):
                v = "postgresql+asyncpg://" + v[len("postgres://") :]
            elif v.startswith("postgresql://"):
                v = "postgresql+asyncpg://" + v[len("postgresql://") :]

        parsed = urlparse(v)
        if parsed.query:
            rewritten: list[tuple[str, str]] = []
            for k, val in parse_qsl(parsed.query, keep_blank_values=True):
                if k == "sslmode":
                    rewritten.append(("ssl", val))
                else:
                    rewritten.append((k, val))
            v = urlunparse(parsed._replace(query=urlencode(rewritten)))
        return v

    dispatcher_interval_seconds: float = Field(default=30.0)

    # Signing secret for the role-picker session cookie (Phase E). Optional in
    # dev (a per-process random key is generated); MUST be set in production
    # or sessions invalidate on every restart.
    session_cookie_secret: str | None = Field(default=None)

    # CORS allow-list for the deployed frontends. Comma-separated. Localhost
    # dev URLs are always allowed via regex regardless of this setting.
    frontend_origin: str = Field(default="https://verdant-pie-1d3c9f.netlify.app")


@lru_cache
def get_settings() -> Settings:
    return Settings()
