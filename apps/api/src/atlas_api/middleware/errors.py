"""Error handling (FR-038/039): every failure becomes the standard envelope; internals are
logged server-side and never serialized to clients."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from atlas_core.correlation import get_correlation_id
from atlas_core.errors import AtlasError, RateLimitedError
from atlas_observability import get_logger

logger = get_logger("atlas_api.errors")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AtlasError)
    async def atlas_error_handler(request: Request, exc: AtlasError) -> JSONResponse:
        correlation_id = get_correlation_id()
        if exc.http_status >= 500:
            logger.error(
                "request_failed",
                code=exc.code,
                path=request.url.path,
                internal=exc.internal_context,
            )
        headers = {}
        if isinstance(exc, RateLimitedError):
            headers["Retry-After"] = str(exc.retry_after_seconds)
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_envelope(correlation_id),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {"field": ".".join(str(part) for part in err["loc"]), "issue": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "ATLAS-VAL-001",
                    "message": "The request is invalid.",
                    "correlation_id": get_correlation_id(),
                    "details": details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "ATLAS-INT-001",
                    "message": "An internal error occurred.",
                    "correlation_id": get_correlation_id(),
                }
            },
        )
