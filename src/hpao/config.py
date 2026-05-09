from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(...)
    app_env: str = Field(default="dev")

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
