from fastapi import FastAPI
from app.core.config import settings
from app.core.database import db
from app.core.cache import cache
from app.core.logging import logger_manager
from app.core.logging import get_logger

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

    await cache.initialize()
    logger.info("Redis cache connection established")


async def shutdown_event(app: FastAPI) -> None:
    logger.info("Shutting down VeriUnlearn")

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
