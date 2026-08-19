from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SelectiveDeletionRequest(BaseModel):
    identity_key: str | None = Field(default=None, description="Identity to scrub (all matching records)")
    record_ids: list[str] | None = Field(default=None, description="Explicit record ids (surgical deletion)")
    deletion_type: str = Field(
        default="records",
        description="record|message|file|embedding|chat|identity_field|adapter|neuron_cluster|identity_reset",
    )
    method: str = Field(
        default="retrain",
        description="retrain (SISA) | certified (Newton-step) | influence (gradient scrub)",
    )
    scope: str = Field(
        default="records",
        description="Phase 4 selection scope: records | chat | dataset",
    )
    chat_id: str | None = Field(default=None, description="Entire conversation (scope=chat)")
    dataset_id: str | None = Field(default=None, description="Entire dataset (scope=dataset)")


class ImpactRequest(BaseModel):
    identity_key: str | None = None
    record_ids: list[str] | None = None
    chat_id: str | None = None
    dataset_id: str | None = None
    scope: str = "records"


class IdentityResetRequest(BaseModel):
    identity_key: str = Field(description="Complete identity reset for this identity")


class DeletionRequestCreate(BaseModel):
    identity_key: str | None = None
    record_ids: list[str] | None = None
    deletion_type: str = "records"
    method: str = "retrain"


class DeletionRequestOut(BaseModel):
    id: str
    identity_key: str | None
    subject_label: str
    deletion_type: str
    method: str
    status: str
    error: str | None
    record_ids: list[str]
    shard_ids: list[int]
    requested_by: str
    requested_at: datetime
    completed_at: datetime | None
    duration_seconds: float | None
    result: dict[str, Any]
    certificate_id: str | None


class DeletionHistoryOut(BaseModel):
    id: str
    request_id: str
    scope: str
    subject: str
    method: str
    status: str
    record_count: int
    shard_ids: list[int]
    duration_seconds: float | None
    model_id: str | None
    model_version: int | None
    dataset_id: str | None
    dataset_version: int | None
    records_before: int
    records_after: int
    embeddings_before: int
    embeddings_after: int
    vectors_removed: int
    certified_bound: float | None
    certificate_id: str | None
    before: dict[str, Any]
    after: dict[str, Any]
    created_at: datetime | None = None
