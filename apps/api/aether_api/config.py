# SCORE-IMPACT: Stability, operability, and demo repeatability.
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_seed_path() -> Path:
    return Path(__file__).resolve().parents[3] / "infra" / "seed" / "scenic_demo.json"


def default_admin_seed_path() -> Path:
    return Path(__file__).resolve().parents[3] / "infra" / "seed" / "admins.yaml"


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
    admin_seed_path: Path = Field(default_factory=default_admin_seed_path)
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    jwt_secret: SecretStr = Field(
        default=SecretStr("dev-only-secret-change-me-in-production")
    )
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    tourist_token_ttl_minutes: int = Field(default=1440, ge=1)
    admin_token_ttl_minutes: int = Field(default=480, ge=1)

    model_config = SettingsConfigDict(
        env_prefix="AETHER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        # Support "a,b,c" comma-separated env value as well as list[str].
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _guard_production_config(self) -> "Settings":
        if self.environment == "production":
            if "*" in self.cors_origins:
                raise ValueError(
                    "AETHER_CORS_ORIGINS must not contain '*' in production."
                )
            if self.jwt_secret.get_secret_value().startswith("dev-only-secret"):
                raise ValueError(
                    "AETHER_JWT_SECRET must be overridden in production."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
