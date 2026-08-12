from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError
from pydantic import BaseModel, ConfigDict, ValidationError

from secure_cloud_platform.config import Settings
from secure_cloud_platform.errors import AuthenticationError, AuthorizationError
from secure_cloud_platform.models import Role, SubjectType


class Scope(StrEnum):
    WORKLOADS_READ = "workloads:read"
    WORKLOADS_WRITE = "workloads:write"
    WORKLOADS_DELETE = "workloads:delete"
    IDENTITIES_WRITE = "identities:write"
    AUDIT_READ = "audit:read"


ROLE_SCOPES: dict[Role, frozenset[Scope]] = {
    Role.VIEWER: frozenset({Scope.WORKLOADS_READ}),
    Role.OPERATOR: frozenset({Scope.WORKLOADS_READ, Scope.WORKLOADS_WRITE}),
    Role.ADMIN: frozenset(Scope),
}

ROLE_LEVEL: dict[Role, int] = {
    Role.VIEWER: 10,
    Role.OPERATOR: 20,
    Role.ADMIN: 30,
}


class TokenClaims(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sub: str
    subject_type: SubjectType
    role: Role
    scopes: list[Scope]
    iss: str
    aud: str | list[str]
    iat: int
    nbf: int
    exp: int
    jti: str


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    subject_type: SubjectType
    role: Role
    scopes: frozenset[Scope]
    token_id: str

    def has_scope(self, scope: Scope) -> bool:
        return scope in self.scopes

    def require(self, *, minimum_role: Role, scopes: frozenset[Scope]) -> None:
        if ROLE_LEVEL[self.role] < ROLE_LEVEL[minimum_role]:
            raise AuthorizationError("insufficient role")
        if not scopes.issubset(self.scopes):
            raise AuthorizationError("missing required scope")


class PasswordService:
    """Argon2id hashing for human passwords and service credentials."""

    def __init__(self) -> None:
        self._hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65_536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
        )

    def hash(self, value: str) -> str:
        return self._hasher.hash(value)

    def verify(self, encoded: str, candidate: str) -> bool:
        try:
            return self._hasher.verify(encoded, candidate)
        except (VerificationError, InvalidHash, Exception):
            return False

    @staticmethod
    def generate_service_secret() -> str:
        return secrets.token_urlsafe(32)


class TokenService:
    def __init__(self, settings: Settings) -> None:
        self._key = settings.jwt_signing_key.get_secret_value()
        self._issuer = settings.jwt_issuer
        self._audience = settings.jwt_audience
        self._key_id = settings.jwt_key_id
        self._ttl = settings.access_token_ttl_seconds

    def issue(
        self,
        *,
        subject: str,
        subject_type: SubjectType,
        role: Role,
        scopes: frozenset[Scope] | None = None,
    ) -> tuple[str, int]:
        allowed = ROLE_SCOPES[role]
        effective_scopes = allowed if scopes is None else allowed.intersection(scopes)
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=self._ttl)
        claims: dict[str, Any] = {
            "sub": subject,
            "subject_type": subject_type.value,
            "role": role.value,
            "scopes": sorted(scope.value for scope in effective_scopes),
            "iss": self._issuer,
            "aud": self._audience,
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int(expires.timestamp()),
            "jti": str(uuid4()),
        }
        encoded = jwt.encode(
            claims,
            self._key,
            algorithm="HS256",
            headers={"kid": self._key_id, "typ": "JWT"},
        )
        token = encoded.decode("utf-8") if isinstance(encoded, bytes) else encoded
        return token, self._ttl

    def decode(self, token: str) -> Principal:
        try:
            payload = jwt.decode(
                token,
                self._key,
                algorithms=["HS256"],
                audience=self._audience,
                issuer=self._issuer,
                leeway=5,
                options={
                    "require": [
                        "sub",
                        "subject_type",
                        "role",
                        "scopes",
                        "iss",
                        "aud",
                        "iat",
                        "nbf",
                        "exp",
                        "jti",
                    ]
                },
            )
            claims = TokenClaims.model_validate(payload)
        except (jwt.PyJWTError, ValidationError, ValueError) as exc:
            raise AuthenticationError("invalid or expired access token") from exc

        allowed = ROLE_SCOPES[claims.role]
        claimed = frozenset(claims.scopes)
        if not claimed.issubset(allowed):
            raise AuthenticationError("token contains scopes outside its role")
        return Principal(
            subject=claims.sub,
            subject_type=claims.subject_type,
            role=claims.role,
            scopes=claimed,
            token_id=claims.jti,
        )


def parse_scopes(values: list[str]) -> frozenset[Scope]:
    try:
        return frozenset(Scope(value) for value in values)
    except ValueError as exc:
        raise AuthorizationError("unknown scope requested") from exc
