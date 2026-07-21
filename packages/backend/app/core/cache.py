import json
import time
from typing import Any, Optional
from datetime import timedelta

import redis.asyncio as aioredis

from app.core.config import settings


class InMemoryRedis:
    def __init__(self):
        self._store = {}
        self._expiry = {}

    async def ping(self):
        return True

    async def get(self, key):
        if key in self._expiry and time.time() > self._expiry[key]:
            self._store.pop(key, None)
            self._expiry.pop(key, None)
            return None
        return self._store.get(key)

    async def set(self, key, value):
        self._store[key] = value
        self._expiry.pop(key, None)

    async def setex(self, key, ttl, value):
        self._store[key] = value
        self._expiry[key] = time.time() + ttl

    async def delete(self, *keys):
        for key in keys:
            self._store.pop(key, None)
            self._expiry.pop(key, None)

    async def scan(self, cursor=0, match=None, count=None):
        keys = list(self._store.keys())
        if match:
            import fnmatch
            pattern = match.replace("*", "")
            keys = [k for k in keys if pattern in k]
        return 0, keys

    async def exists(self, key):
        return 1 if key in self._store else 0

    async def ttl(self, key):
        if key in self._expiry:
            remaining = int(self._expiry[key] - time.time())
            return max(remaining, 0)
        return -1 if key not in self._store else 3600

    async def incr(self, key):
        val = int(self._store.get(key, 0)) + 1
        self._store[key] = str(val)
        return val

    async def expire(self, key, ttl):
        if key in self._store:
            self._expiry[key] = time.time() + ttl

    async def publish(self, channel, message):
        from app.core.logging import get_logger
        get_logger(__name__).warning(
            f"InMemoryRedis.publish({channel}, ...) is a no-op — pub/sub requires a real Redis instance"
        )

    def pubsub(self):
        class PubSub:
            async def subscribe(self, channel):
                from app.core.logging import get_logger
                get_logger(__name__).warning(
                    f"InMemoryRedis.subscribe({channel}) is a no-op — pub/sub requires a real Redis instance"
                )
            async def close(self):
                from app.core.logging import get_logger
                get_logger(__name__).warning("InMemoryRedis PubSub.close() is a no-op")
        return PubSub()

    async def close(self):
        self._store.clear()
        self._expiry.clear()


class CacheManager:
    _redis: Any = None

    async def initialize(self) -> None:
        try:
            self._redis = aioredis.from_url(
                settings.redis_url,
                socket_timeout=settings.redis_socket_timeout,
                retry_on_timeout=settings.redis_retry_on_timeout,
                decode_responses=True,
            )
            await self._redis.ping()
        except Exception as e:
            from app.core.logging import get_logger
            get_logger(__name__).warning(
                f"Could not connect to Redis at {settings.redis_url}: {e}. "
                "Falling back to InMemoryRedis for local run."
            )
            self._redis = InMemoryRedis()

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
