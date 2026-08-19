"""VeriUnlearn API — verifiable machine unlearning for GDPR/DPDP compliance."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    APIKeyAuthMiddleware,
    OriginCheckMiddleware,
    RequestMetricsMiddleware,
    SecurityHeadersMiddleware,
)
from app.db.session import init_db

configure_logging("DEBUG" if settings.DEBUG else "INFO")
logger = get_logger("veriunlearn.main")

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    logger.info("%s starting (env=%s)", settings.APP_NAME, settings.ENV)
    yield
    logger.info("%s stopped", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Verifiable Machine Unlearning Framework for Privacy-Compliant AI. "
        "Implements SISA, influence functions, certified removal, Merkle-tree "
        "deletion proofs, signed certificates, and an immutable audit trail for "
        "GDPR Article 17 / DPDP Act 2023 compliance."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Phase 7 middleware (order matters: innermost runs last — security headers
# wrap the request, origin/API-key checks run before the route, metrics wrap
# everything).
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(OriginCheckMiddleware)
app.add_middleware(RequestMetricsMiddleware)
app.add_middleware(APIKeyAuthMiddleware)

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.middleware("http")
async def request_logging(request: Request, call_next) -> Response:
    logger.info("request", extra={"method": request.method, "path": request.url.path})
    response = await call_next(request)
    return response


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "service": settings.APP_NAME, "version": "1.0.0"}


@app.get("/metrics", tags=["meta"])
async def metrics(
    authorization: str | None = Header(default=None),
) -> Response:
    """Prometheus scrape endpoint (Phase 7). Optional bearer-token protection."""
    if settings.METRICS_TOKEN and authorization != f"Bearer {settings.METRICS_TOKEN}":
        return JSONResponse(status_code=401, content={"error": "unauthorized", "message": "metrics token required"})
    try:
        from app.db.session import session_factory
        from app.services.metrics import render_metrics, update_system_gauges
        from app.services.monitoring import MonitoringService

        async with session_factory() as session:
            snapshot = await MonitoringService(session).snapshot(persist=False)
        update_system_gauges(snapshot)
    except Exception:
        logger.exception("metrics scrape failed")
    return Response(content=render_metrics(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "service": settings.APP_NAME,
        "docs": "/docs",
        "api": settings.API_V1_PREFIX,
    }
