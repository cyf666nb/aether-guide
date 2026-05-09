# SCORE-IMPACT: Stability, operability, and demo repeatability.
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_seed_path() -> Path:
    return Path(__file__).resolve().parents[3] / "infra" / "seed" / "scenic_demo.json"


class Settings(BaseSettings):
    app_name: str = "Aether Guide API"
    environment: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    admin_prefix: str = "/admin/v1"
    storage_mode: Literal["inmemory", "database"] = "inmemory"
    ai_provider: Literal["fake", "litellm"] = "fake"
    database_url: str = "sqlite+aiosqlite:///./.local/aether.db"
    redis_url: str = "redis://localhost:6379/0"
    llm_timeout_seconds: float = 6.0
    llm_max_retries: int = 2
    rate_limit_per_minute: int = 120
    trace_header_name: str = "X-Trace-Id"
    seed_data_path: Path = Field(default_factory=default_seed_path)
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    model_config = SettingsConfigDict(
        env_prefix="AETHER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

