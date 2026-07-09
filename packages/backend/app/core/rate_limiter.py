import time
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request, status

from app.core.cache import cache
from app.core.config import settings


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_after: int
    limit: int


class RateLimiter:
    def __init__(
        self,
        window_seconds: int = 60,
        max_requests: int = 60,
        group: str = "default",
    ) -> None:
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.group = group

    def _key(self, identifier: str) -> str:
        window = int(time.time() / self.window_seconds)
        return f"ratelimit:{self.group}:{window}:{identifier}"

    async def check(self, identifier: str) -> RateLimitResult:
        key = self._key(identifier)
        current = await cache.redis.incr(key)
        if current == 1:
            await cache.redis.expire(key, self.window_seconds)
        ttl = await cache.redis.ttl(key)
        if ttl < 0:
            ttl = self.window_seconds
        return RateLimitResult(
            allowed=current <= self.max_requests,
            remaining=max(0, self.max_requests - current),
            reset_after=int(ttl),
            limit=self.max_requests,
        )

    async def __call__(self, request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        result = await self.check(ip)
        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": str(result.remaining),
                    "X-RateLimit-Reset": str(result.reset_after),
                    "Retry-After": str(result.reset_after),
                },
            )


class TenantRateLimiter(RateLimiter):
    async def __call__(self, request: Request) -> None:
        tenant_id = getattr(request.state, "tenant_id", None) or "anonymous"
        result = await self.check(tenant_id)
        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Tenant rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": str(result.remaining),
                    "X-RateLimit-Reset": str(result.reset_after),
                    "Retry-After": str(result.reset_after),
                },
            )


def make_rate_limiter(
    max_requests: int = 60,
    window_seconds: int = 60,
    group: str = "default",
    by_tenant: bool = False,
) -> RateLimiter:
    cls = TenantRateLimiter if by_tenant else RateLimiter
    return cls(
        max_requests=max_requests,
        window_seconds=window_seconds,
        group=group,
    )


def parse_rate_limit(spec: str) -> tuple[int, int]:
    """Parse '100/minute' into (100, 60)."""
    parts = spec.split("/")
    count = int(parts[0])
    unit = parts[1] if len(parts) > 1 else "minute"
    window = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}.get(unit, 60)
    return count, window


_default_count, _default_window = parse_rate_limit(settings.rate_limit_default)
_default_limiter = RateLimiter(max_requests=_default_count, window_seconds=_default_window, group="global")


async def default_rate_limiter(request: Request) -> None:
    await _default_limiter(request)
