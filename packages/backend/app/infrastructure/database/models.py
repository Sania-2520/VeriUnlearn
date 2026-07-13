import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship

from app.core.database import Base


class TenantApiKeyModel(Base):
    __tablename__ = "tenant_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False)
    key_prefix = Column(String(8), nullable=False)
    scopes = Column(JSON, nullable=False, default=list)
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_used_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    tenant = relationship("TenantModel", backref="api_keys")
    creator = relationship("UserModel", foreign_keys=[created_by])

    __table_args__ = (
        Index("idx_tenant_api_keys_prefix", "key_prefix"),
    )


class TenantModel(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(128), unique=True, nullable=False, index=True)
    domain = Column(String(255))
    plan = Column(String(50), nullable=False, default="starter")
    settings = Column(JSON, nullable=False, default=dict)
    features = Column(JSON, nullable=False, default=dict)
    max_users = Column(Integer, nullable=False, default=10)
    max_storage_gb = Column(Integer, nullable=False, default=10)
    max_api_requests_per_min = Column(Integer, nullable=False, default=1000)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

    users = relationship("UserModel", back_populates="tenant", lazy="selectin")


class UserModel(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    avatar_url = Column(String(512))
    role = Column(String(50), nullable=False, default="member")
    is_email_verified = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_locked = Column(Boolean, nullable=False, default=False)
    locked_until = Column(DateTime(timezone=True))
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    last_login_at = Column(DateTime(timezone=True))
    last_login_ip = Column(INET)
    mfa_enabled = Column(Boolean, nullable=False, default=False)
    mfa_secret = Column(String(255))
    preferences = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

    tenant = relationship("TenantModel", back_populates="users", lazy="selectin")
    sessions = relationship("SessionModel", back_populates="user", lazy="selectin", cascade="all, delete-orphan")
    oauth_accounts = relationship("OAuthAccountModel", back_populates="user", lazy="selectin", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_tenant_email"),
        Index("idx_users_tenant", "tenant_id"),
    )


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token_hash = Column(String(255), nullable=False)
    access_token_jti = Column(String(255), unique=True, nullable=False)
    user_agent = Column(Text)
    ip_address = Column(INET)
    device_name = Column(String(255))
    is_revoked = Column(Boolean, nullable=False, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    revoked_at = Column(DateTime(timezone=True))

    user = relationship("UserModel", back_populates="sessions")

    __table_args__ = (
        Index("idx_sessions_user", "user_id"),
        Index("idx_sessions_refresh", "refresh_token_hash"),
    )


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    event_version = Column(String(10), nullable=False, default="1.0")
    actor_id = Column(String(36), nullable=True, index=True)
    actor_type = Column(String(20), nullable=False, default="user")
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(36), nullable=True)
    action = Column(String(255), nullable=False, default="")
    status = Column(String(20), nullable=False, default="success")
    event_metadata = Column("metadata", JSON, nullable=False, default=dict)
    changes = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    session_id = Column(String(36), nullable=True)
    request_id = Column(String(36), nullable=True)
    previous_event_hash = Column(String(64), nullable=True)
    event_hash = Column(String(64), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_audit_tenant_ts", "tenant_id", "timestamp"),
        Index("idx_audit_event_type", "event_type", "timestamp"),
    )


class AuditChainHeadModel(Base):
    __tablename__ = "audit_chain_heads"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), unique=True, nullable=False, index=True)
    last_event_hash = Column(String(64), nullable=False)
    chain_length = Column(Integer, nullable=False, default=0)
    merkle_root = Column(String(64), nullable=True)
    blockchain_tx_hash = Column(String(128), nullable=True)
    blockchain_network = Column(String(50), nullable=True)
    anchored_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)


class OAuthAccountModel(Base):
    __tablename__ = "oauth_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False)
    provider_user_id = Column(String(255), nullable=False)
    provider_email = Column(String(255))
    access_token = Column(Text)
    refresh_token = Column(Text)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    user = relationship("UserModel", back_populates="oauth_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
        Index("idx_oauth_accounts_user", "user_id"),
    )


class UnlearningRequestModel(Base):
    __tablename__ = "unlearning_requests"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    requested_by = Column(String(36), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(255), nullable=False)
    reason = Column(Text, nullable=True)
    gdpr_article = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    priority = Column(String(20), nullable=False, default="normal")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_unlearning_requests_tenant", "tenant_id", "status"),
        Index("idx_unlearning_requests_created", "tenant_id", "created_at"),
    )


