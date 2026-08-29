"""Redaction for venue traffic before it is stored or logged (Spec 03 plan §13, T023).

Venue payloads carry credential material in predictable places: an OANDA bearer token in a
request header, a Binance ``signature`` query parameter, an MT5 password in a login call. We
keep venue messages for 30 days for support and reconciliation, so they must be scrubbed on
the way *in* — a redaction applied at display time is one forgotten code path away from
leaking a live key into a log aggregator.

The complement to this module is the guard test (T028) asserting that no API response, event
payload, or audit entry can carry credential material.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "[REDACTED]"

# Matched case-insensitively against key names, as substrings: "X-MBX-APIKEY" hits "apikey".
_SENSITIVE_KEY_PARTS: tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "token",
    "apikey",
    "api_key",
    "api-key",
    "credential",
    "signature",
    "authorization",
    "auth",
    "private",
    "passphrase",
    "session",
    "cookie",
    "bearer",
    "access_key",
    "secret_key",
    "refresh",
    "otp",
    "mfa",
)

# Value-shaped matches for material that appears without a helpful key name.
_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    re.compile(r"\b[0-9a-fA-F]{64}\b"),  # Binance/Bybit HMAC signatures
    re.compile(r"\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),  # JWT
    re.compile(r"(?i)\b(?:api[_-]?key|secret|token)\s*[=:]\s*[^\s,;&\"']+"),
)

_MAX_DEPTH = 12


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SENSITIVE_KEY_PARTS)


def redact_text(value: str) -> str:
    """Scrub secret-shaped substrings from free text (venue error strings, URLs)."""
    for pattern in _VALUE_PATTERNS:
        value = pattern.sub(REDACTED, value)
    return value


def redact(value: Any, *, _depth: int = 0) -> Any:
    """Recursively redact a payload before it is persisted, logged, or emitted.

    Sensitive keys have their values replaced wholesale; remaining strings are scanned for
    secret-shaped content. Depth is bounded so a cyclic or pathological payload cannot hang
    the caller — beyond the limit the subtree is dropped rather than half-scrubbed.
    """
    if _depth > _MAX_DEPTH:
        return REDACTED
    if isinstance(value, Mapping):
        return {
            key: (REDACTED if is_sensitive_key(str(key)) else redact(item, _depth=_depth + 1))
            for key, item in value.items()
        }
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, bytes):
        return REDACTED
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [redact(item, _depth=_depth + 1) for item in value]
    return value


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {key: (REDACTED if is_sensitive_key(key) else value) for key, value in headers.items()}


def redact_url(url: str) -> str:
    """Strip credential-bearing query parameters, preserving the rest of the URL for support."""
    if "?" not in url:
        return redact_text(url)
    base, _, query = url.partition("?")
    parts = []
    for pair in query.split("&"):
        key, sep, _ = pair.partition("=")
        parts.append(f"{key}={REDACTED}" if sep and is_sensitive_key(key) else pair)
    return redact_text(f"{base}?{'&'.join(parts)}")


def contains_secret_marker(value: Any) -> bool:
    """Whether a payload still looks like it holds credential material.

    Used by the guard test and by defensive assertions on the event-publish path.
    """
    if isinstance(value, Mapping):
        return any(
            is_sensitive_key(str(key)) and item != REDACTED or contains_secret_marker(item)
            for key, item in value.items()
        )
    if isinstance(value, str):
        return any(pattern.search(value) for pattern in _VALUE_PATTERNS)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(contains_secret_marker(item) for item in value)
    return False


__all__ = [
    "REDACTED",
    "contains_secret_marker",
    "is_sensitive_key",
    "redact",
    "redact_headers",
    "redact_text",
    "redact_url",
]
