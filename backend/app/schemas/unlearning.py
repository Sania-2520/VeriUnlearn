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
