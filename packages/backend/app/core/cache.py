import json
from typing import Any, Optional
from datetime import timedelta

import redis.asyncio as aioredis

from app.core.config import settings


class CacheManager:
    _redis: aioredis.Redis | None = None

    async def initialize(self) -> None:
        self._redis = aioredis.from_url(
            settings.redis_url,
            socket_timeout=settings.redis_socket_timeout,
            retry_on_timeout=settings.redis_retry_on_timeout,
            decode_responses=True,
        )
        await self._redis.ping()

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None

    @property
    def redis(self) -> aioredis.Redis:
        if not self._redis:
            raise RuntimeError("Redis not initialized. Call initialize() first.")
        return self._redis

    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | timedelta | None = None,
    ) -> None:
        serialized = json.dumps(value, default=str)
        if ttl is not None:
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            await self.redis.setex(key, ttl, serialized)
        else:
            await self.redis.set(key, serialized)

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor=cursor, match=pattern)
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break

    async def exists(self, key: str) -> bool:
        return await self.redis.exists(key) > 0

    async def ttl(self, key: str) -> int:
        return await self.redis.ttl(key)

    async def incr(self, key: str) -> int:
        return await self.redis.incr(key)

    async def expire(self, key: str, ttl: int) -> None:
        await self.redis.expire(key, ttl)

    async def publish(self, channel: str, message: Any) -> None:
        serialized = json.dumps(message, default=str)
        await self.redis.publish(channel, serialized)

    async def subscribe(self, channel: str) -> aioredis.client.PubSub:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        return pubsub


cache = CacheManager()
