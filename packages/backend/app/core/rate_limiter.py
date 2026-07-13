import time
import uuid
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
    window_ms: int


class SlidingWindowRateLimiter:
    """Redis-backed sliding window rate limiter using a sorted set.

    Uses ZREMRANGEBYSCORE to expire old entries and ZCARD to count
    requests in the current window, giving accurate sliding-window
    semantics instead of the fixed-window bucket approach.
    """

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
        return f"ratelimit:{self.group}:{identifier}"

    async def check(self, identifier: str) -> RateLimitResult:
        key = self._key(identifier)
        now_ms = time.time() * 1000
        window_start_ms = now_ms - (self.window_seconds * 1000)
        window_ms = self.window_seconds * 1000

        try:
            redis = cache.redis
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start_ms)
            pipe.zcard(key)
            pipe.zadd(key, {f"{uuid.uuid4()}": now_ms})
            pipe.expire(key, self.window_seconds)
            results = await pipe.execute()

            current = results[1]  # ZCARD result
        except Exception:
            current = 0

        allowed = current < self.max_requests
        if not allowed:
            try:
                await cache.redis.zrem(key, f"{uuid.uuid4()}")
            except Exception:
                pass

        return RateLimitResult(
            allowed=allowed,
            remaining=max(0, self.max_requests - current - (1 if allowed else 0)),
            reset_after=self.window_seconds,
            limit=self.max_requests,
            window_ms=window_ms,
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
                    "X-RateLimit-Window": str(result.window_ms),
                    "Retry-After": str(result.reset_after),
                },
            )


class TenantSlidingWindowRateLimiter(SlidingWindowRateLimiter):
    """Rate limiter keyed on tenant ID instead of IP."""

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
                    "X-RateLimit-Window": str(result.window_ms),
                    "Retry-After": str(result.reset_after),
                },
            )


def parse_rate_limit(spec: str) -> tuple[int, int]:
    """Parse '100/minute' into (100, 60)."""
    parts = spec.split("/")
    count = int(parts[0])
    unit = parts[1] if len(parts) > 1 else "minute"
    window = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}.get(unit, 60)
    return count, window


def make_rate_limiter(
    max_requests: int = 60,
    window_seconds: int = 60,
    group: str = "default",
    by_tenant: bool = False,
) -> SlidingWindowRateLimiter:
    cls = TenantSlidingWindowRateLimiter if by_tenant else SlidingWindowRateLimiter
    return cls(
        max_requests=max_requests,
        window_seconds=window_seconds,
        group=group,
    )


class PerEndpointRateLimiter:
    """Routes requests to per-endpoint limiters based on path prefix.

    Maps:
        /api/v*/auth/*       -> 20/min   (authentication)
        /api/v*/inference/*  -> 30/min   (inference)
        /api/v*/training/*   -> 10/min   (training)
        /api/v*/unlearning/* -> 10/min   (unlearning)
        everything else      -> configurable default
    """

    _ENDPOINT_LIMITS: dict[str, tuple[int, int]] = {
        "auth":       parse_rate_limit(settings.rate_limit_auth),
        "inference":  parse_rate_limit(settings.rate_limit_streaming),
        "training":   parse_rate_limit(settings.rate_limit_unlearning),
        "unlearning": parse_rate_limit(settings.rate_limit_unlearning),
    }

    def __init__(self, group: str = "per-endpoint") -> None:
        self.group = group
        self._limiters: dict[str, SlidingWindowRateLimiter] = {}
        default_count, default_window = parse_rate_limit(settings.rate_limit_default)
        self._default_limiter = SlidingWindowRateLimiter(
            window_seconds=default_window,
            max_requests=default_count,
            group=f"{group}:default",
        )
        for name, (count, window) in self._ENDPOINT_LIMITS.items():
            self._limiters[name] = SlidingWindowRateLimiter(
                window_seconds=window,
                max_requests=count,
                group=f"{group}:{name}",
            )

    def _resolve_limiter(self, path: str) -> SlidingWindowRateLimiter:
        normalised = path.lower().rstrip("/")
        for name, limiter in self._limiters.items():
            if f"/{name}" in normalised:
                return limiter
        return self._default_limiter

    async def __call__(self, request: Request) -> None:
        limiter = self._resolve_limiter(request.url.path)
        await limiter(request)


class TenantPerEndpointRateLimiter(PerEndpointRateLimiter):
    """Same path-based routing but keyed on tenant ID."""

    def __init__(self, group: str = "per-endpoint-tenant") -> None:
        super().__init__(group=group)
        default_count, default_window = parse_rate_limit(settings.rate_limit_default)
        self._default_limiter = TenantSlidingWindowRateLimiter(
            window_seconds=default_window,
            max_requests=default_count,
            group=f"{group}:default",
        )
        self._limiters = {}
        for name, (count, window) in self._ENDPOINT_LIMITS.items():
            self._limiters[name] = TenantSlidingWindowRateLimiter(
                window_seconds=window,
                max_requests=count,
                group=f"{group}:{name}",
            )

    async def __call__(self, request: Request) -> None:
        limiter = self._resolve_limiter(request.url.path)
        await limiter(request)


_default_count, _default_window = parse_rate_limit(settings.rate_limit_default)
_default_limiter = SlidingWindowRateLimiter(
    max_requests=_default_count, window_seconds=_default_window, group="global",
)
_endpoint_limiter = PerEndpointRateLimiter()
_tenant_endpoint_limiter = TenantPerEndpointRateLimiter()


async def default_rate_limiter(request: Request) -> None:
    await _default_limiter(request)


async def endpoint_rate_limiter(request: Request) -> None:
    await _endpoint_limiter(request)


async def tenant_endpoint_rate_limiter(request: Request) -> None:
    await _tenant_endpoint_limiter(request)
