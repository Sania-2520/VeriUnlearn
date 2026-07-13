from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, desc, update as sa_update

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.infrastructure.database.models import AIProviderModel
from app.infrastructure.external.ml_engine import ml_engine_client, MLEngineClientError

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter), Depends(require_permission(Permission.PROVIDERS_READ))])


class CreateProviderRequest(BaseModel):
    name: str
    provider_type: str
    api_key: Optional[str] = None
    models: list[str] = []
    config: dict = {}


@router.get("")
async def list_providers(current_user: CurrentUser, session: DatabaseSession):
    result = await session.execute(
        select(AIProviderModel).where(
            AIProviderModel.tenant_id == current_user["tenant_id"],
            AIProviderModel.is_deleted == False,
        ).order_by(desc(AIProviderModel.created_at))
    )
    providers = result.scalars().all()
    return {
        "data": [
            {
                "id": p.id,
                "name": p.name,
                "provider_type": p.provider_type,
                "models": p.models or [],
                "is_active": p.is_active,
                "last_tested_at": p.last_tested_at.isoformat() if p.last_tested_at else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in providers
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_provider(
    request: CreateProviderRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    now = datetime.now(timezone.utc)
    provider = AIProviderModel(
        id=str(uuid4()),
        tenant_id=current_user["tenant_id"],
        name=request.name,
        provider_type=request.provider_type,
        api_key_encrypted=request.api_key,
        models=request.models,
        config=request.config,
        created_by=current_user["user_id"],
        created_at=now,
        updated_at=now,
    )
    session.add(provider)
    await session.commit()
    await session.refresh(provider)
    return {
        "provider": {
            "id": provider.id,
            "name": provider.name,
            "provider_type": provider.provider_type,
            "models": provider.models or [],
            "created_at": provider.created_at.isoformat() if provider.created_at else None,
        }
    }


@router.post("/{provider_id}/test")
async def test_provider(
    provider_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    result = await session.execute(
        select(AIProviderModel).where(
            AIProviderModel.id == provider_id,
            AIProviderModel.tenant_id == current_user["tenant_id"],
            AIProviderModel.is_deleted == False,
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    try:
        test_result = await ml_engine_client.test_provider(
            provider_type=provider.provider_type,
            config=provider.config or {},
            api_key=provider.api_key_encrypted,
        )
        provider.last_tested_at = datetime.now(timezone.utc)
        await session.commit()
        return test_result
    except MLEngineClientError as e:
        logger.error("Provider test failed for %s: %s", provider_id, str(e))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.delete("/{provider_id}")
async def delete_provider(
    provider_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    result = await session.execute(
        select(AIProviderModel).where(
            AIProviderModel.id == provider_id,
            AIProviderModel.tenant_id == current_user["tenant_id"],
            AIProviderModel.is_deleted == False,
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    provider.is_deleted = True
    provider.is_active = False
    await session.commit()
    return {"message": "Provider deleted", "id": provider_id}
