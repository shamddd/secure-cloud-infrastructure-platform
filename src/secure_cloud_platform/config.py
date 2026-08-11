from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Validated runtime configuration loaded from SCIP_* environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SCIP_",
        extra="ignore",
        case_sensitive=False,
        enable_decoding=False,
    )

    app_name: str = "secure-cloud-infrastructure-platform"
    environment: Environment = Environment.PRODUCTION
    log_level: str = "INFO"
    database_url: str
    jwt_signing_key: SecretStr
    jwt_issuer: str = "secure-cloud-infrastructure-platform"
    jwt_audience: str = "secure-cloud-platform-api"
    jwt_key_id: str = "local-hs256-v1"
    access_token_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    allowed_hosts: list[str] = Field(default_factory=list)
    cors_origins: list[str] = Field(default_factory=list)
    auto_create_schema: bool = False
    docs_enabled: bool = False
    metrics_enabled: bool = True
    otlp_traces_endpoint: str | None = None

    @field_validator("jwt_signing_key")
    @classmethod
    def signing_key_must_be_strong(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if len(raw) < 32:
            raise ValueError("jwt_signing_key must contain at least 32 characters")
        return value

    @field_validator("allowed_hosts", "cors_origins", mode="before")
    @classmethod
    def parse_csv_lists(cls, value: object) -> object:
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def production_guards(self) -> Settings:
        if self.environment is Environment.PRODUCTION:
            if self.database_url.startswith("sqlite"):
                raise ValueError("production requires PostgreSQL, not SQLite")
            if self.auto_create_schema:
                raise ValueError("production must use migrations, not auto_create_schema")
            if not self.allowed_hosts or "*" in self.allowed_hosts:
                raise ValueError("production requires an explicit allowed_hosts list")
            key = self.jwt_signing_key.get_secret_value().lower()
            forbidden = ("change-me", "replace-me", "example", "placeholder")
            if any(marker in key for marker in forbidden):
                raise ValueError("production jwt_signing_key is a placeholder")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
