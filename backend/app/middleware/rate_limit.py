from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


@dataclass
class RateLimit:
    max_requests: int
    window_seconds: int


@dataclass
class UsageQuota:
    max_training_samples: int = 10000
    max_documents: int = 100
    max_conversations: int = 500
    max_unlearning_requests: int = 50


RATE_LIMITS: dict[str, RateLimit] = {
    "default": RateLimit(max_requests=60, window_seconds=60),
    "chat": RateLimit(max_requests=30, window_seconds=60),
    "training": RateLimit(max_requests=10, window_seconds=300),
    "unlearning": RateLimit(max_requests=5, window_seconds=300),
    "upload": RateLimit(max_requests=20, window_seconds=60),
    "export": RateLimit(max_requests=5, window_seconds=300),
}

ROLE_MULTIPLIERS: dict[str, float] = {
    "admin": 3.0,
    "user": 1.0,
    "auditor": 0.5,
}


class RateLimitStore:
    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, limit: RateLimit, multiplier: float = 1.0) -> bool:
        now = time.time()
        window_start = now - limit.window_seconds

        self._requests[key] = [t for t in self._requests[key] if t > window_start]

        effective_limit = int(limit.max_requests * multiplier)
        if len(self._requests[key]) >= effective_limit:
            return False

        self._requests[key].append(now)
        return True

    def get_remaining(self, key: str, limit: RateLimit, multiplier: float = 1.0) -> int:
        now = time.time()
        window_start = now - limit.window_seconds
        recent = [t for t in self._requests[key] if t > window_start]
        effective_limit = int(limit.max_requests * multiplier)
        return max(0, effective_limit - len(recent))

    def get_reset_time(self, key: str) -> float:
        if not self._requests[key]:
            return 0
        oldest = min(self._requests[key])
        return max(0, oldest + 60 - time.time())


_store = RateLimitStore()


def _get_rate_limit_category(path: str) -> str:
    if "/chat/" in path:
        return "chat"
    if "/training/" in path:
        return "training"
    if "/unlearning/" in path:
        return "unlearning"
    if "/documents/" in path and ("upload" in path or "process" in path):
        return "upload"
    if "/gdpr/" in path:
        return "export"
    return "default"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)

        import os
        if os.environ.get("RATE_LIMIT_DISABLED") == "1":
            return await call_next(request)

        path = request.url.path
        category = _get_rate_limit_category(path)
        limit = RATE_LIMITS.get(category, RATE_LIMITS["default"])

        user_id = None
        role = "user"
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_token
                token = auth_header[7:]
                payload = decode_token(token)
                if payload:
                    user_id = payload.get("sub")
                    role = payload.get("role", "user")
            except Exception:
                pass

        if user_id is None:
            client_ip = request.client.host if request.client else "unknown"
            key = f"ip:{client_ip}:{category}"
            multiplier = 0.5
        else:
            key = f"user:{user_id}:{category}"
            multiplier = ROLE_MULTIPLIERS.get(role, 1.0)

        if not _store.is_allowed(key, limit, multiplier):
            remaining = _store.get_remaining(key, limit, multiplier)
            reset_time = _store.get_reset_time(key)

            try:
                from app.metrics import RATE_LIMIT_HITS
                RATE_LIMIT_HITS.labels(category=category).inc()
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "category": category,
                    "limit": int(limit.max_requests * multiplier),
                    "window_seconds": limit.window_seconds,
                    "remaining": remaining,
                    "retry_after_seconds": int(reset_time),
                },
                headers={
                    "Retry-After": str(int(reset_time)),
                    "X-RateLimit-Limit": str(int(limit.max_requests * multiplier)),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Category": category,
                },
            )

        response = await call_next(request)

        remaining = _store.get_remaining(key, limit, multiplier)
        response.headers["X-RateLimit-Limit"] = str(int(limit.max_requests * multiplier))
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Category"] = category

        return response
