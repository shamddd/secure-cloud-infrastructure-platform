from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from secure_cloud_platform.errors import AuthenticationError, ConflictError, NotFoundError
from secure_cloud_platform.models import AuditEvent, ServiceAccount, User, Workload
from secure_cloud_platform.schemas import ServiceAccountCreate, UserCreate, WorkloadCreate
from secure_cloud_platform.security import ROLE_SCOPES, PasswordService


async def record_audit(
    session: AsyncSession,
    *,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditEvent(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome="success",
            details=details or {},
        )
    )


async def create_user(
    session: AsyncSession,
    passwords: PasswordService,
    request: UserCreate,
    *,
    actor: str,
) -> User:
    user = User(
        username=request.username,
        password_hash=passwords.hash(request.password),
        role=request.role.value,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError("username already exists") from exc
    await record_audit(
        session,
        actor=actor,
        action="identity.user.create",
        resource_type="user",
        resource_id=user.id,
        details={"username": user.username, "role": user.role},
    )
    return user


async def authenticate_user(
    session: AsyncSession,
    passwords: PasswordService,
    *,
    username: str,
    password: str,
) -> User:
    user = await session.scalar(select(User).where(User.username == username))
    if user is None or user.disabled or not passwords.verify(user.password_hash, password):
        raise AuthenticationError("invalid credentials")
    return user


async def create_service_account(
    session: AsyncSession,
    passwords: PasswordService,
    request: ServiceAccountCreate,
    *,
    actor: str,
) -> tuple[ServiceAccount, str]:
    requested_scopes = frozenset(request.scopes) if request.scopes else ROLE_SCOPES[request.role]
    if not requested_scopes.issubset(ROLE_SCOPES[request.role]):
        raise ConflictError("requested scopes exceed the selected role")
    client_secret = passwords.generate_service_secret()
    account = ServiceAccount(
        client_id=str(uuid4()),
        name=request.name,
        secret_hash=passwords.hash(client_secret),
        role=request.role.value,
        scopes=sorted(scope.value for scope in requested_scopes),
    )
    session.add(account)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError("service account name already exists") from exc
    await record_audit(
        session,
        actor=actor,
        action="identity.service_account.create",
        resource_type="service_account",
        resource_id=account.id,
        details={"name": account.name, "role": account.role, "scopes": account.scopes},
    )
    return account, client_secret


async def authenticate_service_account(
    session: AsyncSession,
    passwords: PasswordService,
    *,
    client_id: str,
    client_secret: str,
) -> ServiceAccount:
    account = await session.scalar(
        select(ServiceAccount).where(ServiceAccount.client_id == client_id)
    )
    if (
        account is None
        or account.disabled
        or not passwords.verify(account.secret_hash, client_secret)
    ):
        raise AuthenticationError("invalid credentials")
    return account


async def create_workload(
    session: AsyncSession,
    request: WorkloadCreate,
    *,
    actor: str,
) -> Workload:
    workload = Workload(
        name=request.name,
        image=request.image,
        replicas=request.replicas,
        container_port=request.container_port,
        created_by=actor,
    )
    session.add(workload)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise ConflictError("workload name already exists") from exc
    await record_audit(
        session,
        actor=actor,
        action="workload.create",
        resource_type="workload",
        resource_id=workload.id,
        details={"name": workload.name, "image": workload.image, "replicas": workload.replicas},
    )
    return workload


async def list_workloads(session: AsyncSession, *, limit: int) -> Sequence[Workload]:
    result = await session.scalars(
        select(Workload).where(Workload.status != "deleted").order_by(Workload.name).limit(limit)
    )
    return result.all()


async def get_workload(session: AsyncSession, workload_id: str) -> Workload:
    workload = await session.scalar(
        select(Workload).where(Workload.id == workload_id, Workload.status != "deleted")
    )
    if workload is None:
        raise NotFoundError("workload not found")
    return workload


async def scale_workload(
    session: AsyncSession,
    *,
    workload_id: str,
    replicas: int,
    expected_version: int,
    actor: str,
) -> Workload:
    result = await session.execute(
        update(Workload)
        .where(
            Workload.id == workload_id,
            Workload.status != "deleted",
            Workload.version == expected_version,
        )
        .values(replicas=replicas, version=Workload.version + 1)
        .returning(Workload)
    )
    workload = result.scalar_one_or_none()
    if workload is None:
        exists = await session.scalar(select(Workload.id).where(Workload.id == workload_id))
        if exists is None:
            raise NotFoundError("workload not found")
        raise ConflictError("workload version changed; reload before retrying")
    await record_audit(
        session,
        actor=actor,
        action="workload.scale",
        resource_type="workload",
        resource_id=workload.id,
        details={"replicas": replicas, "version": workload.version},
    )
    return workload


async def delete_workload(session: AsyncSession, workload_id: str, *, actor: str) -> None:
    workload = await get_workload(session, workload_id)
    workload.status = "deleted"
    workload.version += 1
    await record_audit(
        session,
        actor=actor,
        action="workload.delete",
        resource_type="workload",
        resource_id=workload.id,
        details={"name": workload.name},
    )


async def list_audit_events(session: AsyncSession, *, limit: int) -> Sequence[AuditEvent]:
    result = await session.scalars(
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    )
    return result.all()


async def reset_all_data(session: AsyncSession) -> None:
    """Test-only helper used by integration fixtures."""
    for model in (AuditEvent, Workload, ServiceAccount, User):
        await session.execute(delete(model))
