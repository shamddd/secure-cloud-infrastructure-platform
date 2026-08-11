from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from secure_cloud_platform.errors import AuthenticationError
from secure_cloud_platform.models import Role
from secure_cloud_platform.security import PasswordService, Principal, Scope, TokenService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async for session in request.app.state.database.session():
        yield session


def get_password_service(request: Request) -> PasswordService:
    return cast(PasswordService, request.app.state.password_service)


def get_token_service(request: Request) -> TokenService:
    return cast(TokenService, request.app.state.token_service)


def get_principal(
    token: Annotated[str, Depends(oauth2_scheme)],
    tokens: Annotated[TokenService, Depends(get_token_service)],
) -> Principal:
    if not token:
        raise AuthenticationError("missing access token")
    return tokens.decode(token)


def authorize(*, minimum_role: Role, scopes: frozenset[Scope]) -> Callable[[Principal], Principal]:
    def dependency(principal: Annotated[Principal, Depends(get_principal)]) -> Principal:
        principal.require(minimum_role=minimum_role, scopes=scopes)
        return principal

    return dependency


SessionDep = Annotated[AsyncSession, Depends(get_session)]
PasswordDep = Annotated[PasswordService, Depends(get_password_service)]
TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]
PrincipalDep = Annotated[Principal, Depends(get_principal)]
