"""Application configuration.

All settings are environment-driven (12-factor). Defaults target local
development; production values are documented in ``.env.example`` and the
deployment guide.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../backend


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "VeriUnlearn"
    ENV: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    # ``NoDecode`` keeps comma-separated values from a ``.env`` file working
    # (pydantic-settings would otherwise try to JSON-parse a complex field and
    # raise instead of falling back to the validator below).
    CORS_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # --- Auth ---
    SECRET_KEY: str = "dev-only-change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./veriunlearn.db"

    # --- Caching / rate limiting ---
    REDIS_URL: str | None = None
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # --- Vector store ---
    VECTOR_STORE_BACKEND: str = "memory"  # memory | qdrant
    QDRANT_URL: str | None = None
    QDRANT_API_KEY: str | None = None

    # --- ML ---
    DEFAULT_SHARD_COUNT: int = 4
    DEFAULT_TRAIN_FRACTION: float = 0.8
    MAX_UPLOAD_MB: int = 50
    DATA_DIR: Path = PROJECT_ROOT / "data"
    MODEL_DIR: Path = PROJECT_ROOT / "models"
    KEYS_DIR: Path = PROJECT_ROOT / "keys"
    IDENTITY_SYNTHESIS_SEED: int = 42

    # --- Crypto ---
    RSA_KEY_BITS: int = 2048
    SERVER_PRIVATE_KEY_PATH: Path = PROJECT_ROOT / "keys" / "server_private.pem"
    SERVER_PUBLIC_KEY_PATH: Path = PROJECT_ROOT / "keys" / "server_public.pem"

    # --- Blockchain (optional) ---
    BLOCKCHAIN_ENABLED: bool = False
    BLOCKCHAIN_RPC_URL: str | None = None
    BLOCKCHAIN_REGISTRY_ADDRESS: str | None = None

    # --- Notifications (Phase 7) ---
    EMAIL_PROVIDER: str = "null"  # null | smtp
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str = "noreply@veriunlearn.dev"
    NOTIFICATION_MAX_ATTEMPTS: int = 5

    # --- Monitoring / metrics (Phase 7) ---
    PROMETHEUS_ENABLED: bool = True
    METRICS_TOKEN: str | None = None  # optional bearer token for /metrics

    # --- API keys (Phase 7) ---
    API_KEY_DEFAULT_QUOTA: int = 60

    # --- Assistant (OpenAI-compatible LLM) ---
    LLM_BASE_URL: str | None = None  # e.g. https://api.openai.com/v1
    LLM_API_KEY: str | None = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: int = 120
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2048

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_async_db(self) -> bool:
        return self.DATABASE_URL.startswith(("postgres", "sqlite+aiosqlite"))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.KEYS_DIR.mkdir(parents=True, exist_ok=True)
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
