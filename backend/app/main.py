from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1 import auth, chat, training, unlearning, documents, admin, api_keys, gdpr, usage, webhooks, backup, registry, experiments
from app.middleware.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(f"VeriUnlearn Pro starting (env={settings.app_env})")
    yield
    logger.info("VeriUnlearn Pro shutting down")


app = FastAPI(
    title="VeriUnlearn Pro API",
    description=(
        "An End-to-End Framework for Verifiable Machine Unlearning with Cryptographic Proofs.\n\n"
        "## Features\n"
        "- **Conversational AI** with RAG retrieval and streaming\n"
        "- **Real LoRA Training** with dataset management\n"
        "- **7 Unlearning Algorithms** with adaptive selection\n"
        "- **Cryptographic Proofs** (Merkle tree, Ed25519 signatures)\n"
        "- **GDPR Compliance** (data export, account deletion)\n"
        "- **RBAC** (admin, user, auditor roles)\n"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    openapi_tags=[
        {"name": "Auth", "description": "Authentication and user management"},
        {"name": "Chat", "description": "Conversational AI with RAG"},
        {"name": "Training", "description": "Dataset management and model training"},
        {"name": "Unlearning", "description": "Machine unlearning with verification"},
        {"name": "Documents", "description": "Document upload and RAG indexing"},
        {"name": "Admin", "description": "Admin panel and user management"},
        {"name": "API Keys", "description": "API key management"},
        {"name": "GDPR", "description": "Data export and deletion rights"},
        {"name": "Usage", "description": "Usage quotas and limits"},
        {"name": "Webhooks", "description": "Event notifications"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)


@app.middleware("http")
async def add_version_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-API-Version"] = "1.0.0"
    response.headers["X-API-Deprecated"] = "false"
    return response

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "veriunlearn", "version": "1.0.0"}


app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(training.router, prefix="/api/v1")
app.include_router(unlearning.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(api_keys.router, prefix="/api/v1")
app.include_router(gdpr.router, prefix="/api/v1")
app.include_router(usage.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(backup.router, prefix="/api/v1")
app.include_router(registry.router, prefix="/api/v1")
app.include_router(experiments.router, prefix="/api/v1")
