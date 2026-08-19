"""API key management (Phase 7).

Keys are issued as ``vk_<32 random chars>``; only the SHA-256 hash is stored.
Per-key quota is enforced with a sliding one-minute window persisted on the
row (survives restarts). Usage is tracked with counters plus a bounded rolling
log for the developer portal.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, UnauthorizedError, ValidationFailedError
from app.db.models import APIKey
from app.repositories.base import BaseRepository


class APIKeyRepository(BaseRepository[APIKey]):
    model = APIKey

    async def by_hash(self, key_hash: str) -> APIKey | None:
        result = await self.session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: str, *, limit: int = 100) -> list[APIKey]:
        result = await self.session.execute(
            select(APIKey).where(APIKey.user_id == user_id).order_by(APIKey.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; normalise to UTC-aware."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class APIKeyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = APIKeyRepository(session)

    async def issue(
        self,
        *,
        user_id: str,
        name: str,
        scopes: list[str] | None = None,
        quota_per_minute: int = 60,
        expires_in_days: int | None = 90,
    ) -> dict[str, Any]:
        if not name.strip():
            raise ValidationFailedError("Key name is required")
        if quota_per_minute < 1 or quota_per_minute > 100_000:
            raise ValidationFailedError("quota_per_minute must be 1..100000")
        scopes = scopes or ["*"]
        for scope in scopes:
            if scope != "*" and (":" not in scope or len(scope) > 64):
                raise ValidationFailedError(f"Invalid scope: {scope}")

        raw = "vk_" + secrets.token_urlsafe(24)
        now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC for naive column
        key = APIKey(
            user_id=user_id,
            name=name.strip(),
            key_hash=_hash_key(raw),
            key_prefix=raw[:10],
            scopes=scopes,
            quota_per_minute=quota_per_minute,
            expires_at=now + timedelta(days=expires_in_days) if expires_in_days else None,
        )
        await self.repo.add(key)
        return {
            "id": key.id,
            "name": key.name,
            "key": raw,  # shown exactly once
            "key_prefix": key.key_prefix,
            "scopes": key.scopes,
            "quota_per_minute": key.quota_per_minute,
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
        }

    async def authenticate(self, api_key: str) -> APIKey:
        """Validate a raw key, enforce quota, log usage. Raises on any failure."""
        key = await self.repo.by_hash(_hash_key(api_key))
        if key is None or not key.is_active:
            raise UnauthorizedError("Invalid or inactive API key")
        now = datetime.now(timezone.utc)
        if _aware(key.expires_at) is not None and _aware(key.expires_at) < now:
            raise UnauthorizedError("API key expired")
        # Sliding one-minute window.
        window_start = _aware(key.window_start)
        if window_start is None or now - window_start >= timedelta(minutes=1):
            key.window_start = now.replace(tzinfo=None)  # naive UTC for naive column
            key.window_count = 0
        if key.window_count >= key.quota_per_minute:
            raise UnauthorizedError("API key rate limit exceeded")
        key.window_count += 1
        key.requests_count += 1
        key.last_used_at = now.replace(tzinfo=None)  # naive UTC for naive column
        # Bounded rolling usage log (last 50 requests).
        key.usage = (key.usage or [])[-49:] + [{"at": now.isoformat(), "path": None, "status": None}]
        await self.session.flush()
        return key

    def log_usage(self, key: APIKey, *, path: str, status: int) -> None:
        usage = (key.usage or [])[-49:] + [{"at": datetime.now(timezone.utc).isoformat(), "path": path, "status": status}]
        key.usage = usage
        key.requests_count += 1

    async def revoke(self, key_id: str, user_id: str | None = None) -> APIKey:
        key = await self.repo.get(key_id)
        if user_id is not None and key.user_id != user_id:
            raise NotFoundError(f"API key {key_id} not found")
        key.is_active = False
        await self.session.flush()
        return key

    async def list_keys(self, user_id: str, *, include_secret: bool = False) -> list[dict[str, Any]]:
        keys = await self.repo.list_for_user(user_id)
        return [
            {
                "id": k.id,
                "name": k.name,
                "key_prefix": k.key_prefix,
                "scopes": k.scopes,
                "is_active": k.is_active,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "quota_per_minute": k.quota_per_minute,
                "requests_count": k.requests_count,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "usage": k.usage[-10:],
            }
            for k in keys
        ]
