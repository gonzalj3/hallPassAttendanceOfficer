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
        ``postgresql+asyncpg://...`` form SQLAlchemy 2.0 + asyncpg accepts.

        ``fly postgres attach`` writes ``postgres://...?sslmode=disable`` into
        ``DATABASE_URL``. Two things break asyncpg there:

        1. The ``postgres://`` scheme — SQLAlchemy 2.0 requires a driver,
           e.g. ``postgresql+asyncpg``. Bare ``postgresql://`` likewise.
        2. The ``sslmode`` query param — that's libpq / psycopg syntax;
           asyncpg uses ``ssl=`` and rejects ``sslmode`` as an unknown
           kwarg. Fly's ``flycast`` hostname goes over Fly's internal
           wireguard mesh, so no SSL is needed; just drop the param.

        URLs already in the asyncpg form (or pinned to another explicit
        driver like ``postgresql+psycopg``) are passed through unchanged.
        """
        if not v.startswith("postgresql+"):
            if v.startswith("postgres://"):
                v = "postgresql+asyncpg://" + v[len("postgres://") :]
            elif v.startswith("postgresql://"):
                v = "postgresql+asyncpg://" + v[len("postgresql://") :]

        parsed = urlparse(v)
        if parsed.query:
            kept = [
                (k, val)
                for k, val in parse_qsl(parsed.query, keep_blank_values=True)
                if k != "sslmode"
            ]
            v = urlunparse(parsed._replace(query=urlencode(kept)))
        return v

    # Inter-agent boundary (Phase 8 + dispatcher). When either is unset the
    # dispatcher still runs detect_overdue_passes for state hygiene but skips
    # outbound webhooks -- handy for local dev without a parent-comms agent.
    parent_comms_url: str | None = Field(default=None)
    parent_comms_secret: str | None = Field(default=None)
    dispatcher_interval_seconds: float = Field(default=30.0)

    # OpenAI / Codex hackathon credentials (Phase 5c embeddings + Phase 7
    # agent loop). Tests inject a stub Embedder so OPENAI_API_KEY is only
    # required at runtime when an OpenAI-backed component actually runs.
    openai_api_key: str | None = Field(default=None)
    openai_project_id: str | None = Field(default=None)
    openai_model: str = Field(default="gpt-4o-mini")
    openai_embedding_model: str = Field(default="text-embedding-3-small")

    # CORS allow-list for the deployed frontend. Override per-deploy:
    # multiple origins can be comma-separated. Localhost dev URLs are
    # always allowed via a regex regardless of this setting.
    frontend_origin: str = Field(default="https://verdant-pie-1d3c9f.netlify.app")


@lru_cache
def get_settings() -> Settings:
    return Settings()
