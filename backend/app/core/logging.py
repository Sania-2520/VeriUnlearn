from __future__ import annotations

import logging
import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def setup_logging() -> None:
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.remove()
    logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG" if settings.app_debug else "INFO",
        colorize=True,
    )
    logger.add(
        Path("logs") / "veriunlearn.log",
        format=log_format,
        level="INFO",
        rotation="10 MB",
        retention="30 days",
        compression="gz",
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)

    for logger_name in ("uvicorn", "uvicorn.access", "fastapi", "sqlalchemy.engine"):
        logging.getLogger(logger_name).handlers = [InterceptHandler()]
        logging.getLogger(logger_name).propagate = False
