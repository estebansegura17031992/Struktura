"""
Dependencies de autenticación — JWT y roles (R-0107, R-0202).
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.db import get_db
from app.core.exceptions import InsufficientPermissionsError, TokenInvalidError
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if not credentials:
        raise TokenInvalidError()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if not user_id:
            raise TokenInvalidError()
    except JWTError:
        raise TokenInvalidError() from None

    repo = UserRepository(db)
    user = await repo.get_by_id(UUID(user_id))

    if not user or user.deleted_at is not None:
        raise TokenInvalidError()

    return user


def require_role(*roles: str):
    async def _check(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise InsufficientPermissionsError()
        return current_user

    return _check


async def get_refresh_token_from_cookie(request: Request) -> str:
    """
    Extrae el refresh token de la cookie HttpOnly.
    Lee directamente del request para compatibilidad con httpx en tests
    (httpx maneja cookies con path=/auth/refresh de forma diferente a browsers).
    """
    # Intentar desde cookies del request
    token = request.cookies.get("refresh_token")
    if not token:
        raise TokenInvalidError()
    return token


# Tipos anotados para uso limpio en endpoints
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_role("admin"))]
EditorUser = Annotated[User, Depends(require_role("admin", "editor"))]
DB = Annotated[AsyncSession, Depends(get_db)]
RefreshTokenCookie = Annotated[str, Depends(get_refresh_token_from_cookie)]
