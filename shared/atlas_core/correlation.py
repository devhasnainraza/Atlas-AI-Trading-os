"""Correlation ID propagation (Spec 00 FR-034).

A correlation ID is generated at the edge (or accepted from trusted callers), stored in a
context variable, and stamped onto every log line, event envelope, and background task the
request triggers. Ordering never depends on wall clocks — the ID is the join key.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

_correlation_id: ContextVar[str | None] = ContextVar("atlas_correlation_id", default=None)

CORRELATION_HEADER = "X-Correlation-ID"


def new_correlation_id() -> str:
    return str(uuid.uuid4())


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


def get_correlation_id() -> str:
    """Return the current correlation ID, creating one if none is bound yet."""
    value = _correlation_id.get()
    if value is None:
        value = new_correlation_id()
        _correlation_id.set(value)
    return value


def clear_correlation_id() -> None:
    _correlation_id.set(None)
