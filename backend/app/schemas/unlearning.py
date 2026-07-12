from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UnlearningRequestCreate(BaseModel):
    sample_ids: list[int] = Field(..., min_length=1)
    algorithm: str | None = None
    reason: str | None = None


class UnlearningBenchmarkRequest(BaseModel):
    dataset_size: int = Field(..., ge=1)
    num_deleted: int = Field(..., ge=1)
    sensitivity: str = "medium"
    latency_budget: float = Field(300.0, gt=0)


class AlgorithmBenchmark(BaseModel):
    name: str
    recommended: bool
    estimated_cost: float
    estimated_latency: float
    guarantees: str
    privacy_score: float
    utility_retention: float
    implementation_status: str
    budget_fit: bool
    mia_before: float
    mia_after: float
    mia_reduction: float


class UnlearningBenchmarkResponse(BaseModel):
    recommended: str
    dataset_size: int
    num_deleted: int
    deletion_ratio: float
    sensitivity: str
    latency_budget: float
    algorithms: list[AlgorithmBenchmark]


class UnlearningRequestResponse(BaseModel):
    id: int
    user_id: int
    status: str
    algorithm: str
    reason: str | None
    progress: float
    error_message: str | None
    created_at: datetime
    completed_at: str | None

    model_config = {"from_attributes": True}


class UnlearningResultResponse(BaseModel):
    id: int
    request_id: int
    model_version_before_id: int | None
    model_version_after_id: int | None
    algorithm: str | None
    execution_mode: str | None
    guarantees: str | None
    simulated: bool
    privacy_score: float | None
    estimated_cost: float | None
    estimated_latency: float | None
    mia_before_accuracy: float | None
    mia_before_precision: float | None
    mia_before_recall: float | None
    mia_after_accuracy: float | None
    mia_after_precision: float | None
    mia_after_recall: float | None
    utility_accuracy: float | None
    utility_precision: float | None
    utility_recall: float | None
    utility_f1: float | None
    utility_loss: float | None
    utility_retention: float | None
    weight_distance: float | None
    gradient_distance: float | None
    cosine_similarity: float | None
    influence_score: float | None
    merkle_root: str | None
    signature: str | None
    certificate_path: str | None
    deletion_latency_ms: float | None
    privacy_leakage: float | None
    attack_success_rate_delta: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProofVerificationResponse(BaseModel):
    result_id: int
    request_id: int
    verified: bool
    merkle_valid: bool
    signature_valid: bool
    certificate_valid: bool
    certificate_hash_valid: bool
    certificate_signature_valid: bool
    public_key: str
    errors: list[str]
