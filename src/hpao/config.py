from functools import lru_cache

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
        """Coerce bare ``postgres://`` and ``postgresql://`` URLs into the
        ``postgresql+asyncpg://`` form SQLAlchemy 2.0 + asyncpg expects.

        ``fly postgres attach`` writes a bare ``postgres://`` URL into
        ``DATABASE_URL``; without this the app would crash on first connect
        and require a manual ``fly secrets set DATABASE_URL=postgresql+asyncpg://...``.
        URLs that already specify a driver (``postgresql+asyncpg://``,
        ``postgresql+psycopg://``, etc.) are passed through unchanged.
        """
        if v.startswith("postgresql+"):
            return v
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v[len("postgresql://") :]
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
