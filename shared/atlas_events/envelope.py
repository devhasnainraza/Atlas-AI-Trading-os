"""Event envelope v1 (Spec 00 FR-015; contracts/platform-events.md)."""

from __future__ import annotations

import os
import threading
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from atlas_core.correlation import get_correlation_id

_last_id_lock = threading.Lock()
_last_id_value = 0


def new_event_id() -> str:
    """UUIDv7-style identifier: 48-bit unix-ms timestamp + random tail, strictly
    monotonic within this process.

    Time-ordered IDs keep event stores index-friendly. Random tails alone do not sort
    within the same millisecond, so a process-local guard bumps the value when needed —
    the same technique RFC 9562 suggests via counters.
    """
    global _last_id_value
    ts_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand = int.from_bytes(os.urandom(10), "big")
    value = (ts_ms << 80) | (0x7 << 76) | (rand & ((1 << 76) - 1))
    with _last_id_lock:
        if value <= _last_id_value:
            value = _last_id_value + 1
        _last_id_value = value
    return str(uuid.UUID(int=value))


class EventEnvelope(BaseModel):
    """Immutable record of something that happened."""

    event_id: str = Field(default_factory=new_event_id)
    event_type: str
    schema_version: str = "1.0.0"
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str = Field(default_factory=get_correlation_id)
    causation_id: str | None = None
    producer: str = "unknown"
    replay_of: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_replay(self) -> bool:
        return self.replay_of is not None

    def as_replay(self) -> EventEnvelope:
        """A copy marked as a replay of this event (new delivery, same identity trail)."""
        return self.model_copy(update={"replay_of": self.event_id})
