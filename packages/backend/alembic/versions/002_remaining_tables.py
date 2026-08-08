"""Add remaining tables for audit, unlearning, verification, webhooks

Revision ID: 002
Revises: 001
Create Date: 2026-07-13 14:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("event_version", sa.String(10), nullable=False, server_default="1.0"),
        sa.Column("actor_id", sa.String(36), nullable=True, index=True),
        sa.Column("actor_type", sa.String(20), nullable=False, server_default="user"),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("action", sa.String(255), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="success"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("changes", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("request_id", sa.String(36), nullable=True),
        sa.Column("previous_event_hash", sa.String(64), nullable=True),
        sa.Column("event_hash", sa.String(64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_audit_tenant_ts", "audit_events", ["tenant_id", "timestamp"])
    op.create_index("idx_audit_event_type", "audit_events", ["event_type", "timestamp"])

    op.create_table(
        "audit_chain_heads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), unique=True, nullable=False, index=True),
        sa.Column("last_event_hash", sa.String(64), nullable=False),
        sa.Column("chain_length", sa.Integer, nullable=False, server_default="0"),
        sa.Column("merkle_root", sa.String(64), nullable=True),
        sa.Column("blockchain_tx_hash", sa.String(128), nullable=True),
        sa.Column("blockchain_network", sa.String(50), nullable=True),
        sa.Column("anchored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "unlearning_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("requested_by", sa.String(36), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("gdpr_article", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_unlearning_requests_tenant", "unlearning_requests", ["tenant_id", "status"])
    op.create_index("idx_unlearning_requests_created", "unlearning_requests", ["tenant_id", "created_at"])

    op.create_table(
        "unlearning_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_id", sa.String(36), sa.ForeignKey("unlearning_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("algorithm", sa.String(50), nullable=False, server_default="hybrid"),
        sa.Column("model_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Float, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_time_ms", sa.Integer, nullable=True),
        sa.Column("results", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_unlearning_jobs_request", "unlearning_jobs", ["request_id"])

    op.create_table(
        "deletion_queue",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("unlearning_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=False),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_deletion_queue_tenant_status", "deletion_queue", ["tenant_id", "status"])
    op.create_index("idx_deletion_queue_job", "deletion_queue", ["job_id"])

    op.create_table(
        "model_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("parent_version_id", sa.String(36), nullable=True),
        sa.Column("algorithm", sa.String(50), nullable=True),
        sa.Column("checkpoint_path", sa.String(512), nullable=True),
        sa.Column("model_weights_hash", sa.String(128), nullable=True),
        sa.Column("metrics", postgresql.JSONB, nullable=True),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("is_unlearned", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("shard_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("total_data_points", sa.Integer, nullable=False, server_default="0"),
        sa.Column("removed_data_points", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_model_versions_tenant_name", "model_versions", ["tenant_id", "name"])

    op.create_table(
        "model_shards",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_version_id", sa.String(36), sa.ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shard_index", sa.Integer, nullable=False),
        sa.Column("checkpoint_path", sa.String(512), nullable=True),
        sa.Column("data_range", postgresql.JSONB, nullable=True),
        sa.Column("data_point_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("metrics", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_model_shards_version", "model_shards", ["model_version_id", "shard_index"])

    op.create_table(
        "deletion_proofs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("unlearning_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_id", sa.String(36), sa.ForeignKey("unlearning_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("proof_type", sa.String(20), nullable=False, server_default="merkle"),
        sa.Column("merkle_root", sa.String(128), nullable=False, server_default=""),
        sa.Column("merkle_tree_depth", sa.Integer, nullable=False, server_default="0"),
        sa.Column("merkle_tree", postgresql.JSONB, nullable=True),
        sa.Column("signature_algorithm", sa.String(20), nullable=False, server_default="ed25519"),
        sa.Column("signature_hex", sa.String(512), nullable=False, server_default=""),
        sa.Column("public_key_hex", sa.String(512), nullable=False, server_default=""),
        sa.Column("zk_proof", postgresql.JSONB, nullable=True),
        sa.Column("certificate", sa.Text, nullable=True),
        sa.Column("certificate_hash", sa.String(128), nullable=True),
        sa.Column("verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_deletion_proofs_request", "deletion_proofs", ["request_id"])
    op.create_index("idx_deletion_proofs_job", "deletion_proofs", ["job_id"])
    op.create_index("idx_deletion_proofs_tenant", "deletion_proofs", ["tenant_id"])

    op.create_table(
        "proof_verifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proof_id", sa.String(36), sa.ForeignKey("deletion_proofs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verifier_id", sa.String(36), nullable=True),
        sa.Column("verification_method", sa.String(50), nullable=False, server_default="api"),
        sa.Column("is_valid", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_proof_verifications_proof", "proof_verifications", ["proof_id"])

    op.create_table(
        "webhooks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("secret", sa.String(255), nullable=False),
        sa.Column("events", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("headers", postgresql.JSONB, nullable=True, server_default="{}"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="3"),
        sa.Column("timeout_ms", sa.Integer, nullable=False, server_default="5000"),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_webhooks_tenant", "webhooks", ["tenant_id"])

    op.create_table(
        "webhook_event_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("webhook_id", sa.String(36), sa.ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("response_code", sa.Integer, nullable=True),
        sa.Column("response_body", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default="3"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_webhook_logs_webhook", "webhook_event_logs", ["webhook_id", "created_at"])
    op.create_index("idx_webhook_logs_retry", "webhook_event_logs", ["status", "next_retry_at"])


def downgrade() -> None:
    op.drop_table("webhook_event_logs")
    op.drop_table("webhooks")
    op.drop_table("proof_verifications")
    op.drop_table("deletion_proofs")
    op.drop_table("model_shards")
    op.drop_table("model_versions")
    op.drop_table("deletion_queue")
    op.drop_table("unlearning_jobs")
    op.drop_table("unlearning_requests")
    op.drop_table("audit_chain_heads")
    op.drop_table("audit_events")