class UnlearningJobModel(Base):
    __tablename__ = "unlearning_jobs"

    id = Column(String(36), primary_key=True)
    request_id = Column(String(36), ForeignKey("unlearning_requests.id", ondelete="CASCADE"), nullable=False)
    algorithm = Column(String(50), nullable=False, default="hybrid")
    model_id = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    progress = Column(Float, nullable=False, default=0.0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    results = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_unlearning_jobs_request", "request_id"),
    )


class DeletionQueueItemModel(Base):
    __tablename__ = "deletion_queue"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("unlearning_jobs.id", ondelete="SET NULL"), nullable=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(255), nullable=False)
    operation = Column(String(20), nullable=False)
    priority = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="pending")
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    error_message = Column(Text, nullable=True)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_deletion_queue_tenant_status", "tenant_id", "status"),
        Index("idx_deletion_queue_job", "job_id"),
    )


class ModelVersionModel(Base):
    __tablename__ = "model_versions"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    parent_version_id = Column(String(36), nullable=True)
    algorithm = Column(String(50), nullable=True)
    checkpoint_path = Column(String(512), nullable=True)
    model_weights_hash = Column(String(128), nullable=True)
    metrics = Column(JSON, nullable=True)
    config = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    is_unlearned = Column(Boolean, nullable=False, default=False)
    shard_count = Column(Integer, nullable=False, default=1)
    total_data_points = Column(Integer, nullable=False, default=0)
    removed_data_points = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_model_versions_tenant_name", "tenant_id", "name"),
    )


class ModelShardModel(Base):
    __tablename__ = "model_shards"

    id = Column(String(36), primary_key=True)
    model_version_id = Column(String(36), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False)
    shard_index = Column(Integer, nullable=False)
    checkpoint_path = Column(String(512), nullable=True)
    data_range = Column(JSON, nullable=True)
    data_point_count = Column(Integer, nullable=False, default=0)
    metrics = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_model_shards_version", "model_version_id", "shard_index"),
    )


class DeletionProofModel(Base):
    __tablename__ = "deletion_proofs"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    job_id = Column(String(36), ForeignKey("unlearning_jobs.id", ondelete="CASCADE"), nullable=False)
    request_id = Column(String(36), ForeignKey("unlearning_requests.id", ondelete="CASCADE"), nullable=False)
    proof_type = Column(String(20), nullable=False, default="merkle")
    merkle_root = Column(String(128), nullable=False, default="")
    merkle_tree_depth = Column(Integer, nullable=False, default=0)
    merkle_tree = Column(JSON, nullable=True)
    signature_algorithm = Column(String(20), nullable=False, default="ed25519")
    signature_hex = Column(String(512), nullable=False, default="")
    public_key_hex = Column(String(512), nullable=False, default="")
    zk_proof = Column(JSON, nullable=True)
    certificate = Column(Text, nullable=True)
    certificate_hash = Column(String(128), nullable=True)
    verified = Column(Boolean, nullable=False, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    event_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_deletion_proofs_request", "request_id"),
        Index("idx_deletion_proofs_job", "job_id"),
        Index("idx_deletion_proofs_tenant", "tenant_id"),
    )


class ProofVerificationModel(Base):
    __tablename__ = "proof_verifications"

    id = Column(String(36), primary_key=True)
    proof_id = Column(String(36), ForeignKey("deletion_proofs.id", ondelete="CASCADE"), nullable=False)
    verifier_id = Column(String(36), nullable=True)
    verification_method = Column(String(50), nullable=False, default="api")
    is_valid = Column(Boolean, nullable=False, default=False)
    details = Column(JSON, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_proof_verifications_proof", "proof_id"),
    )


class WebhookModel(Base):
    __tablename__ = "webhooks"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False)
    secret = Column(String(255), nullable=False)
    events = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)
    status = Column(String(20), nullable=False, default="active")
    headers = Column(JSON, nullable=True, default=dict)
    retry_count = Column(Integer, nullable=False, default=3)
    timeout_ms = Column(Integer, nullable=False, default=5000)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_webhooks_tenant", "tenant_id"),
    )


class WebhookEventLogModel(Base):
    __tablename__ = "webhook_event_logs"

    id = Column(String(36), primary_key=True)
    webhook_id = Column(String(36), ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    status = Column(String(20), nullable=False, default="pending")
    response_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_webhook_logs_webhook", "webhook_id", "created_at"),
        Index("idx_webhook_logs_retry", "status", "next_retry_at"),
    )
