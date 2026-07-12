from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey


PREFIX_LENGTH = 8
KEY_LENGTH = 48


def _generate_key() -> tuple[str, str, str]:
    key = secrets.token_hex(KEY_LENGTH)
    prefix = key[:PREFIX_LENGTH]
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key, prefix, key_hash


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class ApiKeyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_key(self, user_id: int, name: str, scopes: str | None = None) -> tuple[ApiKey, str]:
        key, prefix, key_hash = _generate_key()
        api_key = ApiKey(
            user_id=user_id,
            name=name,
            prefix=prefix,
            key_hash=key_hash,
            scopes=scopes,
        )
        self.db.add(api_key)
        await self.db.flush()
        await self.db.refresh(api_key)
        return api_key, key

    async def list_keys(self, user_id: int) -> list[ApiKey]:
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_key(self, key_id: int, user_id: int) -> None:
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
        )
        key = result.scalar_one_or_none()
        if key is None:
            raise ValueError("API key not found")
        await self.db.delete(key)
        await self.db.flush()

    async def authenticate(self, key: str) -> ApiKey | None:
        key_hash = _hash_key(key)
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active)
        )
        api_key = result.scalar_one_or_none()
        if api_key is None:
            return None
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            return None
        api_key.last_used_at = datetime.now(timezone.utc)
        return api_key
