from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

import sqlalchemy

from app.core.config import settings
from app.core.events import register_lifespan_events
from app.core.exception_handlers import register_error_handlers
from app.core.middleware import setup_middleware
from app.api.v1 import router as api_v1_router

from app.core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.events import startup_event, shutdown_event
    await startup_event(app)
    yield
    await shutdown_event(app)


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Verifiable Machine Unlearning Framework with Cryptographic Proofs for GDPR-Compliant AI Systems",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
    contact={
        "name": "VeriUnlearn Team",
        "email": "team@veriunlearn.com",
        "url": "https://veriunlearn.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0",
    },
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

allowed_hosts = settings.allowed_hosts_list if settings.allowed_hosts else (["*"] if settings.debug else [settings.domain])
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts,
)


register_error_handlers(app)
setup_middleware(app)


app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    import time
    from app.core.cache import cache
    from app.core.database import db
    from datetime import datetime, timezone

    health_status = {
        "status": "healthy",
        "version": settings.version,
        "environment": settings.environment.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {},
    }

    db_start = time.perf_counter()
    try:
        async with db.session_factory() as session:
            await session.execute(
                sqlalchemy.text("SELECT 1")
            )
        db_latency = round((time.perf_counter() - db_start) * 1000, 2)
        health_status["components"]["database"] = {
            "status": "healthy",
            "latency_ms": db_latency,
        }
    except Exception:
        logger.warning("Health check: database unhealthy")
        health_status["components"]["database"] = {
            "status": "unhealthy",
        }
        health_status["status"] = "degraded"

    cache_start = time.perf_counter()
    try:
        await cache.redis.ping()
        cache_latency = round((time.perf_counter() - cache_start) * 1000, 2)
        health_status["components"]["cache"] = {
            "status": "healthy",
            "latency_ms": cache_latency,
        }
    except Exception:
        logger.warning("Health check: cache unhealthy")
        health_status["components"]["cache"] = {
            "status": "unhealthy",
        }
        health_status["status"] = "degraded"

    ml_start = time.perf_counter()
    try:
        from app.infrastructure.external.ml_engine import ml_engine_client
        ml_health = await ml_engine_client.health()
        ml_latency = round((time.perf_counter() - ml_start) * 1000, 2)
        health_status["components"]["ml_engine"] = {
            "status": "healthy" if ml_health.get("status") == "healthy" else "degraded",
            "latency_ms": ml_latency,
            "algorithms": ml_health.get("algorithms", []),
        }
    except Exception:
        logger.warning("Health check: ml_engine unhealthy")
        health_status["components"]["ml_engine"] = {
            "status": "unhealthy",
        }
        health_status["status"] = "degraded"

    return health_status


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    from app.core.database import db

    try:
        async with db.session_factory() as session:
            await session.execute(sqlalchemy.text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.warning("Readiness check failed: %s", e)
        from fastapi.responses import JSONResponse
        return JSONResponse({"status": "not_ready"}, status_code=503)


@app.get("/health/live", tags=["Health"])
async def liveness_check():
    return {"status": "alive"}


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.app_name,
        "version": settings.version,
        "docs": "/docs" if settings.debug else None,
    }
