from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import (
    CurrentUser,
    DatabaseSession,
    default_rate_limiter,
    get_auth_service,
    require_mfa,
    require_permission,
)
from app.core.rbac import Permission
from app.core.security import generate_api_key
from app.domain.auth.entities import ApiKey
from app.domain.auth.services import AuthService
from app.infrastructure.database.repositories.auth import SQLAlchemyApiKeyRepository

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.API_KEYS_MANAGE))])


class CreateApiKeyRequest(BaseModel):
    name: str
    scopes: list[str] = []


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: list[str]
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None = None


class ApiKeyCreatedResponse(ApiKeyResponse):
    raw_key: str


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateApiKeyRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
    _mfa: Annotated[None, Depends(require_mfa)] = None,
):
    if current_user.get("auth_type") == "api_key":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create API keys when authenticated with an API key",
        )

    tenant_id = current_user["tenant_id"]
    repo = SQLAlchemyApiKeyRepository(session)

    raw_key, key_hash, prefix = generate_api_key()
    api_key = ApiKey(
        tenant_id=tenant_id,
        name=request.name,
        key_hash=key_hash,
        key_prefix=prefix,
        scopes=request.scopes,
        created_by=current_user.get("user_id"),
    )
    created = await repo.create(api_key)
    await session.commit()

    return ApiKeyCreatedResponse(
        id=created.id,
        name=created.name,
        key_prefix=created.key_prefix,
        scopes=created.scopes,
        is_active=created.is_active,
        created_at=created.created_at,
        raw_key=raw_key,
    )


@router.get("")
async def list_api_keys(
    current_user: CurrentUser,
    session: DatabaseSession,
    _mfa: Annotated[None, Depends(require_mfa)] = None,
):
    tenant_id = current_user["tenant_id"]
    repo = SQLAlchemyApiKeyRepository(session)
    keys = await repo.list_by_tenant(tenant_id)
    return {
        "data": [
            ApiKeyResponse(
                id=k.id,
                name=k.name,
                key_prefix=k.key_prefix,
                scopes=k.scopes,
                is_active=k.is_active,
                created_at=k.created_at,
                last_used_at=k.last_used_at,
            )
            for k in keys
        ]
    }


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
    _mfa: Annotated[None, Depends(require_mfa)] = None,
):
    if current_user.get("auth_type") == "api_key":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot revoke API keys when authenticated with an API key",
        )

    repo = SQLAlchemyApiKeyRepository(session)
    await repo.revoke(key_id)
    await session.commit()
    return {"message": "API key revoked"}
