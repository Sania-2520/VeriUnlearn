import logging
import re
import sys
from typing import Any

from pythonjsonlogger import jsonlogger

from app.core.config import settings

RESERVED_ATTRS = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "module", "msecs",
    "message", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName", "taskName",
}

_SENSITIVE_PATTERNS = [
    (re.compile(r'(?i)(password|passwd|pwd)\s*[:=]\s*\S+'), r'\1=[REDACTED]'),
    (re.compile(r'(?i)(secret|token|api_key|apikey|auth[_-]?key)\s*[:=]\s*\S+'), r'\1=[REDACTED]'),
    (re.compile(r'(?i)(authorization|bearer)\s+\S+'), r'\1 [REDACTED]'),
    (re.compile(r'(?i)(x-api-key)\s*:\s*\S+'), r'\1: [REDACTED]'),
]


def _redact_sensitive(text: str) -> str:
    for pattern, replacement in _SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class SafeJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record: dict[str, Any], record: logging.LogRecord, message_dict: dict[str, Any]) -> None:
        for field in list(message_dict.keys()):
            if field in RESERVED_ATTRS:
                log_record[f"extra_{field}"] = message_dict.pop(field)
        for key, value in list(message_dict.items()):
            if isinstance(value, str):
                message_dict[key] = _redact_sensitive(value)
        for key, value in list(log_record.items()):
            if isinstance(value, str):
                log_record[key] = _redact_sensitive(value)
        super().add_fields(log_record, record, message_dict)


class LoggerManager:
    _initialized: bool = False

    def initialize(self) -> None:
        if self._initialized:
            return

        handler = logging.StreamHandler(sys.stdout)
        formatter = SafeJsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s %(module)s %(funcName)s %(lineno)d",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(settings.log_level.value)

        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("redis.asyncio").setLevel(logging.WARNING)

        self._initialized = True

    def get_logger(self, name: str) -> logging.Logger:
        return logging.getLogger(name)


logger_manager = LoggerManager()


def get_logger(name: str) -> logging.Logger:
    return logger_manager.get_logger(name)
