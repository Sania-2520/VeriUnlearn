"""ORM models.

Domain entities:
- users            : platform users with RBAC roles
- datasets         : ingested data sources (Adult Census, CSV uploads, ...)
- dataset_records  : individual rows; the unit of unlearning
- ml_models        : deployed model versions (SISA ensembles)
- model_shards     : per-shard models owned by an :class:`MLModel`
- deletion_requests: GDPR/DPDP erasure requests
- certificates     : signed deletion certificates (Merkle roots, hashes, sig)
- audit_events     : append-only hash-chained audit trail
- blockchain_ledger: local mirror of on-chain certificate registrations
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    # Naive UTC (PostgreSQL ``TIMESTAMP WITHOUT TIME ZONE`` columns).
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="operator")  # admin|operator|auditor
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ---------------------------------------------------------------------------
# Datasets & records
# ---------------------------------------------------------------------------


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), default="csv")
    version: Mapped[int] = mapped_column(Integer, default=1)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    feature_names: Mapped[list[str]] = mapped_column(JSON, default=list)
    label_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shard_count: Mapped[int] = mapped_column(Integer, default=4)
    status: Mapped[str] = mapped_column(String(32), default="ready")
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    records: Mapped[list[DatasetRecord]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", lazy="raise"
    )


class DatasetRecord(Base):
    __tablename__ = "dataset_records"
    __table_args__ = (
        Index("ix_records_identity", "identity_key"),
        Index("ix_records_shard", "dataset_id", "shard_id"),
        Index("ix_records_chat", "chat_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    record_index: Mapped[int] = mapped_column(Integer, nullable=False)
    shard_id: Mapped[int] = mapped_column(Integer, default=0)
    features: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    label: Mapped[Any] = mapped_column(JSON, nullable=True)
    # --- synthetic/derived PII (AES-256-GCM encrypted at rest) ---
    identity_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    full_name_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    aadhaar_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    pan_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    passport_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    dob_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitivity: Mapped[str] = mapped_column(String(32), default="personal")  # personal|sensitive|public
    # --- source / chunking (Phase 3 record viewer) ---
    chat_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    chunk_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # --- integrity ---
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    tombstone_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    influence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    vector_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    dataset: Mapped[Dataset] = relationship(back_populates="records")


# ---------------------------------------------------------------------------
# Models & shards
# ---------------------------------------------------------------------------


class MLModel(Base):
    __tablename__ = "ml_models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_type: Mapped[str] = mapped_column(String(32), default="linear")  # linear|llm_lora
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    shard_count: Mapped[int] = mapped_column(Integer, default=4)
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="created")  # created|training|ready|unlearning|failed
    weights_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    aggregation: Mapped[str] = mapped_column(String(32), default="soft_voting")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    adapters: Mapped[list[str]] = mapped_column(JSON, default=list)

    shards: Mapped[list[ModelShard]] = relationship(
        back_populates="model", cascade="all, delete-orphan", lazy="raise"
    )


class ModelShard(Base):
    __tablename__ = "model_shards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(
        ForeignKey("ml_models.id", ondelete="CASCADE"), index=True, nullable=False
    )
    shard_index: Mapped[int] = mapped_column(Integer, nullable=False)
    weights_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    weights_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    train_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    retrained_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    record_version: Mapped[int] = mapped_column(Integer, default=0)
    trained_on: Mapped[int] = mapped_column(Integer, default=0)

    model: Mapped[MLModel] = relationship(back_populates="shards")


# ---------------------------------------------------------------------------
# Deletion requests
# ---------------------------------------------------------------------------


class DeletionRequest(Base):
    __tablename__ = "deletion_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    identity_key: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    subject_label: Mapped[str] = mapped_column(String(255), nullable=False)
    deletion_type: Mapped[str] = mapped_column(String(64), nullable=False)
    method: Mapped[str] = mapped_column(String(32), default="retrain")  # retrain|influence|certified
    scope: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    record_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    shard_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|in_progress|completed|rejected|failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[str] = mapped_column(String(36), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    certificate_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


# ---------------------------------------------------------------------------
# Certificates
# ---------------------------------------------------------------------------


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    deletion_request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    subject_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    deletion_type: Mapped[str] = mapped_column(String(64), nullable=False)
    deleted_record_count: Mapped[int] = mapped_column(Integer, default=0)
    dataset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    model_version: Mapped[int] = mapped_column(Integer, default=0)
    shard_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    pre_merkle_root: Mapped[str] = mapped_column(String(64), nullable=False)
    post_merkle_root: Mapped[str] = mapped_column(String(64), nullable=False)
    deleted_record_hashes: Mapped[list[str]] = mapped_column(JSON, default=list)
    method: Mapped[str] = mapped_column(String(32), default="retrain")
    certified_bound: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|valid|invalid
    certificate_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    zk_proof: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    blockchain_tx: Mapped[str | None] = mapped_column(String(128), nullable=True)


# ---------------------------------------------------------------------------
# Audit trail (hash chain)
# ---------------------------------------------------------------------------


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    certificate_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# Blockchain ledger (local mirror of on-chain registrations)
# ---------------------------------------------------------------------------


class BlockchainLedger(Base):
    __tablename__ = "blockchain_ledger"
    __table_args__ = (UniqueConstraint("certificate_id", name="uq_ledger_cert"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    certificate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    cert_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    chain: Mapped[str] = mapped_column(String(64), default="local")
    tx_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="recorded")
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# Phase 3 — Privacy Auditor
# ---------------------------------------------------------------------------


class PrivacyReport(Base):
    """Result of a full-dataset privacy scan.

    ``findings`` is a list of per-record detection summaries
    (record_id, category, severity, snippet, confidence) plus a dataset-level
    aggregate (counts by category/severity, risk score).
    """

    __tablename__ = "privacy_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dataset_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    scope: Mapped[str] = mapped_column(String(32), default="all")  # all | dataset | identity
    subject: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scanned_records: Mapped[int] = mapped_column(Integer, default=0)
    findings_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    high_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, default=0)
    low_count: Mapped[int] = mapped_column(Integer, default=0)
    categories: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)


class IdentityIndex(Base):
    """Denormalised searchable identity profile (Phase 3 identity search)."""

    __tablename__ = "identity_index"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    identity_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    aadhaar: Mapped[str] = mapped_column(String(64), default="")
    pan: Mapped[str] = mapped_column(String(64), default="")
    passport: Mapped[str] = mapped_column(String(64), default="")
    customer_id: Mapped[str] = mapped_column(String(64), default="")
    employee_id: Mapped[str] = mapped_column(String(64), default="")
    dob: Mapped[str] = mapped_column(String(32), default="")
    address: Mapped[str] = mapped_column(String(512), default="")
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    dataset_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class EmbeddingIndex(Base):
    """Tracks embeddings / vectors / chunks per record (Phase 3/4 impact)."""

    __tablename__ = "embedding_index"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    record_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    dataset_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    embedding_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    vector_id: Mapped[str] = mapped_column(String(128), nullable=False)
    chunk_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    dim: Mapped[int] = mapped_column(Integer, default=0)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class SearchHistory(Base):
    """Persisted identity searches (Phase 3 search-history page)."""

    __tablename__ = "search_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    query: Mapped[str] = mapped_column(String(255), default="")
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class DeletionHistory(Base):
    """Deletion reports (Phase 4 STEP 7): before/after snapshot per request."""

    __tablename__ = "deletion_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="records")
    subject: Mapped[str] = mapped_column(String(255), default="")
    method: Mapped[str] = mapped_column(String(32), default="retrain")
    status: Mapped[str] = mapped_column(String(32), default="completed")
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    shard_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    model_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dataset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    dataset_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_before: Mapped[int] = mapped_column(Integer, default=0)
    records_after: Mapped[int] = mapped_column(Integer, default=0)
    embeddings_before: Mapped[int] = mapped_column(Integer, default=0)
    embeddings_after: Mapped[int] = mapped_column(Integer, default=0)
    vectors_removed: Mapped[int] = mapped_column(Integer, default=0)
    certified_bound: Mapped[float | None] = mapped_column(Float, nullable=True)
    certificate_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    before: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    after: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# Phase 5 — Verifiable Machine Unlearning
# ---------------------------------------------------------------------------


class VerificationReport(Base):
    """Result of a full deletion-verification job (Phase 5).

    ``checks`` maps check name → ``{passed, details}``; ``merkle_snapshot`` is
    the serialised Merkle tree at verification time for visualisation.
    """

    __tablename__ = "verification_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    certificate_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    deletion_request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    dataset_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    verdict: Mapped[str] = mapped_column(String(32), default="pending")  # pending|valid|invalid
    checks_passed: Mapped[int] = mapped_column(Integer, default=0)
    checks_total: Mapped[int] = mapped_column(Integer, default=0)
    checks: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    merkle_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class CryptoProof(Base):
    """Immutable cryptographic proof object (Phase 5 proof generator).

    Persisted copy of the signed proof: body fields + nonce + timestamp +
    content hash + RSA signature. ``verification_status`` mirrors the last
    ``ProofService.verify`` result.
    """

    __tablename__ = "crypto_proofs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    proof_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)  # certificate|deletion_request|dataset
    claim: Mapped[str] = mapped_column(String(255), nullable=False)
    pre_merkle_root: Mapped[str] = mapped_column(String(64), nullable=False)
    post_merkle_root: Mapped[str] = mapped_column(String(64), nullable=False)
    leaf_hashes: Mapped[list[str]] = mapped_column(JSON, default=list)
    nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    scheme: Mapped[str] = mapped_column(String(32), default="rsa-pkcs1v15-sha256")
    verification_status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# Phase 6 — Security Evaluation, Benchmarking & Research Suite
# ---------------------------------------------------------------------------


class Experiment(Base):
    """A versioned research experiment (Phase 6).

    Captures parameters, dataset/model versions, environment (platform, seed,
    dependency versions) and a human-readable description so every run is
    reproducible. ``history`` holds prior versions of the experiment config.
    """

    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    seed: Mapped[int] = mapped_column(Integer, default=42)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    environment: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    dataset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|running|completed|failed
    result_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(String(36), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class ExperimentHistory(Base):
    """Append-only version log of experiment configs (Phase 6)."""

    __tablename__ = "experiment_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class BenchmarkResult(Base):
    """One persisted benchmark row: a method's metrics on a dataset (Phase 6).

    ``metrics`` holds utility (accuracy/precision/recall/F1), cost (deletion /
    training seconds), resource usage (GPU/RAM MB, inference latency) and
    privacy/security scores (leakage, forgetting, recovery, attack success).
    """

    __tablename__ = "benchmark_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    dataset_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    model_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    method: Mapped[str] = mapped_column(String(64), nullable=False)  # original|full_retrain|sisa|influence|certified|veriunlearn
    deleted_records: Mapped[int] = mapped_column(Integer, default=0)
    eval_records: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AttackResult(Base):
    """Persisted privacy-attack outcome (Phase 6)."""

    __tablename__ = "attack_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    model_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    attack_type: Mapped[str] = mapped_column(String(32), nullable=False)  # mia|inversion|extraction|poisoning
    stage: Mapped[str] = mapped_column(String(32), default="pre_unlearning")  # pre_unlearning|post_unlearning|post_verification
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class PerformanceMetric(Base):
    """Resource/profile sample (Phase 6): CPU, RAM, disk, timings, latency."""

    __tablename__ = "performance_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    kind: Mapped[str] = mapped_column(String(32), default="system")  # system|benchmark
    metric: Mapped[str] = mapped_column(String(64), default="cpu_percent")
    value: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(32), default="")
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    sampled_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class PrivacyScore(Base):
    """Research metrics calculation result (Phase 6).

    Forget Quality Score, Privacy Gain, Knowledge Retention, Accuracy Drop,
    Utility Loss, Deletion Efficiency, Verification Overhead, Compliance
    Readiness — computed from benchmark + attack + operational data.
    """

    __tablename__ = "privacy_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    experiment_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    method: Mapped[str] = mapped_column(String(64), default="")
    scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# Phase 7 — Enterprise platform (RBAC, API keys, notifications, monitoring)
# ---------------------------------------------------------------------------


class Role(Base):
    """A platform role (RBAC). Roles map to permissions via the in-code
    permission matrix (``app/core/rbac.py``); this table persists the matrix
    for admin visibility and audit."""

    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)


class Permission(Base):
    """A permission string (e.g. ``unlearning:execute``) with a human label."""

    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(32), default="general")


class APIKey(Base):
    """Programmatic access key (Phase 7 API management).

    Only the SHA-256 hash of the key is stored; the plaintext is shown once at
    issuance. ``quota_per_minute`` is enforced with a sliding window stored on
    the row (``window_start`` / ``window_count``). ``usage`` keeps a bounded
    rolling log of recent requests for the developer portal.
    """

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)  # e.g. ["datasets:read"]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    quota_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    window_start: Mapped[datetime] = mapped_column(DateTime, default=_now)
    window_count: Mapped[int] = mapped_column(Integer, default=0)
    requests_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    usage: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Notification(Base):
    """In-app notification with provider-abstracted delivery (email).

    ``channel`` is ``in_app`` or ``email``; email deliveries that fail are
    retried with ``attempts`` / ``next_attempt_at`` until ``delivered``.
    """

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)  # deletion.completed|verification.completed|certificate.ready|experiment.finished|system.error
    channel: Mapped[str] = mapped_column(String(16), default="in_app")  # in_app|email
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class SystemMetric(Base):
    """Monitoring snapshot (Phase 7): CPU/RAM/disk, dependency health, queue
    lengths, API latency/error rate, uptime seconds."""

    __tablename__ = "system_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(32), default="system")  # system|dependency|queue|api
    name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    value: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(32), default="")
    healthy: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    sampled_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)


class ComplianceReport(Base):
    """A persisted GDPR/DPDP compliance snapshot (Phase 7 dashboards).

    ``scores`` mirrors the compliance overview payload at capture time so the
    compliance history can be trended and exported.
    """

    __tablename__ = "compliance_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    gdpr_score: Mapped[float] = mapped_column(Float, default=0.0)
    gdpr_status: Mapped[str] = mapped_column(String(32), default="review")
    dpdp_score: Mapped[float] = mapped_column(Float, default=0.0)
    dpdp_status: Mapped[str] = mapped_column(String(32), default="review")
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(16), default="low")
    open_requests: Mapped[int] = mapped_column(Integer, default=0)
    completed_requests: Mapped[int] = mapped_column(Integer, default=0)
    certs_valid: Mapped[int] = mapped_column(Integer, default=0)
    scores: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(36), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)


class DeploymentLog(Base):
    """Deployment/release event (Phase 7 CI/CD): version, environment, status."""

    __tablename__ = "deployment_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), default="staging")
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|success|failed
    commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artifact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deployed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    log: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AnalyticsCache(Base):
    """Cached analytics computation (Phase 7): keyed result with freshness."""

    __tablename__ = "analytics_cache"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    cache_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
