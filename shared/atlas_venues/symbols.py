"""Canonical symbol normalization across venues (Spec 03 plan §5, T011).

The same instrument is spelled differently everywhere: ``EURUSD`` at MT5, ``EUR_USD`` at
OANDA, ``BTCUSDT`` at Binance, ``BTC/USD`` in most UIs. Atlas stores both the venue's spelling
(what goes on the wire) and a canonical form (what the user sees and what cross-venue
comparison keys on).

Canonical form is ``BASE/QUOTE`` for pairs and the bare uppercase ticker otherwise. The rule
is deliberately mechanical rather than clever: a heuristic that guesses wrong pairs a user's
order with the wrong instrument, so unresolvable symbols keep their venue spelling and are
flagged instead of guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from atlas_venues.enums import AssetClass

# Quote currencies, longest first so "USDT" is tried before "USD" when splitting "BTCUSDT".
_QUOTE_CURRENCIES: tuple[str, ...] = (
    "USDT",
    "USDC",
    "TUSD",
    "BUSD",
    "FDUSD",
    "USD",
    "EUR",
    "GBP",
    "JPY",
    "CHF",
    "AUD",
    "CAD",
    "NZD",
    "BTC",
    "ETH",
    "BNB",
    "TRY",
    "BRL",
    "ZAR",
    "SEK",
    "NOK",
    "SGD",
    "HKD",
    "MXN",
    "PLN",
    "CNH",
)

# Venue suffixes that denote an account flavour, not a different instrument: "EURUSD.pro",
# "EURUSD.raw", "EURUSDm". Stripped so the same instrument compares equal across accounts.
_VENUE_SUFFIX_RE = re.compile(
    r"[._\-]?(pro|raw|ecn|micro|mini|cent|c|m|i|z|sb|\d)+$", re.IGNORECASE
)
_SEPARATORS = ("/", "_", "-", ".", ":")


@dataclass(frozen=True, slots=True)
class SymbolParts:
    canonical: str
    base: str | None
    quote: str | None
    resolved: bool

    @property
    def is_pair(self) -> bool:
        return self.base is not None and self.quote is not None


def normalize(
    venue_symbol: str,
    *,
    asset_class: AssetClass | None = None,
    base: str | None = None,
    quote: str | None = None,
) -> SymbolParts:
    """Derive the canonical form of a venue symbol.

    When the venue tells us the base and quote currencies (most do, in their instrument
    listing), those are used directly and nothing is inferred. Splitting is only attempted for
    venues that report a bare concatenated ticker.
    """
    raw = venue_symbol.strip().upper()
    if not raw:
        raise ValueError("venue_symbol must not be empty")

    if base and quote:
        return SymbolParts(f"{base.upper()}/{quote.upper()}", base.upper(), quote.upper(), True)

    # Strip the account-flavour suffix before looking for separators, otherwise "EURUSD.pro"
    # splits on its own suffix and yields "EURUSD/PRO".
    raw = _strip_suffix(raw)

    for sep in _SEPARATORS:
        if sep in raw:
            left, _, right = raw.partition(sep)
            right = _strip_suffix(right)
            if left and right:
                return SymbolParts(f"{left}/{right}", left, right, True)

    if asset_class in (AssetClass.EQUITY, AssetClass.INDEX, AssetClass.COMMODITY):
        return SymbolParts(raw, None, None, True)

    stripped = raw
    for quote_ccy in _QUOTE_CURRENCIES:
        if stripped.endswith(quote_ccy) and len(stripped) > len(quote_ccy):
            base_ccy = stripped[: -len(quote_ccy)]
            return SymbolParts(f"{base_ccy}/{quote_ccy}", base_ccy, quote_ccy, True)

    # Unresolvable: keep the venue spelling rather than invent a split. Callers surface this
    # as "venue symbol shown as-is" instead of silently mapping to the wrong instrument.
    return SymbolParts(stripped, None, None, False)


def canonical_symbol(
    venue_symbol: str,
    *,
    asset_class: AssetClass | None = None,
    base: str | None = None,
    quote: str | None = None,
) -> str:
    return normalize(venue_symbol, asset_class=asset_class, base=base, quote=quote).canonical


def _strip_suffix(value: str) -> str:
    stripped = _VENUE_SUFFIX_RE.sub("", value)
    # Never strip everything away, and never strip a plain currency code down to nothing.
    return stripped if len(stripped) >= 3 else value


def same_instrument(left: str, right: str) -> bool:
    """Whether two venue symbols denote the same instrument (best-effort, suffix-insensitive)."""
    return normalize(left).canonical == normalize(right).canonical


__all__ = ["SymbolParts", "canonical_symbol", "normalize", "same_instrument"]
