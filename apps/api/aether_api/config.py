# SCORE-IMPACT: Stability, operability, and demo repeatability.
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_seed_path() -> Path:
    return Path(__file__).resolve().parents[3] / "infra" / "seed" / "scenic_demo.json"


def default_admin_seed_path() -> Path:
    return Path(__file__).resolve().parents[3] / "infra" / "seed" / "admins.yaml"


def default_env_files() -> tuple[Path, Path, str]:
    root = Path(__file__).resolve().parents[3]
    return (root / ".env", root / ".env.local", ".env")


class Settings(BaseSettings):
    app_name: str = "Aether Guide API"
    environment: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    admin_prefix: str = "/admin/v1"
    storage_mode: Literal["inmemory", "database"] = "inmemory"
    ai_provider: Literal["fake", "litellm", "anthropic", "openai"] = "fake"
    ai_fake_fallback_enabled: bool = False
    database_url: str = "sqlite+aiosqlite:///./.local/aether.db"
    redis_url: str = "redis://localhost:6379/0"
    llm_timeout_seconds: float = 6.0
    llm_max_tokens: int = Field(default=700, ge=1)
    llm_temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    llm_thinking_type: Literal["disabled", "enabled", "adaptive", "auto", "omit"] = Field(
        default="disabled",
        validation_alias=AliasChoices(
            "AETHER_LLM_THINKING_TYPE",
            "ANTHROPIC_THINKING_TYPE",
        ),
    )
    llm_thinking_budget_tokens: int | None = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices(
            "AETHER_LLM_THINKING_BUDGET_TOKENS",
            "ANTHROPIC_THINKING_BUDGET_TOKENS",
        ),
    )
    llm_max_retries: int = 2
    anthropic_base_url: str = Field(
        default="https://ark.cn-beijing.volces.com/api/coding",
        validation_alias=AliasChoices(
            "AETHER_ANTHROPIC_BASE_URL",
        ),
    )
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AETHER_ANTHROPIC_API_KEY",
        ),
    )
    anthropic_model: str = Field(
        default="",
        validation_alias=AliasChoices(
            "AETHER_ANTHROPIC_MODEL",
        ),
    )
    anthropic_version: str = Field(
        default="2023-06-01",
        validation_alias=AliasChoices(
            "AETHER_ANTHROPIC_VERSION",
        ),
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AETHER_OPENAI_API_KEY"),
    )
    openai_base_url: str = Field(
        default="https://ark.cn-beijing.volces.com/api/coding/v3",
        validation_alias=AliasChoices("AETHER_OPENAI_BASE_URL"),
    )
    vlm_model: str = Field(
        default="doubao-seed-2.0-pro",
        validation_alias=AliasChoices("AETHER_VLM_MODEL"),
    )
    tts_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AETHER_TTS_API_KEY"),
    )
    tts_base_url: str = Field(
        default="https://token-plan-cn.xiaomimimo.com/v1",
        validation_alias=AliasChoices("AETHER_TTS_BASE_URL"),
    )
    tts_model: str = Field(
        default="mimo-v2.5-tts",
        validation_alias=AliasChoices("AETHER_TTS_MODEL"),
    )
    tts_voice: str = Field(
        default="female-tianmei",
        validation_alias=AliasChoices("AETHER_TTS_VOICE"),
    )
    qdrant_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AETHER_QDRANT_URL", "QDRANT_URL"),
    )
    qdrant_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AETHER_QDRANT_API_KEY", "QDRANT_API_KEY"),
    )
    embedding_model_name: str = Field(
        default="BAAI/bge-m3",
        validation_alias=AliasChoices("AETHER_EMBEDDING_MODEL", "EMBEDDING_MODEL"),
    )
    embedding_use_gpu: bool = Field(
        default=False,
        validation_alias=AliasChoices("AETHER_EMBEDDING_USE_GPU", "EMBEDDING_USE_GPU"),
    )

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
        env_file=default_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
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
