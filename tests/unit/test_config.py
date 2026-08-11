from __future__ import annotations

import pytest
from pydantic import ValidationError

from secure_cloud_platform.config import Environment, Settings


def test_production_rejects_sqlite_and_placeholder_configuration() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment=Environment.PRODUCTION,
            database_url="sqlite+aiosqlite:///unsafe.db",
            jwt_signing_key="change-me-this-is-not-a-production-secret",
            allowed_hosts=["*"],
        )


def test_csv_host_and_origin_configuration_is_normalized() -> None:
    settings = Settings(
        environment=Environment.TEST,
        database_url="sqlite+aiosqlite:///test.db",
        jwt_signing_key="a-secure-test-key-that-is-long-enough-1234",
        allowed_hosts="api.example.test, localhost",  # type: ignore[arg-type]
        cors_origins="https://console.example.test",  # type: ignore[arg-type]
    )
    assert settings.allowed_hosts == ["api.example.test", "localhost"]
    assert settings.cors_origins == ["https://console.example.test"]


def test_csv_lists_load_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCIP_ENVIRONMENT", "test")
    monkeypatch.setenv("SCIP_DATABASE_URL", "sqlite+aiosqlite:///environment.db")
    monkeypatch.setenv("SCIP_JWT_SIGNING_KEY", "an-environment-key-that-is-long-enough-1234")
    monkeypatch.setenv("SCIP_ALLOWED_HOSTS", "api,localhost,127.0.0.1")
    monkeypatch.setenv("SCIP_CORS_ORIGINS", "https://console.example.test")

    settings = Settings(_env_file=None)

    assert settings.allowed_hosts == ["api", "localhost", "127.0.0.1"]
    assert settings.cors_origins == ["https://console.example.test"]
