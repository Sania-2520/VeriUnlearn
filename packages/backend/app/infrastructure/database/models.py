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


class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="New Chat")
    folder_id = Column(String(36), nullable=True)
    ai_provider_id = Column(String(36), nullable=True)
    model = Column(String(255), nullable=True)
    system_prompt = Column(Text, nullable=True)
    temperature = Column(Float, nullable=False, default=0.7)
    max_tokens = Column(Integer, nullable=False, default=4096)
    is_pinned = Column(Boolean, nullable=False, default=False)
    is_archived = Column(Boolean, nullable=False, default=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    message_count = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    total_cost = Column(Float, nullable=False, default=0.0)
    event_metadata = Column("metadata", JSON, nullable=False, default=dict)
    last_activity_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_chat_sessions_user", "user_id", "tenant_id"),
        Index("idx_chat_sessions_activity", "tenant_id", "last_activity_at"),
    )


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(String(36), nullable=True)
    role = Column(String(20), nullable=False, default="user")
    content = Column(Text, nullable=False, default="")
    content_type = Column(String(20), nullable=False, default="text")
    content_rendered = Column(Text, nullable=True)
    event_metadata = Column("metadata", JSON, nullable=False, default=dict)
    is_streaming = Column(Boolean, nullable=False, default=False)
    is_regenerated = Column(Boolean, nullable=False, default=False)
    is_edited = Column(Boolean, nullable=False, default=False)
    feedback = Column(String(20), nullable=True)
    tokens_input = Column(Integer, nullable=False, default=0)
    tokens_output = Column(Integer, nullable=False, default=0)
    cost = Column(Float, nullable=False, default=0.0)
    latency_ms = Column(Integer, nullable=True)
    model_used = Column(String(255), nullable=True)
    provider_used = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_chat_messages_session", "session_id", "created_at"),
    )


class MemoryEntryModel(Base):
    __tablename__ = "memory_entries"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    session_id = Column(String(36), nullable=True)
    memory_type = Column(String(20), nullable=False, default="persistent")
    category = Column(String(50), nullable=True)
    content = Column(JSON, nullable=False, default=dict)
    importance = Column(Float, nullable=False, default=1.0)
    access_count = Column(Integer, nullable=False, default=0)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    event_metadata = Column("metadata", JSON, nullable=False, default=dict)
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_memory_entries_user", "tenant_id", "user_id", "memory_type"),
    )


class MemoryConfigModel(Base):
    __tablename__ = "memory_config"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), unique=True, nullable=False, index=True)
    persistent_memory_enabled = Column(Boolean, nullable=False, default=True)
    retention_days = Column(Integer, nullable=False, default=90)
    max_entries = Column(Integer, nullable=False, default=1000)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)


class ChatFolderModel(Base):
    __tablename__ = "chat_folders"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False)
    name = Column(String(255), nullable=False)
    parent_id = Column(String(36), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_chat_folders_user", "user_id", "tenant_id"),
    )


class RagDocumentModel(Base):
    __tablename__ = "rag_documents"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=True)
    filename = Column(String(512), nullable=False)
    original_filename = Column(String(512), nullable=False)
    file_type = Column(String(20), nullable=False, default="txt")
    file_size_bytes = Column(Integer, nullable=False, default=0)
    storage_path = Column(String(1024), nullable=False, default="")
    storage_bucket = Column(String(255), nullable=True)
    mime_type = Column(String(100), nullable=True)
    page_count = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    event_metadata = Column("metadata", JSON, nullable=False, default=dict)
    content_hash = Column(String(128), nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_rag_documents_tenant", "tenant_id", "status"),
    )


class RagDocumentChunkModel(Base):
    __tablename__ = "rag_document_chunks"

    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(128), nullable=False, default="")
    token_count = Column(Integer, nullable=False, default=0)
    event_metadata = Column("metadata", JSON, nullable=False, default=dict)
    embedding_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class ExperimentModel(Base):
    __tablename__ = "experiments"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    experiment_type = Column(String(50), nullable=False, default="benchmark")
    status = Column(String(20), nullable=False, default="draft")
    config = Column(JSON, nullable=False, default=dict)
    metrics = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=False, default=list)
    dataset_ids = Column(JSON, nullable=False, default=list)
    model_version_ids = Column(JSON, nullable=False, default=list)
    algorithm = Column(String(50), nullable=True)
    num_trials = Column(Integer, nullable=False, default=1)
    created_by = Column(String(36), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_experiments_tenant", "tenant_id", "status"),
        Index("idx_experiments_type", "tenant_id", "experiment_type"),
    )


class ExperimentRunModel(Base):
    __tablename__ = "experiment_runs"

    id = Column(String(36), primary_key=True)
    experiment_id = Column(String(36), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True)
    run_index = Column(Integer, nullable=False, default=0)
    algorithm = Column(String(50), nullable=False)
    dataset_name = Column(String(255), nullable=True)
    data_size = Column(Integer, nullable=True)
    deletion_fraction = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    metrics = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_experiment_runs_experiment", "experiment_id", "run_index"),
    )


class DatasetRegistryModel(Base):
    __tablename__ = "dataset_registry"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    dataset_type = Column(String(50), nullable=False, default="synthetic")
    source = Column(String(255), nullable=True)
    version = Column(String(20), nullable=False, default="1.0")
    num_samples = Column(Integer, nullable=False, default=0)
    num_features = Column(Integer, nullable=False, default=0)
    num_classes = Column(Integer, nullable=False, default=2)
    feature_names = Column(JSON, nullable=True)
    class_names = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=False, default=list)
    dataset_metadata = Column("metadata", JSON, nullable=False, default=dict)
    storage_path = Column(String(512), nullable=True)
    checksum = Column(String(128), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_dataset_registry_tenant", "tenant_id", "name"),
    )


class SecurityAssessmentModel(Base):
    __tablename__ = "security_assessments"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=True)
    model_version_id = Column(String(255), nullable=False)
    tests = Column(JSON, nullable=False, default=list)
    config = Column(JSON, nullable=False, default=dict)
    status = Column(String(20), nullable=False, default="queued")
    scores = Column(JSON, nullable=False, default=dict)
    results = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=False, default=list)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_security_assessments_tenant", "tenant_id", "status"),
    )


class AIProviderModel(Base):
    __tablename__ = "ai_providers"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    provider_type = Column(String(50), nullable=False)
    api_key_encrypted = Column(String(1024), nullable=True)
    models = Column(JSON, nullable=False, default=list)
    config = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)
    last_tested_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_ai_providers_tenant", "tenant_id", "name"),
    )
