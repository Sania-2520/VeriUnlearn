from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Optional structured search body for POST /privacy/search."""

    query: str | None = Field(default=None, description="Free-text query across identity fields")
    identity_key: str | None = None
    filters: dict[str, Any] | None = Field(
        default=None,
        description="Structured filters: name, email, phone, aadhaar, pan, passport, record_id, chat_id, customer_id, employee_id",
    )


class ScanRequest(BaseModel):
    dataset_id: str | None = None
    identity_key: str | None = None


class ScanResponse(BaseModel):
    report_id: str
    scanned_records: int
    findings_count: int
    risk_score: float
    counts_by_severity: dict[str, int]
    categories: dict[str, int]


class ExportRequest(BaseModel):
    query: str | None = None
    identity_key: str | None = None
    filters: dict[str, Any] | None = None
