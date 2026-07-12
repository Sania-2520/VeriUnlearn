from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.dependencies import DatabaseDep, CurrentUser
from app.services.api_key_service import ApiKeyService


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    prefix: str
    scopes: str | None
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreate(BaseModel):
    name: str
    scopes: str | None = None


class ApiKeyCreated(BaseModel):
    key: str
    api_key: ApiKeyResponse


router = APIRouter(prefix="/api-keys", tags=["API Keys"])


@router.post("/", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(body: ApiKeyCreate, user: CurrentUser, db: DatabaseDep):
    service = ApiKeyService(db)
    api_key, raw_key = await service.create_key(user.id, body.name, body.scopes)
    return ApiKeyCreated(
        key=raw_key,
        api_key=ApiKeyResponse(
            id=api_key.id,
            name=api_key.name,
            prefix=api_key.prefix,
            scopes=api_key.scopes,
            is_active=api_key.is_active,
            last_used_at=api_key.last_used_at,
            created_at=api_key.created_at,
        ),
    )


@router.get("/", response_model=list[ApiKeyResponse])
async def list_api_keys(user: CurrentUser, db: DatabaseDep):
    service = ApiKeyService(db)
    keys = await service.list_keys(user.id)
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            prefix=k.prefix,
            scopes=k.scopes,
            is_active=k.is_active,
            last_used_at=k.last_used_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: int, user: CurrentUser, db: DatabaseDep):
    service = ApiKeyService(db)
    try:
        await service.revoke_key(key_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
