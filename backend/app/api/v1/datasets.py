from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile
from sqlalchemy import delete, select

from app.api.deps import CurrentUser, DbSession
from app.api.serializers import dataset_out
from app.core.config import settings
from app.core.exceptions import ValidationFailedError
from app.db.models import DatasetRecord, EmbeddingIndex, IdentityIndex, MLModel, ModelShard
from app.repositories.dataset_repo import DatasetRepository
from app.schemas.dataset import DatasetOut
from app.services.audit import AuditService
from app.services.embeddings import get_vector_store
from app.services.ingestion import IngestionService

router = APIRouter(prefix="/datasets", tags=["datasets"])

MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_MB * 1024 * 1024
MAX_SHARD_COUNT = 64


@router.post("/upload", response_model=DatasetOut, status_code=201)
async def upload_dataset(
    db: DbSession,
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
    shard_count: Annotated[int, Form()] = settings.DEFAULT_SHARD_COUNT,
) -> DatasetOut:
    if shard_count < 1 or shard_count > MAX_SHARD_COUNT:
        raise ValidationFailedError(f"shard_count must be between 1 and {MAX_SHARD_COUNT}")
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
async def list_datasets(db: DbSession, user: CurrentUser, limit: int = 100) -> list[DatasetOut]:
    datasets = await DatasetRepository(db).list(limit=limit)
    return [DatasetOut(**dataset_out(d)) for d in datasets]


@router.get("/{dataset_id}", response_model=DatasetOut)
async def get_dataset(dataset_id: str, db: DbSession, user: CurrentUser) -> DatasetOut:
    dataset = await DatasetRepository(db).get(dataset_id)
    return DatasetOut(**dataset_out(dataset))


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str, db: DbSession, user: CurrentUser) -> dict:
    """Delete a dataset and everything derived from it.

    Performs explicit cleanup so no orphan rows or vectors survive:
    vectors (Qdrant collection / memory bucket), embedding-index rows,
    identity profiles (dataset id removed, empty profiles dropped), trained
    models + shards (SQLite has no FK cascade), records and the dataset row.
    """
    repo = DatasetRepository(db)
    dataset = await repo.get(dataset_id)

    # 1. Vector store: drop the dataset collection entirely.
    get_vector_store().drop_collection(f"dataset_{dataset_id}")

    # 2. Chunk/embedding index rows.
    await db.execute(delete(EmbeddingIndex).where(EmbeddingIndex.dataset_id == dataset_id))

    # 3. Identity profiles: detach this dataset; drop profiles left empty.
    profiles = (await db.execute(select(IdentityIndex))).scalars().all()
    for profile in profiles:
        if dataset_id in (profile.dataset_ids or []):
            remaining = [d for d in profile.dataset_ids if d != dataset_id]
            if remaining:
                profile.dataset_ids = remaining
            else:
                await db.delete(profile)

    # 4. Trained models + shards (explicit delete works on every backend).
    await db.execute(
        delete(ModelShard).where(
            ModelShard.model_id.in_(select(MLModel.id).where(MLModel.dataset_id == dataset_id))
        )
    )
    await db.execute(delete(MLModel).where(MLModel.dataset_id == dataset_id))

    # 5. Records + dataset row.
    await db.execute(delete(DatasetRecord).where(DatasetRecord.dataset_id == dataset_id))
    await repo.delete(dataset)

    await AuditService(db).log(
        event_type="dataset.deleted", actor=user["sub"], subject=dataset_id
    )
    return {"message": f"Dataset {dataset_id} deleted"}
