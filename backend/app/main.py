"""VeriUnlearn API — verifiable machine unlearning for GDPR/DPDP compliance."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
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
    version="0.1.0",
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

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.middleware("http")
async def request_logging(request: Request, call_next) -> Response:
    logger.info("request", extra={"method": request.method, "path": request.url.path})
    response = await call_next(request)
    return response


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "service": settings.APP_NAME, "version": "0.1.0"}


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "service": settings.APP_NAME,
        "docs": "/docs",
        "api": settings.API_V1_PREFIX,
    }
