"""Trading error taxonomy (plan §17, T026).

These extend the Spec 00 envelope, so the existing ``AtlasError`` handler in
:mod:`atlas_api.middleware.errors` serializes them without any new handler — a new code is
purely additive.

Two rules hold throughout:

* ``message`` is always user-safe. Venue text reaches the client only after passing through
  :func:`atlas_venues.redaction.redact_text`, and raw venue payloads, credentials, internal
  hostnames, and stack traces never appear (FR-032, FR-057).
* Codes are never renumbered. A retired code stays retired.

:class:`OutcomeUnresolvedError` is the load-bearing one. It is *not* a 500 and *not*
retryable: it means the order may or may not exist at the venue, and the only correct next
step is reconciliation, never a resubmission (FR-030).
"""

from __future__ import annotations

from typing import Any

from atlas_core.errors import AtlasError

# -- Connection and instrument ---------------------------------------------------------------


class ConnectionUnavailableError(AtlasError):
    """ATLAS-TRD-001 — the venue connection is unhealthy, quarantined, or disconnected."""

    code = "ATLAS-TRD-001"
    http_status = 409
    default_message = "The venue connection is unavailable. Check its health and reconnect."


class CapabilityNotPermittedError(AtlasError):
    """ATLAS-TRD-002 — the venue or the credential does not grant this operation.

    Distinct from an authorization failure: the *user* may be permitted while the credential
    is read-only, or the venue simply has no such capability (FR-005).
    """

    code = "ATLAS-TRD-002"
    http_status = 422
    default_message = "This venue connection does not permit that operation."


class InstrumentNotTradableError(AtlasError):
    """ATLAS-TRD-003 — instrument is halted, delisted, or its session is closed."""

    code = "ATLAS-TRD-003"
    http_status = 422
    default_message = "That instrument cannot be traded right now."


class InvalidQuantityError(AtlasError):
    """ATLAS-TRD-004 — quantity or price violates the venue's step, tick, or bounds."""

    code = "ATLAS-TRD-004"
    http_status = 422
    default_message = "The quantity or price does not match the instrument's requirements."


# -- Data and intent lifecycle ---------------------------------------------------------------


class StaleMarketDataError(AtlasError):
    """ATLAS-TRD-005 — no quote fresh enough to price or size the order.

    Refusing is the feature: an order valued against a stale price is an unmeasured risk, so
    the gate declines rather than guessing (FR-039).
    """

    code = "ATLAS-TRD-005"
    http_status = 409
    default_message = "Market data is not fresh enough to price this order. Please wait."


class IntentExpiredError(AtlasError):
    """ATLAS-TRD-006 — the intent's TTL elapsed, or its terms were invalidated.

    A confirmation must authorize the order the user actually reviewed. If the price, the
    account, or the instrument spec moved, the intent dies and a new one is required (FR-025).
    """

    code = "ATLAS-TRD-006"
    http_status = 409
    default_message = "This order intent is no longer valid. Please review and create a new one."


class DuplicateSubmissionError(AtlasError):
    """ATLAS-TRD-007 — a submission for this intent already exists.

    Raised by the pre-call submission ledger's uniqueness constraint. This is a *success* from
    the safety standpoint: the second confirm did not reach the venue (FR-026).
    """

    code = "ATLAS-TRD-007"
    http_status = 409
    default_message = "This order was already submitted. No duplicate was sent to the venue."


class OrderNotModifiableError(AtlasError):
    """ATLAS-TRD-008 — the order's state does not allow amend or cancel."""

    code = "ATLAS-TRD-008"
    http_status = 409
    default_message = "This order can no longer be amended or canceled."


# -- Venue outcomes --------------------------------------------------------------------------


class VenueRejectedError(AtlasError):
    """ATLAS-TRD-009 — the venue refused the order. Carries a sanitized venue reason."""

    code = "ATLAS-TRD-009"
    http_status = 422
    default_message = "The venue rejected this order."

    def __init__(
        self,
        message: str | None = None,
        *,
        error_class: str | None = None,
        venue_reason: str | None = None,
        **kw: Any,
    ) -> None:
        super().__init__(message, **kw)
        self.error_class = error_class
        self.venue_reason = venue_reason


