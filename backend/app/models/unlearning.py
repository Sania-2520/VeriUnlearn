from __future__ import annotations

from sqlalchemy import String, Text, Integer, Float, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class UnlearningRequest(Base, TimestampMixin):
    __tablename__ = "unlearning_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    algorithm: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String(64), nullable=True)

    samples = relationship("UnlearningSample", back_populates="request", cascade="all, delete-orphan")
    result = relationship("UnlearningResult", back_populates="request", uselist=False, cascade="all, delete-orphan")


class UnlearningSample(Base, TimestampMixin):
    __tablename__ = "unlearning_samples"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("unlearning_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    training_sample_id: Mapped[int] = mapped_column(ForeignKey("training_samples.id", ondelete="CASCADE"), nullable=False)

    request = relationship("UnlearningRequest", back_populates="samples")


class UnlearningResult(Base, TimestampMixin):
    __tablename__ = "unlearning_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("unlearning_requests.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    model_version_before_id: Mapped[int] = mapped_column(ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True)
    model_version_after_id: Mapped[int] = mapped_column(ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True)

    algorithm: Mapped[str | None] = mapped_column(String(64), nullable=True)
    execution_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    guarantees: Mapped[str | None] = mapped_column(String(64), nullable=True)
    simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    privacy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_latency: Mapped[float | None] = mapped_column(Float, nullable=True)

    mia_before_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    mia_before_precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    mia_before_recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    mia_before_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    mia_after_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    mia_after_precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    mia_after_recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    mia_after_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    utility_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    utility_precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    utility_recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    utility_f1: Mapped[float | None] = mapped_column(Float, nullable=True)
    utility_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    utility_retention: Mapped[float | None] = mapped_column(Float, nullable=True)

    weight_distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    gradient_distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    cosine_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    influence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    merkle_root: Mapped[str | None] = mapped_column(String(128), nullable=True)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    certificate_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    certificate_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    deletion_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    privacy_leakage: Mapped[float | None] = mapped_column(Float, nullable=True)
    attack_success_rate_delta: Mapped[float | None] = mapped_column(Float, nullable=True)

    request = relationship("UnlearningRequest", back_populates="result")


class AuditLedger(Base, TimestampMixin):
    __tablename__ = "audit_ledger"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
