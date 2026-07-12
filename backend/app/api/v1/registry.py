from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.dependencies import DatabaseDep, CurrentUser
from app.services.model_registry_service import ModelRegistryService

router = APIRouter(prefix="/registry", tags=["Model Registry"])


@router.get("/versions/{version_id}/lineage")
async def get_lineage(version_id: int, user: CurrentUser, db: DatabaseDep):
    service = ModelRegistryService(db)
    lineage = await service.get_model_lineage(version_id)
    if not lineage:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"lineage": lineage}


@router.get("/versions/{version_id}/children")
async def get_children(version_id: int, user: CurrentUser, db: DatabaseDep):
    service = ModelRegistryService(db)
    return {"children": await service.get_version_children(version_id)}


@router.get("/versions/compare/{v1_id}/{v2_id}")
async def compare_versions(v1_id: int, v2_id: int, user: CurrentUser, db: DatabaseDep):
    service = ModelRegistryService(db)
    return await service.compare_versions(v1_id, v2_id)


@router.get("/stats")
async def get_stats(user: CurrentUser, db: DatabaseDep):
    service = ModelRegistryService(db)
    return await service.get_version_stats()
