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


@lru_cache
def get_settings() -> Settings:
    return Settings()