class OutcomeUnresolvedError(AtlasError):
    """ATLAS-TRD-010 — we do not know whether the venue received the order.

    Deliberately *not* a 500 and deliberately *not* retryable. Automatic retry here is the
    textbook way to place a duplicate live order, so the order is parked in ``unresolved``
    and reconciliation against the venue — the only authority — decides the truth (FR-030).
    """

    code = "ATLAS-TRD-010"
    http_status = 409
    default_message = (
        "The outcome of this order is unknown. It is being checked against the venue; "
        "do not resubmit."
    )


class ReconciliationHoldError(AtlasError):
    """ATLAS-TRD-011 — an unresolved discrepancy holds routing for this connection.

    Trading on state we know to be wrong is worse than not trading (FR-053).
    """

    code = "ATLAS-TRD-011"
    http_status = 409
    default_message = "Trading is paused for this connection until a state discrepancy is resolved."


class VenueRateLimitedError(AtlasError):
    """ATLAS-TRD-012 — the venue throttled us.

    Separate from the platform's own ``ATLAS-RL-001`` so dashboards can tell "we are being
    limited by Binance" apart from "we are limiting this user".
    """

    code = "ATLAS-TRD-012"
    http_status = 429
    default_message = "The venue is rate limiting requests. Please retry shortly."

    def __init__(self, message: str | None = None, *, retry_after_seconds: int = 5, **kw: Any):
        super().__init__(message, **kw)
        self.retry_after_seconds = retry_after_seconds


# -- Risk ------------------------------------------------------------------------------------


class RiskLimitBreachedError(AtlasError):
    """ATLAS-RISK-001 — one or more risk rules failed.

    ``details`` carries the breached rules with their limit and observed values, because a
    refusal a user cannot understand is a refusal they will work around (Constitution V).
    """

    code = "ATLAS-RISK-001"
    http_status = 422
    default_message = "This order breaches your risk limits."


class KillSwitchEngagedError(AtlasError):
    """ATLAS-RISK-002 — trading is stopped for this scope. Nothing overrides it."""

    code = "ATLAS-RISK-002"
    http_status = 409
    default_message = "Trading is stopped by a kill switch."


class MandateExceededError(AtlasError):
    """ATLAS-RISK-003 — the automation mandate is expired, revoked, or out of allowance.

    The order is not blocked outright: a human can still confirm it. The mandate only ever
    removed the click, never a limit (FR-041).
    """

    code = "ATLAS-RISK-003"
    http_status = 422
    default_message = (
        "This order is outside the active automation mandate. Confirm it manually to proceed."
    )


class RiskInputsUnavailableError(AtlasError):
    """ATLAS-RISK-004 — a risk rule's input is missing or stale, so it cannot be evaluated.

    An unmeasurable risk is not an absent risk. The gate fails closed and recommends waiting
    rather than approving on incomplete information (FR-039).
    """

    code = "ATLAS-RISK-004"
    http_status = 409
    default_message = (
        "Risk cannot be evaluated right now because required data is unavailable. Please wait."
    )


#: Every code this module owns, for the taxonomy contract test.
TRADING_ERROR_CLASSES: tuple[type[AtlasError], ...] = (
    ConnectionUnavailableError,
    CapabilityNotPermittedError,
    InstrumentNotTradableError,
    InvalidQuantityError,
    StaleMarketDataError,
    IntentExpiredError,
    DuplicateSubmissionError,
    OrderNotModifiableError,
    VenueRejectedError,
    OutcomeUnresolvedError,
    ReconciliationHoldError,
    VenueRateLimitedError,
    RiskLimitBreachedError,
    KillSwitchEngagedError,
    MandateExceededError,
    RiskInputsUnavailableError,
)

__all__ = [
    "TRADING_ERROR_CLASSES",
    "CapabilityNotPermittedError",
    "ConnectionUnavailableError",
    "DuplicateSubmissionError",
    "InstrumentNotTradableError",
    "IntentExpiredError",
    "InvalidQuantityError",
    "KillSwitchEngagedError",
    "MandateExceededError",
    "OrderNotModifiableError",
    "OutcomeUnresolvedError",
    "ReconciliationHoldError",
    "RiskInputsUnavailableError",
    "RiskLimitBreachedError",
    "StaleMarketDataError",
    "VenueRateLimitedError",
    "VenueRejectedError",
]
