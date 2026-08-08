import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext  # type: ignore[import-untyped]  # no stubs shipped

from app.core.config import settings

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)  # type: ignore[no-any-return]  # passlib untyped


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)  # type: ignore[no-any-return]  # passlib untyped


class TokenManager:
    """JWT issuing/validation backed by PyJWT (maintained).

    Migrated from python-jose (3.3.0, unmaintained, multiple unfixed
    advisories incl. PYSEC-2024-232/233 and PYSEC-2025-185). Signature,
    audience, issuer, expiry and algorithm-pinning behaviour are identical;
    tokens issued before the migration remain valid.
    """

    def __init__(self) -> None:
        self._refresh_token_bytes = 64

    def create_access_token(
        self,
        subject: str,
        extra_claims: dict[str, Any] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        if expires_delta is None:
            expires_delta = timedelta(
                minutes=settings.jwt_access_token_expire_minutes
            )

        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + expires_delta,
            "jti": secrets.token_hex(16),
            "type": "access",
        }
        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    def create_refresh_token(
        self,
        subject: str,
        extra_claims: dict[str, Any] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        if expires_delta is None:
            expires_delta = timedelta(
                days=settings.jwt_refresh_token_expire_days
            )

        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + expires_delta,
            "jti": secrets.token_hex(16),
            "type": "refresh",
            "token_hash": hashlib.sha256(
                secrets.token_bytes(self._refresh_token_bytes)
            ).hexdigest(),
        }
        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    def decode_token(self, token: str) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
                audience=settings.jwt_audience,
                issuer=settings.jwt_issuer,
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "require": ["exp", "iat"],
                },
            )
            return payload
        except InvalidTokenError as e:
            raise TokenError(f"Invalid token: {e}") from e

    def verify_token(self, token: str, expected_type: str = "access") -> dict[str, Any]:
        payload = self.decode_token(token)
        token_type = payload.get("type")
        if token_type != expected_type:
            raise TokenError(
                f"Invalid token type: expected {expected_type}, got {token_type}"
            )
        return payload

    def generate_token_hash(self) -> tuple[str, str]:
        raw = secrets.token_hex(self._refresh_token_bytes)
        hashed = hashlib.sha256(raw.encode()).hexdigest()
        return raw, hashed

    def hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()


token_manager = TokenManager()


class TokenError(Exception):
    def __init__(self, message: str = "Token error") -> None:
        self.message = message
        super().__init__(self.message)


def generate_secure_token(length: int = 32) -> str:
    return secrets.token_hex(length)


def generate_api_key() -> tuple[str, str, str]:
    raw = f"vu_{secrets.token_urlsafe(32)}"
    hashed = hmac.new(settings.secret_key.encode(), raw.encode(), hashlib.sha384).hexdigest()
    prefix = raw[:8]
    return raw, hashed, prefix
