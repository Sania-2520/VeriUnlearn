from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import CurrentUser, DatabaseSession, default_rate_limiter, require_permission
from app.core.logging import get_logger
from app.core.rbac import Permission
from app.infrastructure.database.models import DatasetRegistryModel

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(default_rate_limiter)])


class CreateDatasetRequest(BaseModel):
    name: str
    description: Optional[str] = None
    dataset_type: str = "synthetic"
    source: Optional[str] = None
    version: str = "1.0"
    num_samples: int = 0
    num_features: int = 0
    num_classes: int = 2
    feature_names: Optional[list[str]] = None
    class_names: Optional[list[str]] = None
    tags: list[str] = []
    metadata: dict = {}
    storage_path: Optional[str] = None
    checksum: Optional[str] = None


class UpdateDatasetRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    num_samples: Optional[int] = None
    num_features: Optional[int] = None
    num_classes: Optional[int] = None
    feature_names: Optional[list[str]] = None
    class_names: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict] = None
    storage_path: Optional[str] = None
    checksum: Optional[str] = None
    is_active: Optional[bool] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def register_dataset(
    request: CreateDatasetRequest,
    _: None = Depends(require_permission(Permission.TRAINING_WRITE)),
    current_user: CurrentUser = ...,
    session: DatabaseSession = ...,
):
    from sqlalchemy import select, func

    now = datetime.now(timezone.utc)
    dataset = DatasetRegistryModel(
        id=str(uuid4()),
        tenant_id=current_user["tenant_id"],
        name=request.name,
        description=request.description,
        dataset_type=request.dataset_type,
        source=request.source,
        version=request.version,
        num_samples=request.num_samples,
        num_features=request.num_features,
        num_classes=request.num_classes,
        feature_names=request.feature_names,
        class_names=request.class_names,
        tags=request.tags,
        dataset_metadata=request.metadata,
        storage_path=request.storage_path,
        checksum=request.checksum,
        created_by=current_user["user_id"],
        created_at=now,
        updated_at=now,
    )
    session.add(dataset)
    await session.commit()
    await session.refresh(dataset)
    return {
        "id": dataset.id,
        "name": dataset.name,
        "dataset_type": dataset.dataset_type,
        "version": dataset.version,
        "created_at": dataset.created_at.isoformat(),
    }


@router.get("")
async def list_datasets(
    current_user: CurrentUser,
    session: DatabaseSession,
    dataset_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    _: None = Depends(require_permission(Permission.BENCHMARKS_READ)),
):
    from sqlalchemy import select, desc, func

    query = select(DatasetRegistryModel).where(
        DatasetRegistryModel.tenant_id == current_user["tenant_id"],
        DatasetRegistryModel.is_active == True,
    )
    count_query = select(func.count(DatasetRegistryModel.id)).where(
        DatasetRegistryModel.tenant_id == current_user["tenant_id"],
        DatasetRegistryModel.is_active == True,
    )
    if dataset_type:
        query = query.where(DatasetRegistryModel.dataset_type == dataset_type)
        count_query = count_query.where(DatasetRegistryModel.dataset_type == dataset_type)
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    query = query.order_by(desc(DatasetRegistryModel.created_at)).offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    datasets = result.scalars().all()
    return {"data": [
        {
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "dataset_type": d.dataset_type,
            "source": d.source,
            "version": d.version,
            "num_samples": d.num_samples,
            "num_features": d.num_features,
            "num_classes": d.num_classes,
            "feature_names": d.feature_names,
            "class_names": d.class_names,
            "tags": d.tags,
            "storage_path": d.storage_path,
            "checksum": d.checksum,
            "is_active": d.is_active,
            "created_by": d.created_by,
            "created_at": d.created_at.isoformat(),
            "updated_at": d.updated_at.isoformat(),
        }
        for d in datasets
    ], "meta": {"page": page, "page_size": page_size, "total": total}}


@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    from sqlalchemy import select

    query = select(DatasetRegistryModel).where(
        DatasetRegistryModel.id == dataset_id,
        DatasetRegistryModel.tenant_id == current_user["tenant_id"],
    )
    result = await session.execute(query)
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "dataset_type": dataset.dataset_type,
        "source": dataset.source,
        "version": dataset.version,
        "num_samples": dataset.num_samples,
        "num_features": dataset.num_features,
        "num_classes": dataset.num_classes,
        "feature_names": dataset.feature_names,
        "class_names": dataset.class_names,
        "tags": dataset.tags,
        "metadata": dataset.dataset_metadata,
        "storage_path": dataset.storage_path,
        "checksum": dataset.checksum,
        "is_active": dataset.is_active,
        "created_by": dataset.created_by,
        "created_at": dataset.created_at.isoformat(),
        "updated_at": dataset.updated_at.isoformat(),
    }


@router.put("/{dataset_id}")
async def update_dataset(
    dataset_id: str,
    request: UpdateDatasetRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    from sqlalchemy import select

    query = select(DatasetRegistryModel).where(
        DatasetRegistryModel.id == dataset_id,
        DatasetRegistryModel.tenant_id == current_user["tenant_id"],
    )
    result = await session.execute(query)
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dataset, field, value)
    dataset.updated_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(dataset)
    return {"status": "updated", "id": dataset.id}


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    current_user: CurrentUser,
    session: DatabaseSession,
):
    from sqlalchemy import select

    query = select(DatasetRegistryModel).where(
        DatasetRegistryModel.id == dataset_id,
        DatasetRegistryModel.tenant_id == current_user["tenant_id"],
    )
    result = await session.execute(query)
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    dataset.is_active = False
    dataset.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return {"status": "deactivated", "id": dataset_id}
