from fastapi import FastAPI

from app.core.cache import cache
from app.core.config import settings
from app.core.database import db
from app.core.logging import get_logger, logger_manager

logger = get_logger(__name__)


async def startup_event(app: FastAPI) -> None:
    logger_manager.initialize()
    logger.info(
        "Starting VeriUnlearn",
        extra={
            "environment": settings.environment.value,
            "version": settings.version,
            "debug": settings.debug,
        },
    )

    await db.initialize()
    logger.info("Database connection established")

    if settings.database_url.startswith("sqlite"):
        from app.core.database import Base
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLite database tables created/verified")

    await cache.initialize()
    logger.info("Redis cache connection established")


async def shutdown_event(app: FastAPI) -> None:
    logger.info("Shutting down VeriUnlearn")

    try:
        from app.infrastructure.external.ml_engine import ml_engine_client
        await ml_engine_client.aclose()
        logger.info("ML Engine HTTP clients closed")
    except Exception:
        logger.warning("Failed to close ML Engine HTTP clients", exc_info=True)

    await cache.close()
    await db.close()
    logger.info("Connections closed")


def register_lifespan_events(app: FastAPI) -> None:
    @app.on_event("startup")
    async def on_startup() -> None:
        await startup_event(app)

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        await shutdown_event(app)
