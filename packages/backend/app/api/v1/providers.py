from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import Optional

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.rbac import Permission

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.PROVIDERS_READ))])


class CreateProviderRequest(BaseModel):
    name: str
    provider_type: str
    api_key: Optional[str] = None
    models: list[str] = []
    config: dict = {}


@router.get("")
async def list_providers(current_user: CurrentUser, session: DatabaseSession):
    return {"data": []}


@router.post("", status_code=201)
async def create_provider(
    request: CreateProviderRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"provider": {}}


@router.post("/{provider_id}/test")
async def test_provider(
    provider_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"success": True, "latency_ms": 0, "models_available": []}


@router.delete("/{provider_id}")
async def delete_provider(
    provider_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    return {"message": "Provider deleted"}
