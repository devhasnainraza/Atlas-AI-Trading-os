"""Freshness policy — the settings-driven version of the venue-layer defaults (FR-018, FR-039).

:func:`atlas_venues.timing.classify_freshness` carries library defaults so adapter code can
classify without a config object. Inside the API the *configured* limits win, because a venue
with a genuinely slower feed needs a wider window and hardcoding would force a code change to
accommodate one.

The classification is binary on purpose. There is no "probably fine": either the quote is
inside its window and may price an order, or it is not and the gate refuses. A third state
would inevitably be treated as usable by someone.
"""

from __future__ import annotations

from dataclasses import dataclass

from atlas_venues.enums import DataFreshness


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    """Per-asset-class staleness thresholds, in seconds."""

    crypto_seconds: float
    forex_seconds: float
    equity_seconds: float
    default_seconds: float

    def __post_init__(self) -> None:
        for name in ("crypto_seconds", "forex_seconds", "equity_seconds", "default_seconds"):
            value = getattr(self, name)
            if not isinstance(value, int | float) or isinstance(value, bool):
                raise TypeError(f"{name} must be a number")
            if value <= 0:
                # A zero or negative limit would mark every quote stale the instant it
                # arrived, halting all trading — a config typo should not be able to do that
                # silently.
                raise ValueError(f"{name} must be positive, got {value}")

    def limit_for(self, asset_class: str) -> float:
        """Threshold for an asset class; anything unlisted gets the default."""
        return {
            "crypto": self.crypto_seconds,
            "forex": self.forex_seconds,
            "equity": self.equity_seconds,
        }.get(asset_class.lower(), self.default_seconds)

    def classify(self, age_seconds: float, asset_class: str) -> DataFreshness:
        """Classify an age. The boundary is inclusive: exactly-at-limit is still fresh.

        A negative age means the quote is stamped in the future — clock skew, not freshness.
        It is treated as stale rather than as maximally fresh, because a venue timestamp we
        cannot reconcile with our own clock is precisely the input we should not trust.
        """
        if age_seconds < 0:
            return DataFreshness.STALE
        return (
            DataFreshness.FRESH
            if age_seconds <= self.limit_for(asset_class)
            else DataFreshness.STALE
        )

    def usable_for_pricing(self, age_seconds: float, asset_class: str) -> bool:
        return self.classify(age_seconds, asset_class) is DataFreshness.FRESH


__all__ = ["FreshnessPolicy"]
