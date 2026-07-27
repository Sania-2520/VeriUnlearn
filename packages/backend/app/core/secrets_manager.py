import base64
import os
import hashlib
from typing import Any, Optional

from cryptography.fernet import Fernet
from app.core.config import settings
from app.core.logging import get_logger

_PBKDF2_ITERATIONS = 600000
_PBKDF2_SALT = b"veriunlearn-key-derivation-v1"

logger = get_logger(__name__)


class SecretsManager:
    def __init__(self) -> None:
        self._vault_client: Optional[Any] = None
        self._initialized = False
        if settings.vault_enabled:
            self._init_vault()

    def _init_vault(self) -> None:
        try:
            import hvac
            self._vault_client = hvac.Client(
                url=settings.vault_url,
                token=settings.vault_token,
            )
            if self._vault_client.is_authenticated():
                self._initialized = True
                logger.info("Vault connection established")
            else:
                logger.warning("Vault authentication failed, falling back to env")
        except ImportError:
            logger.warning("hvac not installed, falling back to environment variables")
        except Exception as e:
            logger.warning("Vault init failed: %s, falling back to env", str(e))

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if self._initialized and self._vault_client:
            try:
                secret = self._vault_client.secrets.kv.v2.read_secret_version(
                    path=settings.vault_kv_path,
                    mount_point="secret",
                )
                data = secret.get("data", {}).get("data", {})
                return data.get(key, os.getenv(key, default))
            except Exception as e:
                logger.error("Failed to read secret '%s' from Vault: %s", key, e)
        return os.getenv(key, default)

    def get_database_url(self) -> str:
        return self.get_secret("DATABASE_URL", settings.database_url) or settings.database_url

    def get_redis_url(self) -> str:
        return self.get_secret("REDIS_URL", settings.redis_url) or settings.redis_url

    def get_jwt_secret(self) -> str:
        return self.get_secret("JWT_SECRET_KEY", settings.jwt_secret_key) or settings.jwt_secret_key

    def get_api_key(self, service: str) -> Optional[str]:
        env_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "azure": "AZURE_OPENAI_KEY",
            "huggingface": "HUGGINGFACE_API_TOKEN",
            "qdrant": "QDRANT_API_KEY",
        }
        env_key = env_map.get(service)
        if env_key:
            return self.get_secret(env_key)
        return None


    def encrypt_api_key(self, plaintext: Optional[str]) -> Optional[str]:
        if not plaintext:
            return None
        try:
            key = base64.urlsafe_b64encode(hashlib.pbkdf2_hmac("sha256", settings.secret_key.encode(), _PBKDF2_SALT, _PBKDF2_ITERATIONS, dklen=32))
            f = Fernet(key)
            return f.encrypt(plaintext.encode()).decode()
        except Exception as e:
            logger.error("Failed to encrypt API key: %s", str(e))
            raise

    def decrypt_api_key(self, ciphertext: Optional[str]) -> Optional[str]:
        if not ciphertext:
            return None
        try:
            key = base64.urlsafe_b64encode(hashlib.pbkdf2_hmac("sha256", settings.secret_key.encode(), _PBKDF2_SALT, _PBKDF2_ITERATIONS, dklen=32))
            f = Fernet(key)
            return f.decrypt(ciphertext.encode()).decode()
        except Exception:
            logger.exception("Failed to decrypt API key")
            return None


secrets_manager = SecretsManager()
