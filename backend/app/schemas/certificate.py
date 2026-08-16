from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CertificateOut(BaseModel):
    id: str
    subject_user_id: str
    deletion_type: str
    deleted_record_count: int
    dataset_id: str | None
    model_id: str | None
    model_version: int
    shard_ids: list[int]
    pre_merkle_root: str
    post_merkle_root: str
    method: str
    certified_bound: float | None
    timestamp: str
    content_hash: str
    signature: str
    verification_status: str
    blockchain_tx: str | None
    zk_proof: dict[str, Any]
    created_at: datetime | None = None


class VerificationOut(BaseModel):
    certificate_id: str
    verified: bool
    hash_integrity: bool
    signature_valid: bool
    post_root_matches_current_state: bool
    recomputed_post_root: str
    deleted_records_still_tombstoned: list[str]
    audit_chain_verified: bool
