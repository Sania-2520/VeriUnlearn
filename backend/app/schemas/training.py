from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = None


class DatasetResponse(BaseModel):
    id: int
    name: str
    description: str | None
    status: str
    sample_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainingStartRequest(BaseModel):
    dataset_id: int
    model_version_id: int | None = None
    hyperparameters: dict | None = None


class TrainingStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    current_epoch: int
    total_epochs: int
    current_loss: float | None


class ModelVersionResponse(BaseModel):
    id: int
    base_model: str
    hash: str
    status: str
    num_samples: int
    train_loss: float | None
    eval_loss: float | None
    metrics: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelVersionList(BaseModel):
    versions: list[ModelVersionResponse]
    total: int
