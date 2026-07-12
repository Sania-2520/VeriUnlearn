from __future__ import annotations

from sqlalchemy import String, Text, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class TrainingDataset(Base, TimestampMixin):
    __tablename__ = "training_datasets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)

    samples = relationship("TrainingSample", back_populates="dataset", cascade="all, delete-orphan")
    model_versions = relationship("ModelVersion", back_populates="dataset")


class TrainingSample(Base, TimestampMixin):
    __tablename__ = "training_samples"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("training_datasets.id", ondelete="CASCADE"), nullable=True, index=True)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    shard_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    slice_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    dataset = relationship("TrainingDataset", back_populates="samples")
    user = relationship("User", back_populates="training_samples")


class ModelVersion(Base, TimestampMixin):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("training_datasets.id", ondelete="SET NULL"), nullable=True)
    base_model: Mapped[str] = mapped_column(String(256), nullable=False)
    adapter_path: Mapped[str] = mapped_column(String(512), nullable=False)
    hash: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="training", nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    num_samples: Mapped[int] = mapped_column(Integer, default=0)
    train_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_loss: Mapped[float | None] = mapped_column(Float, nullable=True)

    dataset = relationship("TrainingDataset", back_populates="model_versions")
    shards = relationship("ModelShard", back_populates="model_version", cascade="all, delete-orphan")
    parent = relationship("ModelVersion", remote_side=[id], backref="children")


class ModelShard(Base, TimestampMixin):
    __tablename__ = "model_shards"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    model_version_id: Mapped[int] = mapped_column(ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    shard_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    adapter_path: Mapped[str] = mapped_column(String(512), nullable=False)
    hash: Mapped[str] = mapped_column(String(128), nullable=False)
    num_samples: Mapped[int] = mapped_column(Integer, default=0)

    model_version = relationship("ModelVersion", back_populates="shards")
