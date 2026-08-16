from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class DatasetOut(BaseModel):
    id: str
    name: str
    description: str | None
    source_type: str
    record_count: int
    feature_names: list[str]
    label_column: str | None
    shard_count: int
    status: str
    meta: dict[str, Any]
    created_at: str | None = None


class DatasetSummary(BaseModel):
    id: str
    name: str
    record_count: int
    shard_count: int
    status: str
