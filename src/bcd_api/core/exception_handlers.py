"""Custom FastAPI exception handlers."""

import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from src.bcd_api.core.exceptions import BCDException

logger = logging.getLogger(__name__)


def register_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on the FastAPI app."""
    app.add_exception_handler(BCDException, bcd_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)


async def bcd_exception_handler(request: Request, exc: BCDException) -> JSONResponse:
    """Handle custom BCD exceptions with error codes and context."""
    logger.warning(f"BCD Exception: {exc.detail} - {getattr(exc, 'error_code', 'UNKNOWN_ERROR')}")
    content = {
        "success": False,
        "error": exc.detail,
        "error_code": getattr(exc, "error_code", "UNKNOWN_ERROR"),
        "context": getattr(exc, "context", {}),
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation error",
            "details": exc.errors(),
        },
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Handle database integrity errors."""
    logger.error(f"Database integrity error: {exc.orig}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "success": False,
            "error": "Database integrity error",
            "details": str(exc.orig),
        },
    )
