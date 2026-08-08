"""Add experiment and dataset registry tables

Revision ID: 003
Revises: 002
Create Date: 2026-07-13 18:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("experiment_type", sa.String(50), nullable=False, server_default="benchmark"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("metrics", postgresql.JSONB, nullable=True),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("dataset_ids", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("model_version_ids", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("algorithm", sa.String(50), nullable=True),
        sa.Column("num_trials", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_experiments_tenant", "experiments", ["tenant_id", "status"])
    op.create_index("idx_experiments_type", "experiments", ["tenant_id", "experiment_type"])

    op.create_table(
        "experiment_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("experiment_id", sa.String(36), nullable=False, index=True),
        sa.Column("run_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("algorithm", sa.String(50), nullable=False),
        sa.Column("dataset_name", sa.String(255), nullable=True),
        sa.Column("data_size", sa.Integer, nullable=True),
        sa.Column("deletion_fraction", sa.Float, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("metrics", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("processing_time_ms", sa.Integer, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_experiment_runs_experiment", "experiment_runs", ["experiment_id", "run_index"])

    op.create_table(
        "dataset_registry",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("dataset_type", sa.String(50), nullable=False, server_default="synthetic"),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("num_samples", sa.Integer, nullable=False, server_default="0"),
        sa.Column("num_features", sa.Integer, nullable=False, server_default="0"),
        sa.Column("num_classes", sa.Integer, nullable=False, server_default="2"),
        sa.Column("feature_names", postgresql.JSONB, nullable=True),
        sa.Column("class_names", postgresql.JSONB, nullable=True),
        sa.Column("tags", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("storage_path", sa.String(512), nullable=True),
        sa.Column("checksum", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_dataset_registry_tenant", "dataset_registry", ["tenant_id", "name"])


def downgrade() -> None:
    op.drop_table("dataset_registry")
    op.drop_table("experiment_runs")
    op.drop_table("experiments")
