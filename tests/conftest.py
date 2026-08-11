from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from secure_cloud_platform.config import Environment, Settings
from secure_cloud_platform.main import create_app
from secure_cloud_platform.models import Role
from secure_cloud_platform.schemas import UserCreate
from secure_cloud_platform.services import create_user

TEST_SIGNING_KEY = "test-signing-key-with-at-least-thirty-two-characters"
ADMIN_PASSWORD = "Admin-Passphrase-2026!"
OPERATOR_PASSWORD = "Operator-Passphrase-2026!"
VIEWER_PASSWORD = "Viewer-Passphrase-2026!"


async def seed_identities(app: FastAPI) -> None:
    database = app.state.database
    passwords = app.state.password_service
    async with database.sessions() as session, session.begin():
        for username, password, role in (
            ("admin", ADMIN_PASSWORD, Role.ADMIN),
            ("operator", OPERATOR_PASSWORD, Role.OPERATOR),
            ("viewer", VIEWER_PASSWORD, Role.VIEWER),
        ):
            await create_user(
                session,
                passwords,
                UserCreate(username=username, password=password, role=role),
                actor="test-bootstrap",
            )


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    database_path = tmp_path / "platform.db"
    settings = Settings(
        environment=Environment.TEST,
        database_url=f"sqlite+aiosqlite:///{database_path}",
        jwt_signing_key=TEST_SIGNING_KEY,
        allowed_hosts=["testserver"],
        auto_create_schema=True,
        docs_enabled=True,
        metrics_enabled=True,
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        asyncio.run(seed_identities(app))
        yield test_client


def token_for(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/v1/auth/token",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return str(response.json()["access_token"])


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
