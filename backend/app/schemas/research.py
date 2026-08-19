from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BenchmarkRunRequest(BaseModel):
    dataset_id: str
    n_delete: int = Field(default=50, ge=1, le=1000)
    eval_size: int = Field(default=300, ge=20, le=2000)
    seed: int = 42
    experiment_id: str | None = None
    method: str | None = Field(
        default=None, description="Restrict to a single method for faster iteration"
    )


class MIARequest(BaseModel):
    model_id: str
    deleted_record_ids: list[str] | None = None
    sample_size: int = Field(default=300, ge=10, le=5000)
    experiment_id: str | None = None


class InversionRequest(BaseModel):
    model_id: str
    target_label: int = 1
    steps: int = Field(default=200, ge=10, le=2000)
    lr: float = Field(default=0.1, gt=0)
    deleted_record_ids: list[str] | None = None
    experiment_id: str | None = None


class ExtractionRequest(BaseModel):
    model_id: str
    deleted_record_ids: list[str]
    experiment_id: str | None = None


class PoisoningRequest(BaseModel):
    model_id: str
    poison_fraction: float = Field(default=0.1, gt=0, le=0.5)
    trigger_value: float = -1.0
    attack_type: str = Field(default="backdoor", description="backdoor|label_flip|gradient")
    experiment_id: str | None = None


class ExperimentCreateRequest(BaseModel):
    name: str
    description: str | None = None
    seed: int = 42
    parameters: dict[str, Any] = Field(default_factory=dict)
    dataset_id: str | None = None
    model_id: str | None = None


class ExperimentVersionRequest(BaseModel):
    name: str | None = None
    parameters: dict[str, Any] | None = None


class ExperimentCompareRequest(BaseModel):
    experiment_ids: list[str] = Field(min_length=2)


class MetricsQuery(BaseModel):
    experiment_id: str | None = None
