"""Shared FastAPI dependencies (DI container for the API layer)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.rbac import has_permission
from app.core.security import decode_access_token
from app.db.session import get_db

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    # API-key authenticated (middleware resolved the owning user already).
    api_user = getattr(request.state, "api_key_user", None)
    if api_user is not None:
        return api_user
    if credentials is None:
        raise UnauthorizedError("Missing bearer token")
    payload = decode_access_token(credentials.credentials)
    return {"sub": payload["sub"], "role": payload.get("role", "operator")}


CurrentUser = Annotated[dict, Depends(get_current_user)]


def require_roles(*roles: str):
    def checker(user: CurrentUser) -> dict:
        if user["role"] not in roles:
            raise ForbiddenError(f"Requires role(s): {', '.join(roles)}")
        return user

    return checker


def require_permission(permission: str):
    """RBAC dependency: the caller's role must grant ``permission``."""

    def checker(user: CurrentUser) -> dict:
        if not has_permission(user["role"], permission):
            raise ForbiddenError(f"Missing permission: {permission}")
        return user

    return checker


AdminUser = Annotated[dict, Depends(require_roles("admin"))]
