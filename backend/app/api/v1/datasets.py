from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession
from app.api.serializers import dataset_out
from app.core.config import settings
from app.core.exceptions import ValidationFailedError
from app.db.models import Dataset
from app.repositories.dataset_repo import DatasetRepository
from app.schemas.dataset import DatasetOut
from app.services.audit import AuditService
from app.services.ingestion import IngestionService

router = APIRouter(prefix="/datasets", tags=["datasets"])

MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_MB * 1024 * 1024


@router.post("/upload", response_model=DatasetOut, status_code=201)
async def upload_dataset(
    db: DbSession,
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
    shard_count: Annotated[int, Form()] = settings.DEFAULT_SHARD_COUNT,
) -> DatasetOut:
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValidationFailedError(f"File exceeds {settings.MAX_UPLOAD_MB}MB limit")
    service = IngestionService(db)
    dataset = await service.ingest_file(file.filename or "upload.csv", content, shard_count=shard_count)
    await AuditService(db).log(
        event_type="dataset.ingested",
        actor=user["sub"],
        subject=dataset.id,
        payload={"name": dataset.name, "records": dataset.record_count},
    )
    return DatasetOut(**dataset_out(dataset))


@router.post("/bootstrap/adult", response_model=DatasetOut, status_code=201)
async def bootstrap_adult(
    db: DbSession,
    user: CurrentUser,
    limit: Annotated[int | None, Query()] = 8000,
    shard_count: Annotated[int, Query()] = settings.DEFAULT_SHARD_COUNT,
) -> DatasetOut:
    service = IngestionService(db)
    dataset = await service.bootstrap_adult(limit=limit, shard_count=shard_count)
    await AuditService(db).log(
        event_type="dataset.ingested",
        actor=user["sub"],
        subject=dataset.id,
        payload={"name": dataset.name, "records": dataset.record_count, "source": "adult-bootstrap"},
    )
    return DatasetOut(**dataset_out(dataset))


@router.get("", response_model=list[DatasetOut])
async def list_datasets(db: DbSession, limit: int = 100) -> list[DatasetOut]:
    datasets = await DatasetRepository(db).list(limit=limit)
    return [DatasetOut(**dataset_out(d)) for d in datasets]


@router.get("/{dataset_id}", response_model=DatasetOut)
async def get_dataset(dataset_id: str, db: DbSession) -> DatasetOut:
    dataset = await DatasetRepository(db).get(dataset_id)
    return DatasetOut(**dataset_out(dataset))


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str, db: DbSession, user: CurrentUser) -> dict:
    repo = DatasetRepository(db)
    dataset = await repo.get(dataset_id)
    # Populate children explicitly (async-safe) so the cascade delete works.
    dataset.records = await repo.get_records(dataset_id, include_deleted=True)
    await repo.delete(dataset)
    await AuditService(db).log(
        event_type="dataset.deleted", actor=user["sub"], subject=dataset_id
    )
    return {"message": f"Dataset {dataset_id} deleted"}
