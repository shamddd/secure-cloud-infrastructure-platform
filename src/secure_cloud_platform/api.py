from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Query, Response, status

from secure_cloud_platform.dependencies import (
    PasswordDep,
    SessionDep,
    TokenServiceDep,
    authorize,
)
from secure_cloud_platform.manifest import build_kubernetes_manifest
from secure_cloud_platform.models import Role, SubjectType
from secure_cloud_platform.schemas import (
    AuditEventRead,
    ServiceAccountCreate,
    ServiceAccountCreated,
    ServiceTokenRequest,
    TokenResponse,
    UserCreate,
    UserRead,
    WorkloadCreate,
    WorkloadRead,
    WorkloadScale,
)
from secure_cloud_platform.security import Principal, Scope, parse_scopes
from secure_cloud_platform.services import (
    authenticate_service_account,
    authenticate_user,
    create_service_account,
    create_user,
    create_workload,
    delete_workload,
    get_workload,
    list_audit_events,
    list_workloads,
    scale_workload,
)

router = APIRouter(prefix="/v1")

AdminWrite = Annotated[
    Principal,
    Depends(authorize(minimum_role=Role.ADMIN, scopes=frozenset({Scope.IDENTITIES_WRITE}))),
]
WorkloadReader = Annotated[
    Principal,
    Depends(authorize(minimum_role=Role.VIEWER, scopes=frozenset({Scope.WORKLOADS_READ}))),
]
WorkloadWriter = Annotated[
    Principal,
    Depends(authorize(minimum_role=Role.OPERATOR, scopes=frozenset({Scope.WORKLOADS_WRITE}))),
]
WorkloadAdmin = Annotated[
    Principal,
    Depends(authorize(minimum_role=Role.ADMIN, scopes=frozenset({Scope.WORKLOADS_DELETE}))),
]
AuditReader = Annotated[
    Principal,
    Depends(authorize(minimum_role=Role.ADMIN, scopes=frozenset({Scope.AUDIT_READ}))),
]


@router.post("/auth/token", response_model=TokenResponse, tags=["authentication"])
async def user_token(
    session: SessionDep,
    passwords: PasswordDep,
    tokens: TokenServiceDep,
    username: Annotated[str, Form(min_length=3, max_length=64)],
    password: Annotated[str, Form(min_length=1, max_length=256)],
) -> TokenResponse:
    user = await authenticate_user(
        session,
        passwords,
        username=username,
        password=password,
    )
    token, expires_in = tokens.issue(
        subject=user.username,
        subject_type=SubjectType.USER,
        role=Role(user.role),
    )
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post("/auth/service-token", response_model=TokenResponse, tags=["authentication"])
async def service_token(
    request: ServiceTokenRequest,
    session: SessionDep,
    passwords: PasswordDep,
    tokens: TokenServiceDep,
) -> TokenResponse:
    account = await authenticate_service_account(
        session,
        passwords,
        client_id=request.client_id,
        client_secret=request.client_secret,
    )
    token, expires_in = tokens.issue(
        subject=account.client_id,
        subject_type=SubjectType.SERVICE,
        role=Role(account.role),
        scopes=parse_scopes(account.scopes),
    )
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    tags=["identities"],
)
async def add_user(
    request: UserCreate,
    session: SessionDep,
    passwords: PasswordDep,
    principal: AdminWrite,
) -> UserRead:
    user = await create_user(session, passwords, request, actor=principal.subject)
    return UserRead.model_validate(user)


@router.post(
    "/service-accounts",
    response_model=ServiceAccountCreated,
    status_code=status.HTTP_201_CREATED,
    tags=["identities"],
)
async def add_service_account(
    request: ServiceAccountCreate,
    session: SessionDep,
    passwords: PasswordDep,
    principal: AdminWrite,
) -> ServiceAccountCreated:
    account, client_secret = await create_service_account(
        session,
        passwords,
        request,
        actor=principal.subject,
    )
    return ServiceAccountCreated(
        id=account.id,
        client_id=account.client_id,
        name=account.name,
        role=Role(account.role),
        scopes=[Scope(value) for value in account.scopes],
        client_secret=client_secret,
    )


@router.post(
    "/workloads",
    response_model=WorkloadRead,
    status_code=status.HTTP_201_CREATED,
    tags=["workloads"],
)
async def add_workload(
    request: WorkloadCreate,
    session: SessionDep,
    principal: WorkloadWriter,
) -> WorkloadRead:
    workload = await create_workload(session, request, actor=principal.subject)
    return WorkloadRead.model_validate(workload)


@router.get("/workloads", response_model=list[WorkloadRead], tags=["workloads"])
async def workloads(
    session: SessionDep,
    principal: WorkloadReader,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[WorkloadRead]:
    del principal
    return [
        WorkloadRead.model_validate(item) for item in await list_workloads(session, limit=limit)
    ]


@router.get("/workloads/{workload_id}", response_model=WorkloadRead, tags=["workloads"])
async def workload(
    workload_id: str,
    session: SessionDep,
    principal: WorkloadReader,
) -> WorkloadRead:
    del principal
    return WorkloadRead.model_validate(await get_workload(session, workload_id))


@router.get("/workloads/{workload_id}/manifest", tags=["workloads"])
async def workload_manifest(
    workload_id: str,
    session: SessionDep,
    principal: WorkloadReader,
) -> dict[str, Any]:
    del principal
    return build_kubernetes_manifest(await get_workload(session, workload_id))


@router.patch(
    "/workloads/{workload_id}/scale",
    response_model=WorkloadRead,
    tags=["workloads"],
)
async def scale(
    workload_id: str,
    request: WorkloadScale,
    session: SessionDep,
    principal: WorkloadWriter,
) -> WorkloadRead:
    result = await scale_workload(
        session,
        workload_id=workload_id,
        replicas=request.replicas,
        expected_version=request.expected_version,
        actor=principal.subject,
    )
    return WorkloadRead.model_validate(result)


@router.delete(
    "/workloads/{workload_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["workloads"],
)
async def remove_workload(
    workload_id: str,
    session: SessionDep,
    principal: WorkloadAdmin,
) -> Response:
    await delete_workload(session, workload_id, actor=principal.subject)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/audit-events", response_model=list[AuditEventRead], tags=["audit"])
async def audit_events(
    session: SessionDep,
    principal: AuditReader,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[AuditEventRead]:
    del principal
    return [
        AuditEventRead.model_validate(event)
        for event in await list_audit_events(session, limit=limit)
    ]
