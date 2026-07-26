import os
from enum import Enum
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


_PLACEHOLDER_SUBSTRINGS = ["change-me", "changeme", "placeholder", "replace-with"]


def _is_placeholder(val: str) -> bool:
    lowered = val.lower()
    for substr in _PLACEHOLDER_SUBSTRINGS:
        if substr in lowered:
            return True
    return False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── General ────────────────────────────────────────────
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    log_level: LogLevel = LogLevel.DEBUG
    app_name: str = "VeriUnlearn"
    version: str = "1.0.0"
    domain: str = "localhost:3000"
    allowed_hosts: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT

    # ─── PostgreSQL ─────────────────────────────────────────
    database_url: str = ""
    database_pool_size: int = 20
    database_max_overflow: int = 40
    database_echo: bool = False

    # ─── Redis ──────────────────────────────────────────────
    redis_url: str = ""
    redis_socket_timeout: int = 5
    redis_retry_on_timeout: bool = True

    # ─── RabbitMQ ───────────────────────────────────────────
    rabbitmq_url: str = ""

    # ─── Celery ────────────────────────────────────────────
    celery_broker_url: str = ""
    celery_result_backend: str = ""
    celery_worker_concurrency: int = 4
    celery_task_always_eager: bool = False

    # ─── JWT ──────────────────────────────────────────────
    secret_key: str = Field(default="", min_length=0)
    jwt_secret_key: str = Field(default="", min_length=0)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    jwt_issuer: str = "veriunlearn"
    jwt_audience: str = "veriunlearn-api"

    # ─── OAuth ─────────────────────────────────────────────
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: Optional[str] = None

    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None
    github_redirect_uri: Optional[str] = None

    # ─── Email ──────────────────────────────────────────────
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: str = "noreply@veriunlearn.com"
    smtp_from_name: str = "VeriUnlearn"

    # ─── AI Providers ───────────────────────────────────────
    openai_api_key: Optional[str] = None
    openai_organization: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_key: Optional[str] = None
    azure_openai_deployment: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3"
    vllm_base_url: str = "http://localhost:8000"
    huggingface_api_token: Optional[str] = None

    # ─── Qdrant ─────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    qdrant_collection_documents: str = "documents"
    qdrant_collection_memory: str = "memory"
    qdrant_collection_conversations: str = "conversations"
    qdrant_vector_size: int = 1536
    qdrant_replication_factor: int = 2

    # ─── MinIO ──────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "veriunlearn"
    minio_secret_key: str = Field(default="", min_length=0)
    minio_use_ssl: bool = False
    minio_documents_bucket: str = "documents"
    minio_uploads_bucket: str = "uploads"
    minio_models_bucket: str = "models"
    minio_proofs_bucket: str = "proofs"
    minio_exports_bucket: str = "exports"
    minio_temp_bucket: str = "temp"

    # ─── ML Engine ──────────────────────────────────────────
    ml_engine_url: str = "http://localhost:8001"
    ml_engine_api_key: Optional[str] = None
    ml_model_cache_dir: str = "/data/model_cache"
    ml_default_embedding_model: str = "BAAI/bge-large-en-v1.5"
    ml_default_llm: str = "mistralai/Mistral-7B-Instruct-v0.3"
    ml_training_batch_size: int = 32
    ml_training_epochs: int = 10
    ml_learning_rate: float = 2e-5
    ml_max_seq_length: int = 512
    ml_use_gpu: bool = True
    ml_gpu_devices: str = "0,1"
    ml_mixed_precision: str = "fp16"
    ml_flush_interval: int = 100
    ml_request_timeout: int = 300

    @property
    def ml_gpu_devices_list(self) -> List[int]:
        return [int(d) for d in self.ml_gpu_devices.split(",")]

    # ─── Unlearning ─────────────────────────────────────────
    unlearning_default_algorithm: str = "hybrid"
    unlearning_sisa_shards: int = 10
    unlearning_influence_batch_size: int = 64
    unlearning_certified_epsilon: float = 0.1
    unlearning_certified_delta: float = 1e-5
    unlearning_max_retries: int = 3
    unlearning_queue_max_size: int = 10000
    unlearning_worker_timeout: int = 300

    # ─── Verification ───────────────────────────────────────
    verification_key_type: str = "ed25519"
    verification_merkle_hash_algorithm: str = "SHA256"
    verification_zk_enabled: bool = False
    verification_certificate_expiry_days: int = 365

    # ─── Security ───────────────────────────────────────────
    security_mia_attack_ratio: float = 0.1
    security_num_shadow_models: int = 5
    security_extraction_query_limit: int = 1000
    security_max_score_threshold: float = 0.1
    security_scan_interval_hours: int = 24

    # ─── Audit ──────────────────────────────────────────────
    audit_blockchain_anchoring: bool = False
    audit_blockchain_network: str = "goerli"
    audit_ethereum_contract_address: Optional[str] = None
    audit_ethereum_private_key: Optional[str] = None
    audit_event_retention_days: int = 3650

    # ─── Compliance ─────────────────────────────────────────
    compliance_gdpr_contact: Optional[str] = None
    compliance_ai_act_contact: Optional[str] = None
    compliance_dpdp_contact: Optional[str] = None
    compliance_report_auto_generate: bool = True
    compliance_report_schedule: str = "0 0 1 * *"

    # ─── Monitoring ─────────────────────────────────────────
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    sentry_dsn: Optional[str] = None
    sentry_environment: Optional[str] = None
    opentelemetry_enabled: bool = True
    opentelemetry_endpoint: str = "http://localhost:4317"

    # ─── Rate Limiting ──────────────────────────────────────
    rate_limit_default: str = "100/minute"
    rate_limit_auth: str = "20/minute"
    rate_limit_streaming: str = "30/minute"
    rate_limit_unlearning: str = "10/minute"

    # ─── File Upload ────────────────────────────────────────
    max_upload_size_mb: int = 100
    allowed_upload_types: str = (
        "image/jpeg,image/png,application/pdf,text/plain,"
        "text/csv,application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    )

    @property
    def allowed_upload_types_list(self) -> List[str]:
        return [t.strip() for t in self.allowed_upload_types.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    # ─── CORS ───────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    cors_allow_credentials: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    # ─── Vault ──────────────────────────────────────────────
    vault_enabled: bool = False
    vault_url: Optional[str] = None
    vault_token: Optional[str] = None
    vault_kv_path: str = "veriunlearn"

    # ─── TLS ────────────────────────────────────────────────
    ssl_enabled: bool = False
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    ssl_ca_certs: Optional[str] = None

    @property
    def allowed_hosts_list(self) -> List[str]:
        if self.allowed_hosts:
            return [h.strip() for h in self.allowed_hosts.split(",")]
        return [self.domain] if self.domain else []

    @field_validator("secret_key", "jwt_secret_key")
    @classmethod
    def validate_secret_keys(cls, v: str) -> str:
        if not v:
            raise ValueError("Secret key must not be empty. Set via SECRET_KEY / JWT_SECRET_KEY env var.")
        if len(v) < 32:
            raise ValueError(f"Secret keys must be at least 32 characters (got {len(v)})")
        if _is_placeholder(v):
            raise ValueError(f"Secret key contains placeholder text — generate a strong random key.")
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL must be set")
        if not any(dialect in v for dialect in ("postgresql", "sqlite")):
            raise ValueError(f"DATABASE_URL must be a PostgreSQL or SQLite connection string")
        return v


settings = Settings()
