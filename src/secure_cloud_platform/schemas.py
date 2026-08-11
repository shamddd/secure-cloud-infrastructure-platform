from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from secure_cloud_platform.models import Role, WorkloadStatus
from secure_cloud_platform.security import Scope

IMAGE_DIGEST_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9._/-]*(?::[a-zA-Z0-9._-]+)?@sha256:[a-f0-9]{64}$"
)
DNS_LABEL_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth2 token type, not a credential
    expires_in: int


class ServiceTokenRequest(BaseModel):
    client_id: str = Field(min_length=36, max_length=36)
    client_secret: str = Field(min_length=32, max_length=256)


class UserCreate(BaseModel):
    username: str = Field(pattern=r"^[a-z][a-z0-9_.-]{2,63}$")
    password: str = Field(min_length=14, max_length=256)
    role: Role


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    role: Role
    disabled: bool
    created_at: datetime


class ServiceAccountCreate(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9-]{2,63}$")
    role: Role = Role.VIEWER
    scopes: list[Scope] = Field(default_factory=list, max_length=16)


class ServiceAccountCreated(BaseModel):
    id: str
    client_id: str
    name: str
    role: Role
    scopes: list[Scope]
    client_secret: str


class WorkloadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=63)
    image: str = Field(min_length=1, max_length=512)
    replicas: int = Field(default=1, ge=1, le=50)
    container_port: int = Field(default=8080, ge=1, le=65_535)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not DNS_LABEL_PATTERN.fullmatch(value):
            raise ValueError("name must be a Kubernetes-compatible DNS label")
        return value

    @field_validator("image")
    @classmethod
    def require_pinned_image_digest(cls, value: str) -> str:
        if not IMAGE_DIGEST_PATTERN.fullmatch(value):
            raise ValueError("image must be pinned to an immutable sha256 digest")
        return value


class WorkloadScale(BaseModel):
    replicas: int = Field(ge=1, le=50)
    expected_version: int = Field(ge=1)


class WorkloadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    image: str
    replicas: int
    container_port: int
    status: WorkloadStatus
    created_by: str
    version: int
    created_at: datetime
    updated_at: datetime


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor: str
    action: str
    resource_type: str
    resource_id: str
    outcome: str
    details: dict[str, object]
    created_at: datetime
