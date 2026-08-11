from __future__ import annotations

import asyncio
import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient

from secure_cloud_platform.config import Environment, Settings
from secure_cloud_platform.main import create_app
from tests.conftest import OPERATOR_PASSWORD, auth, seed_identities, token_for

pytestmark = pytest.mark.postgres


async def seed_and_release_connections(app: FastAPI) -> None:
    await seed_identities(app)
    await app.state.database.dispose()


def test_postgres_migration_and_workload_lifecycle() -> None:
    database_url = os.environ.get("SCIP_TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("SCIP_TEST_POSTGRES_URL is not configured")

    previous_url = os.environ.get("SCIP_DATABASE_URL")
    os.environ["SCIP_DATABASE_URL"] = database_url
    alembic = Config("alembic.ini")
    upgraded = False
    try:
        command.upgrade(alembic, "head")
        upgraded = True
        settings = Settings(
            environment=Environment.TEST,
            database_url=database_url,
            jwt_signing_key="postgres-test-signing-key-with-at-least-thirty-two-characters",
            allowed_hosts=["testserver"],
            auto_create_schema=False,
            docs_enabled=False,
            metrics_enabled=False,
        )
        app = create_app(settings)
        asyncio.run(seed_and_release_connections(app))
        with TestClient(app) as client:
            token = token_for(client, "operator", OPERATOR_PASSWORD)
            response = client.post(
                "/v1/workloads",
                headers=auth(token),
                json={
                    "name": "postgres-backed",
                    "image": "registry.example.test/api@sha256:" + "c" * 64,
                    "replicas": 2,
                },
            )
            assert response.status_code == 201, response.text
            assert client.get("/health/ready").json() == {"status": "ready"}
    finally:
        if upgraded:
            command.downgrade(alembic, "base")
        if previous_url is None:
            os.environ.pop("SCIP_DATABASE_URL", None)
        else:
            os.environ["SCIP_DATABASE_URL"] = previous_url
