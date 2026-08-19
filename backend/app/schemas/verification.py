from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class VerificationRunRequest(BaseModel):
    certificate_id: str | None = None
    deletion_request_id: str | None = None
    dataset_id: str | None = None


class ProofVerifyRequest(BaseModel):
    root: str = Field(description="Published Merkle root to verify against")
    leaf: str = Field(description="Leaf hash claimed to be in the tree")
    proof: list[dict[str, str]] = Field(
        default_factory=list,
        description="Sibling path: [{hash, side: left|right}]",
    )


class ProofIssueRequest(BaseModel):
    subject_id: str
    subject_type: str = "certificate"  # certificate|deletion_request|dataset
    claim: str = "deletion_occurred"
    pre_merkle_root: str
    post_merkle_root: str
    leaf_hashes: list[str] = Field(default_factory=list)


class CheckOut(BaseModel):
    passed: bool
    details: dict[str, Any]


class VerificationReportOut(BaseModel):
    id: str
    certificate_id: str
    deletion_request_id: str | None
    dataset_id: str | None
    model_id: str | None
    verdict: str
    checks_passed: int
    checks_total: int
    checks: dict[str, CheckOut]
    merkle_snapshot: dict[str, Any]
    duration_seconds: float | None
    created_by: str
    created_at: datetime | None = None


class ProofOut(BaseModel):
    proof_id: str
    subject_id: str
    subject_type: str
    claim: str
    pre_merkle_root: str
    post_merkle_root: str
    leaf_hashes: list[str]
    nonce: str
    timestamp: str
    content_hash: str
    signature: str
    scheme: str
    verification_status: str


class ProofVerifyOut(BaseModel):
    verified: bool
    reason: str
    hash_integrity: bool
    signature_valid: bool
    nonce_present: bool
    timestamp_valid: bool
