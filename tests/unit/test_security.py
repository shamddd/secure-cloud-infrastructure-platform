from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from secure_cloud_platform.config import Environment, Settings
from secure_cloud_platform.errors import AuthenticationError, AuthorizationError
from secure_cloud_platform.models import Role, SubjectType
from secure_cloud_platform.security import PasswordService, Scope, TokenService

SIGNING_KEY = "unit-test-signing-key-with-enough-entropy-12345"


def settings() -> Settings:
    return Settings(
        environment=Environment.TEST,
        database_url="sqlite+aiosqlite:///test.db",
        jwt_signing_key=SIGNING_KEY,
        allowed_hosts=["testserver"],
    )


def test_password_hash_is_salted_and_verifiable() -> None:
    passwords = PasswordService()
    first = passwords.hash("correct horse battery staple")
    second = passwords.hash("correct horse battery staple")

    assert first != second
    assert passwords.verify(first, "correct horse battery staple")
    assert not passwords.verify(first, "wrong password")


def test_token_enforces_role_scope_boundary() -> None:
    tokens = TokenService(settings())
    token, _ = tokens.issue(
        subject="viewer",
        subject_type=SubjectType.USER,
        role=Role.VIEWER,
    )
    principal = tokens.decode(token)

    principal.require(minimum_role=Role.VIEWER, scopes=frozenset({Scope.WORKLOADS_READ}))
    with pytest.raises(AuthorizationError):
        principal.require(
            minimum_role=Role.OPERATOR,
            scopes=frozenset({Scope.WORKLOADS_WRITE}),
        )


def test_expired_token_is_rejected() -> None:
    config = settings()
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": "expired-user",
            "subject_type": "user",
            "role": "viewer",
            "scopes": ["workloads:read"],
            "iss": config.jwt_issuer,
            "aud": config.jwt_audience,
            "iat": int((now - timedelta(minutes=5)).timestamp()),
            "nbf": int((now - timedelta(minutes=5)).timestamp()),
            "exp": int((now - timedelta(minutes=1)).timestamp()),
            "jti": "expired-token-id",
        },
        SIGNING_KEY,
        algorithm="HS256",
    )

    with pytest.raises(AuthenticationError):
        TokenService(config).decode(expired)
