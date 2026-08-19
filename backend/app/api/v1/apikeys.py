from __future__ import annotations

from fastapi import APIRouter, Body

from typing import Annotated

from fastapi import APIRouter, Body, Depends

from app.api.deps import DbSession, require_permission
from app.api.serializers import user_out  # noqa: F401  (kept for symmetric imports)
from app.core.exceptions import NotFoundError
from app.services.api_keys import APIKeyService
from app.services.audit import AuditService

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

ApiKeyManageUser = Annotated[dict, Depends(require_permission("api_keys:manage"))]
ApiKeyReadUser = Annotated[dict, Depends(require_permission("api_keys:read"))]


@router.post("")
async def create_key(
    db: DbSession,
    user: ApiKeyManageUser,
    name: str = Body(...),
    scopes: list[str] | None = Body(default=None),
    quota_per_minute: int = Body(default=60),
    expires_in_days: int | None = Body(default=90),
) -> dict:
    """Issue a new API key. The raw key is returned exactly once."""
    key = await APIKeyService(db).issue(
        user_id=user["sub"],
        name=name,
        scopes=scopes,
        quota_per_minute=quota_per_minute,
        expires_in_days=expires_in_days,
    )
    await AuditService(db).log(
        event_type="api_key.created",
        actor=user["sub"],
        subject=key["id"],
        payload={"name": key["name"], "prefix": key["key_prefix"]},
    )
    return {"api_key": key}


@router.get("")
async def list_keys(db: DbSession, user: ApiKeyReadUser) -> dict:
    keys = await APIKeyService(db).list_keys(user["sub"])
    return {"api_keys": keys}


@router.post("/{key_id}/revoke")
async def revoke_key(key_id: str, db: DbSession, user: ApiKeyManageUser) -> dict:
    service = APIKeyService(db)
    key = await service.revoke(key_id, user_id=user["sub"])
    await AuditService(db).log(
        event_type="api_key.revoked",
        actor=user["sub"],
        subject=key_id,
        payload={"name": key.name},
    )
    return {"id": key.id, "is_active": key.is_active}
