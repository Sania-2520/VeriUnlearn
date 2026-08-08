"""FastAPI application for the VeriUnlearn ML Engine.

This package replaces the historical ``api.py`` monolith. The public entry
point is unchanged: ``uvicorn api:app`` and ``from api import app`` keep
working. Endpoint paths, request/response schemas, and behaviour are identical;
only the code organisation changed (routers now live in :mod:`api.routers`).
"""

import contextlib
import hmac
import logging
import os
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from api import deps
from api.routers import (
    adapters,
    attacks,
    benchmarks,
    continual,
    conversations,
    explainability,
    inference,
    rag,
    registry,
    training,
    unlearning,
    verification,
)
from security.input_validator import ValidationError as InputValidationError

logger = logging.getLogger("veriunlearn.ml_engine")

# SECURITY: An empty string means authentication is silently bypassed at
# runtime. The lifespan handler below refuses to start if this key is not
# configured, so the service fails closed at boot rather than at request time.
ML_API_KEY = os.getenv("ML_ENGINE_API_KEY", "")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if not ML_API_KEY:
        logger.critical(
            "ML_ENGINE_API_KEY is not set or is empty — authentication is DISABLED. "
            "All requests will be accepted without verification. "
            "Set a strong API key via the ML_ENGINE_API_KEY environment variable before deploying."
        )
        raise SystemExit(1)
    try:
        yield
    finally:
        _shutdown_runtime()


def _shutdown_runtime() -> None:
    """Release long-lived runtime resources on app shutdown."""
    external = deps.get_gpu_scheduler()
    if external is not None:
        try:
            external.stop()
        except Exception:  # pragma: no cover - defensive shutdown path
            logger.exception("Failed to stop GPU scheduler during shutdown")


app = FastAPI(
    title="VeriUnlearn ML Engine",
    version="1.0.0",
    description="Machine Unlearning, Verification, and Security Engine",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ML_ENGINE_CORS_ORIGINS", "http://localhost:8000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)


@app.exception_handler(InputValidationError)
async def input_validation_error_handler(
    request: Request, exc: InputValidationError
) -> JSONResponse:
    """Map adversarial/oversized inputs to a clean HTTP 422 instead of a 500.

    Rejections are logged (request path + reason) so attack traffic is visible
    in the observability pipeline, not silently dropped.
    """
    logger.warning(
        "Rejected invalid input on %s: %s", request.url.path, exc
    )
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.middleware("http")
async def authenticate_ml_engine(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    if ML_API_KEY:
        api_key = request.headers.get("X-API-Key", "")
        # Constant-time comparison prevents timing side-channel attacks on the
        # shared service key (HMAC comparison runs in time proportional to the
        # digest length, not the match prefix).
        if not hmac.compare_digest(api_key, ML_API_KEY):
            return Response(status_code=401, content='{"detail":"Unauthorized"}', media_type="application/json")
    return await call_next(request)


for _router in (
    unlearning.router,
    verification.router,
    adapters.router,
    registry.router,
    inference.router,
    rag.router,
    conversations.router,
    continual.router,
    training.router,
    benchmarks.router,
    explainability.router,
    attacks.router,
):
    app.include_router(_router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "engine": "veriunlearn-ml",
        "version": "1.0.0",
        "algorithms": list(deps.controller.algorithms.keys()),
        "components": deps.component_status(),
    }


@app.get("/health/live")
async def health_live():
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready():
    ready = deps.readiness_status()
    status_code = 200 if all(ready.values()) else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if status_code == 200 else "not_ready", "components": ready},
    )
