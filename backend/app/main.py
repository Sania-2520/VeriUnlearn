from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1 import auth, chat, training, unlearning, documents, admin, api_keys


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(f"VeriUnlearn Pro starting (env={settings.app_env})")
    yield
    logger.info("VeriUnlearn Pro shutting down")


app = FastAPI(
    title="VeriUnlearn Pro API",
    description="An End-to-End Framework for Verifiable Machine Unlearning with Cryptographic Proofs",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
