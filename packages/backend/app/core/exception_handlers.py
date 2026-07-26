from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.exceptions import VeriUnlearnError
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_error_response(
    code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    error_body: dict[str, Any] = {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
        },
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    if details:
        error_body["error"]["details"] = details
    if request_id:
        error_body["meta"]["request_id"] = request_id

    return JSONResponse(content=error_body, status_code=status_code)


async def veriunlearn_error_handler(
    request: Request,
    exc: VeriUnlearnError,
) -> JSONResponse:
    logger.warning(
        "Application error",
        extra={
            "code": exc.code,
            "error_message": exc.message,
            "status_code": exc.status_code,
            "path": request.url.path,
            "request_id": getattr(request.state, "request_id", None),
        },
    )
    return create_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        request_id=getattr(request.state, "request_id", None),
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "location": ".".join(str(loc) for loc in error.get("loc", [])),
                "message": error.get("msg", "Validation error"),
                "type": error.get("type", "unknown"),
            }
        )

    return create_error_response(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        status_code=422,
        details={"errors": errors},
        request_id=getattr(request.state, "request_id", None),
    )


async def pydantic_validation_error_handler(
    request: Request,
    exc: PydanticValidationError,
) -> JSONResponse:
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "location": ".".join(str(loc) for loc in error.get("loc", [])),
                "message": error.get("msg", "Validation error"),
                "type": error.get("type", "unknown"),
            }
        )

    return create_error_response(
        code="VALIDATION_ERROR",
        message="Data validation failed",
        status_code=422,
        details={"errors": errors},
        request_id=getattr(request.state, "request_id", None),
    )


async def generic_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.error(
        "Unhandled exception",
        extra={
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "path": request.url.path,
            "request_id": getattr(request.state, "request_id", None),
        },
        exc_info=True,
    )

    return create_error_response(
        code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        status_code=500,
        request_id=getattr(request.state, "request_id", None),
    )


async def not_found_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return create_error_response(
        code="NOT_FOUND",
        message="The requested resource was not found",
        status_code=404,
        request_id=getattr(request.state, "request_id", None),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(VeriUnlearnError, veriunlearn_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(PydanticValidationError, pydantic_validation_error_handler)
    app.add_exception_handler(404, not_found_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
