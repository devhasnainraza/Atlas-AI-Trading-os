"""Correlation ID middleware (FR-034): accept or mint an ID at the edge, bind it to the
request context, and echo it on the response."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from atlas_core.correlation import CORRELATION_HEADER, new_correlation_id, set_correlation_id


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get(CORRELATION_HEADER)
        correlation_id = (
            incoming if incoming and _looks_like_uuid(incoming) else new_correlation_id()
        )
        set_correlation_id(correlation_id)
        request.state.correlation_id = correlation_id
        request.state.request_id = str(uuid.uuid4())

        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = correlation_id
        return response


def _looks_like_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False
