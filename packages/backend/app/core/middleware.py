import time
import uuid
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_SENSITIVE_HEADERS = {"authorization", "x-api-key", "cookie", "set-cookie", "x-api-key"}
_SENSITIVE_QUERY_PARAMS = {"token", "key", "secret", "password", "api_key", "access_token"}


def _redact_sensitive(request: Request) -> dict:
    headers = dict(request.headers)
    for key in headers:
        if key.lower() in _SENSITIVE_HEADERS:
            headers[key] = "[REDACTED]"
    query = str(request.url.query) if request.url.query else ""
    return {"headers": headers, "query": query}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response = await call_next(request)
        duration = (time.perf_counter() - start_time) * 1000

        logger.info(
            "Request processed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration, 2),
                "ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(round(duration, 2))
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)

        csp_parts = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "base-uri 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_parts)
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), usb=(), serial=(), display-capture=()"
        )
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        return response


class RateLimitAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)

        if response.status_code == 429:
            await self._record_rate_limit_event(request, response)

        return response

    async def _record_rate_limit_event(
        self, request: Request, response: Response
    ) -> None:
        from app.domain.audit.entities import EventType, ActorType, EventStatus
        from app.domain.audit.services import AuditService
        from app.infrastructure.database.repositories.audit import (
            SQLAlchemyAuditEventRepository,
        )
        from app.core.database import db

        try:
            async with db.session_factory() as session:
                repo = SQLAlchemyAuditEventRepository(session)
                svc = AuditService(repo=repo)

                limit = response.headers.get("X-RateLimit-Limit", "unknown")
                remaining = response.headers.get("X-RateLimit-Remaining", "0")
                reset_after = response.headers.get("X-RateLimit-Reset", "0")
                retry_after = response.headers.get("Retry-After", "0")

                await svc.record(
                    tenant_id=getattr(request.state, "tenant_id", "anonymous"),
                    event_type=EventType.RATE_LIMITED,
                    actor_id=getattr(request.state, "current_user_id", None),
                    actor_type=ActorType.SYSTEM,
                    resource_type="rate_limit",
                    resource_id=request.url.path,
                    action="rate_limit_exceeded",
                    status=EventStatus.FAILURE,
                    metadata={
                        "limit": limit,
                        "remaining": remaining,
                        "reset_after": reset_after,
                        "retry_after": retry_after,
                        "method": request.method,
                        "path": request.url.path,
                        "ip": request.client.host if request.client else None,
                    },
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    request_id=getattr(request.state, "request_id", None),
                )
        except Exception as e:
            logger.warning("Failed to record rate limit audit event: %s", e, exc_info=True)


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitAuditMiddleware)
