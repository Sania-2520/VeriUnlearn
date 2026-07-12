from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import DatabaseDep, CurrentUser
from app.schemas.training import (
    DatasetCreate,
    DatasetResponse,
    TrainingStartRequest,
    ModelVersionResponse,
    ModelVersionList,
)
from app.services.training_service import TrainingService
from app.worker.train_tasks import train_model_task

router = APIRouter(prefix="/training", tags=["Training"])


@router.post("/datasets", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(body: DatasetCreate, user: CurrentUser, db: DatabaseDep):
    service = TrainingService(db)
    dataset = await service.create_dataset(name=body.name, description=body.description)
    return DatasetResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        status=dataset.status,
        sample_count=0,
        created_at=dataset.created_at,
    )


@router.get("/datasets", response_model=list[DatasetResponse])
async def list_datasets(user: CurrentUser, db: DatabaseDep):
    service = TrainingService(db)
    datasets = await service.get_datasets()
    result = []
    for d in datasets:
        count = await service.get_sample_count(d.id)
        result.append(DatasetResponse(
            id=d.id,
            name=d.name,
            description=d.description,
            status=d.status,
            sample_count=count,
            created_at=d.created_at,
        ))
    return result


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: int, user: CurrentUser, db: DatabaseDep):
    service = TrainingService(db)
    dataset = await service.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    count = await service.get_sample_count(dataset.id)
    return DatasetResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        status=dataset.status,
        sample_count=count,
        created_at=dataset.created_at,
    )


@router.post("/start", response_model=dict)
async def start_training(body: TrainingStartRequest, user: CurrentUser, db: DatabaseDep):
    service = TrainingService(db)

    dataset = await service.get_dataset(body.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    service.write_dataset_json(body.dataset_id)

    sample_count = await service.get_sample_count(body.dataset_id)
    if sample_count == 0:
        raise HTTPException(status_code=400, detail="Dataset has no training samples")

    version = await service.create_model_version(
        dataset_id=body.dataset_id,
        adapter_path="pending",
        model_hash="pending",
        num_samples=sample_count,
    )

    task = train_model_task.delay(
        dataset_id=body.dataset_id,
        model_version_id=version.id,
        hyperparameters=body.hyperparameters,
    )
    return {"task_id": task.id, "model_version_id": version.id, "status": "started"}


@router.get("/versions", response_model=ModelVersionList)
async def list_versions(user: CurrentUser, db: DatabaseDep):
    service = TrainingService(db)
    versions = await service.get_model_versions()
    return ModelVersionList(
        versions=[ModelVersionResponse(
            id=v.id,
            base_model=v.base_model,
            hash=v.hash,
            status=v.status,
            num_samples=v.num_samples,
            train_loss=v.train_loss,
            eval_loss=v.eval_loss,
            metrics=v.metrics,
            created_at=v.created_at,
        ) for v in versions],
        total=len(versions),
    )


@router.get("/versions/{version_id}", response_model=ModelVersionResponse)
async def get_version(version_id: int, user: CurrentUser, db: DatabaseDep):
    service = TrainingService(db)
    version = await service.get_model_version(version_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found")
    return ModelVersionResponse(
        id=version.id,
        base_model=version.base_model,
        hash=version.hash,
        status=version.status,
        num_samples=version.num_samples,
        train_loss=version.train_loss,
        eval_loss=version.eval_loss,
        metrics=version.metrics,
        created_at=version.created_at,
    )


@router.post("/versions/{version_id}/activate", response_model=ModelVersionResponse)
async def activate_version(version_id: int, user: CurrentUser, db: DatabaseDep):
    service = TrainingService(db)
    version = await service.activate_model_version(version_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found")
    return ModelVersionResponse(
        id=version.id,
        base_model=version.base_model,
        hash=version.hash,
        status=version.status,
        num_samples=version.num_samples,
        train_loss=version.train_loss,
        eval_loss=version.eval_loss,
        metrics=version.metrics,
        created_at=version.created_at,
    )


@router.post("/datasets/{dataset_id}/build", response_model=dict)
async def build_dataset(dataset_id: int, user: CurrentUser, db: DatabaseDep):
    service = TrainingService(db)
    dataset = await service.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    count = await service.build_dataset_from_conversations(dataset_id)
    return {"dataset_id": dataset_id, "sample_count": count, "status": dataset.status}


@router.get("/tasks/{task_id}", response_model=dict)
async def get_task_status(task_id: str, user: CurrentUser, db: DatabaseDep):
    from celery.result import AsyncResult
    from app.worker.celery_app import celery_app
    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": result.state,
        "result": result.result if result.ready() else None,
    }
