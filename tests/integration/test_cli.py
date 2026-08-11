from __future__ import annotations

import asyncio
from pathlib import Path

from pytest import CaptureFixture, MonkeyPatch
from sqlalchemy import select

from secure_cloud_platform.cli import bootstrap_admin
from secure_cloud_platform.config import get_settings
from secure_cloud_platform.database import Database
from secure_cloud_platform.models import User
from secure_cloud_platform.security import PasswordService


async def create_schema(database_url: str) -> None:
    database = Database(database_url)
    await database.create_schema()
    await database.dispose()


async def read_admin(database_url: str) -> User | None:
    database = Database(database_url)
    try:
        async with database.sessions() as session:
            return await session.scalar(select(User).where(User.username == "bootstrap-admin"))
    finally:
        await database.dispose()


def test_bootstrap_admin_hashes_password_and_does_not_print_it(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    password = "Bootstrap-Passphrase-2026!"
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'bootstrap.db'}"
    asyncio.run(create_schema(database_url))
    monkeypatch.setenv("SCIP_ENVIRONMENT", "test")
    monkeypatch.setenv("SCIP_DATABASE_URL", database_url)
    monkeypatch.setenv(
        "SCIP_JWT_SIGNING_KEY", "bootstrap-test-key-with-at-least-thirty-two-characters"
    )
    monkeypatch.setenv("SCIP_BOOTSTRAP_ADMIN_USERNAME", "bootstrap-admin")
    monkeypatch.setenv("SCIP_BOOTSTRAP_ADMIN_PASSWORD", password)
    get_settings.cache_clear()

    try:
        bootstrap_admin()
        output = capsys.readouterr().out
        admin = asyncio.run(read_admin(database_url))
    finally:
        get_settings.cache_clear()

    assert "bootstrap-admin" in output
    assert password not in output
    assert admin is not None
    assert admin.role == "admin"
    assert PasswordService().verify(admin.password_hash, password)
