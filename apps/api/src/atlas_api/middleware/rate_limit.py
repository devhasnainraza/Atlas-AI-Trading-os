"""Per-client rate limiting (FR-011/020-adjacent; plan §8).

In-memory sliding window keyed by client IP — the reference implementation for local and
tests. The Redis-backed limiter implements the same middleware contract in deployed
environments so one abusive client cannot degrade others (spec edge case).
Health endpoints are exempt so probes never throttle.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from atlas_core.correlation import get_correlation_id

_EXEMPT_PREFIXES = ("/v1/health", "/openapi.json", "/docs")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 120) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith(_EXEMPT_PREFIXES):
            return await call_next(request)

        client_key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._windows[client_key]
        cutoff = now - 60.0
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= self.requests_per_minute:
            retry_after = max(1, int(window[0] - cutoff))
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "ATLAS-RL-001",
                        "message": "Too many requests. Please retry later.",
                        "correlation_id": get_correlation_id(),
                    }
                },
                headers={"Retry-After": str(retry_after)},
            )

        window.append(now)
        return await call_next(request)
