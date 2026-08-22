"""Platform error taxonomy (Spec 00 FR-038/039).

Every service returns errors in one envelope with a stable machine code. Internal detail
never crosses the API boundary — the middleware maps exceptions to envelopes and logs the
full context server-side only.
"""

from __future__ import annotations

from typing import Any


class AtlasError(Exception):
    """Base class for all platform errors.

    Subclasses define a stable ``code`` (never renumbered) and the HTTP status they map
    to. ``message`` must always be user-safe; put internals in ``internal_context`` which
    is logged but never serialized to clients.
    """

    code: str = "ATLAS-INT-001"
    http_status: int = 500
    default_message: str = "An internal error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: list[dict[str, Any]] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or []
        self.internal_context = internal_context or {}
        super().__init__(self.message)

    def to_envelope(self, correlation_id: str) -> dict[str, Any]:
        error: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "correlation_id": correlation_id,
        }
        if self.details:
            error["details"] = self.details
        return {"error": error}


class ValidationError(AtlasError):
    code = "ATLAS-VAL-001"
    http_status = 422
    default_message = "The request is invalid."


class AuthenticationError(AtlasError):
    code = "ATLAS-AUTHN-001"
    http_status = 401
    default_message = "Authentication required."


class AuthorizationError(AtlasError):
    code = "ATLAS-AUTHZ-001"
    http_status = 403
    default_message = "You do not have permission to perform this action."


class NotFoundError(AtlasError):
    code = "ATLAS-NF-001"
    http_status = 404
    default_message = "The requested resource was not found."


class ConflictError(AtlasError):
    code = "ATLAS-CON-001"
    http_status = 409
    default_message = "The request conflicts with the current state."


class RateLimitedError(AtlasError):
    code = "ATLAS-RL-001"
    http_status = 429
    default_message = "Too many requests. Please retry later."

    def __init__(self, message: str | None = None, *, retry_after_seconds: int = 60, **kw: Any):
        super().__init__(message, **kw)
        self.retry_after_seconds = retry_after_seconds


class DependencyUnavailableError(AtlasError):
    code = "ATLAS-DEP-001"
    http_status = 503
    default_message = "A required dependency is temporarily unavailable."


class InternalError(AtlasError):
    code = "ATLAS-INT-001"
    http_status = 500
    default_message = "An internal error occurred."
