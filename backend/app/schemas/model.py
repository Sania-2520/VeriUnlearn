from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ModelOut(BaseModel):
    id: str
    name: str
    model_type: str
    dataset_id: str
    shard_count: int
    version: int
    status: str
    weights_hash: str | None
    metrics: dict[str, Any]
    aggregation: str
    is_active: bool
    created_at: str | None = None


class PredictRequest(BaseModel):
    features: dict[str, Any] = Field(..., description="Feature values keyed by feature name")


class PredictResponse(BaseModel):
    model_id: str
    model_version: int
    prediction: int | str
    probability: float
    shard_count: int
