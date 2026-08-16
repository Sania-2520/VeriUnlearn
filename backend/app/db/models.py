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
    return datetime.now(timezone.utc)


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
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    feature_names: Mapped[list[str]] = mapped_column(JSON, default=list)
    label_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shard_count: Mapped[int] = mapped_column(Integer, default=4)
    status: Mapped[str] = mapped_column(String(32), default="ready")
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    records: Mapped[list["DatasetRecord"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", lazy="raise"
    )


class DatasetRecord(Base):
    __tablename__ = "dataset_records"
    __table_args__ = (
        Index("ix_records_identity", "identity_key"),
        Index("ix_records_shard", "dataset_id", "shard_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    record_index: Mapped[int] = mapped_column(Integer, nullable=False)
    shard_id: Mapped[int] = mapped_column(Integer, default=0)
    features: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    label: Mapped[Any] = mapped_column(JSON, nullable=True)
    # --- synthetic PII (AES-256-GCM encrypted at rest) ---
    identity_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    full_name_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitivity: Mapped[str] = mapped_column(String(32), default="personal")  # personal|sensitive|public
    # --- integrity ---
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    tombstone_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    influence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

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

    shards: Mapped[list["ModelShard"]] = relationship(
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
