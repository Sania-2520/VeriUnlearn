from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me-in-production"

    # Database — PostgreSQL for production, SQLite for development fallback
    database_url: str = ""
    postgres_user: str = "veriunlearn"
    postgres_password: str = "veriunlearn_secret"
    postgres_db: str = "veriunlearn"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    sqlite_path: str = str(Path(__file__).parent.parent.parent.parent / "data" / "veriunlearn.db")

    def _use_sqlite(self) -> bool:
        return self.app_env == "development" or not self.database_url

    def get_database_url(self, async_driver: bool = True) -> str:
        if self._use_sqlite():
            db_path = self.sqlite_path
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            driver = "sqlite+aiosqlite" if async_driver else "sqlite"
            return f"{driver}:///{db_path}"
        if self.database_url:
            return self.database_url
        driver = "postgresql+asyncpg" if async_driver else "postgresql"
        return (
            f"{driver}://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    # MinIO
    minio_root_user: str = "veriunlearn"
    minio_root_password: str = "veriunlearn_secret"
    minio_host: str = "localhost"
    minio_port: int = 9000
    minio_bucket: str = "models"

    @property
    def minio_endpoint(self) -> str:
        return f"http://{self.minio_host}:{self.minio_port}"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ML
    base_model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"
    device: str = "cuda"
    quantization_bits: int = 4
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    use_gradient_checkpointing: bool = True
    max_seq_length: int = 2048
    batch_size: int = 4
    learning_rate: float = 2e-4
    num_epochs: int = 3
    warmup_ratio: float = 0.03

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # OpenTelemetry
    otel_service_name: str = "veriunlearn"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"

    # Paths
    model_cache_dir: str = str(Path.home() / ".cache" / "veriunlearn" / "models")
    adapter_storage_dir: str = str(Path.home() / ".cache" / "veriunlearn" / "adapters")
    certificate_storage_dir: str = str(Path(__file__).parent.parent.parent.parent / "proofs" / "certificates")

    # Unlearning execution mode: "virtual" uses deterministic stubs; "real" uses
    # the algorithm classes with GPU LoRA retraining when available.
    unlearning_mode: str = "virtual"

    # Signing key (Ed25519) used for certificate + result proofs. Override with
    # SIGNING_KEY_PATH to point at a KMS-backed or mounted key file.
    signing_key_path: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def resolved_signing_key_path(self) -> Path:
        return Path(self.signing_key_path) if self.signing_key_path else Path(self.adapter_storage_dir) / "signing_key"


settings = Settings()

os.makedirs(settings.model_cache_dir, exist_ok=True)
os.makedirs(settings.adapter_storage_dir, exist_ok=True)
os.makedirs(settings.certificate_storage_dir, exist_ok=True)
