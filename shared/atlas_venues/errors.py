"""Venue error classification (Spec 03 plan §17, research §7).

Every exception raised by every adapter is mapped to exactly one :class:`ErrorClass` by that
adapter's ``classify_error``. Callers branch on the *class*, never on a venue's error string
or HTTP status, so retry policy is uniform across MT5, OANDA, Binance, Bybit, and IBKR.

The critical member is :attr:`ErrorClass.AMBIGUOUS`: a timeout or dropped connection during
submission does not tell us whether the venue accepted the order. Ambiguous errors must move
the order to ``unresolved`` and stop — they are never retried automatically (FR-030).
"""

from __future__ import annotations

from enum import StrEnum


class ErrorClass(StrEnum):
    RETRYABLE_TRANSIENT = "retryable_transient"
    RATE_LIMITED = "rate_limited"
    TERMINAL_REJECTION = "terminal_rejection"
    PERMISSION_DENIED = "permission_denied"
    AMBIGUOUS = "ambiguous"

    @property
    def is_retryable(self) -> bool:
        """Whether a caller may safely re-issue the same call.

        ``AMBIGUOUS`` is deliberately excluded: re-issuing a submission whose outcome is
        unknown is exactly how duplicate orders reach a venue.
        """
        return self in (ErrorClass.RETRYABLE_TRANSIENT, ErrorClass.RATE_LIMITED)


class VenueError(Exception):
    """Base class for adapter failures, carrying its classification.

    ``venue_message`` holds the venue's own wording for the audit trail. It is redacted
    before storage or logging by :mod:`atlas_venues.redaction`; adapters must never place
    credential material in it.
    """

    error_class: ErrorClass = ErrorClass.TERMINAL_REJECTION

    def __init__(
        self,
        message: str,
        *,
        venue_code: str | None = None,
        venue_message: str | None = None,
        venue_error_code: str | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.venue_code = venue_code
        self.venue_message = venue_message
        self.venue_error_code = venue_error_code
        self.retry_after_seconds = retry_after_seconds

    def __str__(self) -> str:
        prefix = f"[{self.venue_code}] " if self.venue_code else ""
        return f"{prefix}{self.message} ({self.error_class})"


class TransientVenueError(VenueError):
    """A network blip or venue-side 5xx on a call known not to have taken effect."""

    error_class = ErrorClass.RETRYABLE_TRANSIENT


class RateLimitedError(VenueError):
    """The venue refused the call for quota reasons; honour ``retry_after_seconds``."""

    error_class = ErrorClass.RATE_LIMITED


class TerminalRejectionError(VenueError):
    """The venue understood the request and refused it. Retrying changes nothing."""

    error_class = ErrorClass.TERMINAL_REJECTION


class PermissionDeniedError(VenueError):
    """Credentials are invalid, expired, or lack the scope for this operation."""

    error_class = ErrorClass.PERMISSION_DENIED


class AmbiguousOutcomeError(VenueError):
    """The call's effect at the venue is unknown — never retry, escalate to ``unresolved``."""

    error_class = ErrorClass.AMBIGUOUS


class UnsupportedCapabilityError(VenueError):
    """The adapter does not support the requested operation for this venue."""

    error_class = ErrorClass.TERMINAL_REJECTION


__all__ = [
    "AmbiguousOutcomeError",
    "ErrorClass",
    "PermissionDeniedError",
    "RateLimitedError",
    "TerminalRejectionError",
    "TransientVenueError",
    "UnsupportedCapabilityError",
    "VenueError",
]
