"""Event envelope v1 (Spec 00 FR-015; contracts/platform-events.md)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from atlas_core.correlation import get_correlation_id
from atlas_core.ids import uuid7_str


def new_event_id() -> str:
    """Time-ordered event identifier (UUIDv7).

    Delegates to ``atlas_core.ids`` so event ids and database primary keys share one
    implementation: two generators drifting apart is the kind of difference nobody notices
    until an id sorts wrong in a replay.
    """
    return uuid7_str()


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
