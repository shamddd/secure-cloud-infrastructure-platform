from __future__ import annotations

import asyncio
import getpass
import os

from secure_cloud_platform.config import get_settings
from secure_cloud_platform.database import Database
from secure_cloud_platform.models import Role
from secure_cloud_platform.schemas import UserCreate
from secure_cloud_platform.security import PasswordService
from secure_cloud_platform.services import create_user


async def _bootstrap() -> None:
    settings = get_settings()
    username = os.getenv("SCIP_BOOTSTRAP_ADMIN_USERNAME", "admin")
    password = os.getenv("SCIP_BOOTSTRAP_ADMIN_PASSWORD") or getpass.getpass(
        "Initial admin password: "
    )
    database = Database(settings.database_url)
    try:
        async with database.sessions() as session, session.begin():
            await create_user(
                session,
                PasswordService(),
                UserCreate(username=username, password=password, role=Role.ADMIN),
                actor="bootstrap",
            )
    finally:
        await database.dispose()
    print(f"Created administrator {username!r}; no password was logged.")


def bootstrap_admin() -> None:
    asyncio.run(_bootstrap())
