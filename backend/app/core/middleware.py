"""HTTP middleware (Phase 7).

- ``SecurityHeadersMiddleware``: baseline hardening headers.
- ``RequestMetricsMiddleware``: Prometheus counters/histograms + in-process
  latency/error ring for the monitoring endpoint.
- ``APIKeyAuthMiddleware``: allows programmatic access via ``X-API-Key``
  (validated + quota enforced + usage logged) in addition to bearer tokens.
- ``OriginCheckMiddleware``: rejects state-changing cross-origin requests
  (CSRF defence for the token-in-header API) when an Origin header is present.
"""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.logging import get_logger
from app.db.session import session_factory

logger = get_logger("veriunlearn.middleware")

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; connect-src 'self'",
}

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        response.headers.setdefault("X-VeriUnlearn", "1")
        return response


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """CSRF defence: reject cross-origin state-changing requests."""

    async def dispatch(self, request: Request, call_next):
        if request.method not in _SAFE_METHODS:
            origin = request.headers.get("origin")
            if origin is not None and origin not in settings.CORS_ORIGINS:
                from starlette.responses import JSONResponse

                logger.warning("blocked cross-origin request origin=%s path=%s", origin, request.url.path)
                return JSONResponse(status_code=403, content={"error": "forbidden", "message": "Cross-origin request blocked"})
        return await call_next(request)


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start
        try:
            from app.services.metrics import observe_request
            from app.services.monitoring import record_request

            observe_request(request.method, request.url.path, response.status_code, duration)
            record_request(duration, is_error=response.status_code >= 500)
        except Exception:  # noqa: BLE001 - metrics must never break requests
            pass
        return response


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """If ``X-API-Key`` is present, authenticate it instead of the bearer.

    The key is validated (hash lookup, active, expiry, sliding-window quota)
    and usage is logged with the request path/status. Requests without a key
    fall through to the normal bearer-token dependencies.
    """

    async def dispatch(self, request: Request, call_next):
        api_key = request.headers.get("x-api-key")
        if api_key is None:
            return await call_next(request)
        # /metrics and /health stay bearer-free.
        if request.url.path in ("/health", "/metrics", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        async with session_factory() as session:
            try:
                from app.db.models import User
                from app.services.api_keys import APIKeyService

                key = await APIKeyService(session).authenticate(api_key)
                owner = await session.get(User, key.user_id)
                if owner is None or not owner.is_active:
                    raise UnauthorizedError("API key owner is inactive")
                request.state.api_key = key
                request.state.api_key_id = key.id
                # API keys authenticate as their owning user (role-based RBAC).
                request.state.api_key_user = {"sub": owner.id, "role": owner.role, "auth": "api_key"}
            except UnauthorizedError as exc:
                from starlette.responses import JSONResponse

                return JSONResponse(status_code=401, content={"error": "unauthorized", "message": str(exc)})
            except Exception:
                logger.exception("api key auth failed")
                from starlette.responses import JSONResponse

                return JSONResponse(status_code=401, content={"error": "unauthorized", "message": "Invalid API key"})

        response = await call_next(request)
        # Log usage after the response so we can record status + path.
        try:
            async with session_factory() as session:
                key = await session.get(type(key), request.state.api_key_id)
                if key is not None:
                    key.usage = (key.usage or [])[-49:] + [
                        {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "path": request.url.path, "status": response.status_code}
                    ]
                    await session.flush()
        except Exception:  # noqa: BLE001
            pass
        return response
