"""Event catalog (Spec 00 FR-019).

Every event type must be registered with its current schema version before first publish.
The catalog is the machine-readable twin of contracts/platform-events.md; CI compat checks
diff against it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from atlas_core.errors import ValidationError


@dataclass(frozen=True)
class EventTypeDef:
    event_type: str
    schema_version: str
    producer: str
    description: str
    required_payload_fields: tuple[str, ...] = field(default=())


class EventCatalog:
    def __init__(self) -> None:
        self._types: dict[str, EventTypeDef] = {}

    def register(self, definition: EventTypeDef) -> None:
        existing = self._types.get(definition.event_type)
        if existing and existing.schema_version != definition.schema_version:
            raise ValidationError(
                f"Event type '{definition.event_type}' already registered with a "
                f"different schema version; breaking changes require a new .v2 type."
            )
        self._types[definition.event_type] = definition

    def get(self, event_type: str) -> EventTypeDef:
        try:
            return self._types[event_type]
        except KeyError as exc:
            raise ValidationError(f"Unknown event type '{event_type}' — register it first") from exc

    def validate_payload(self, event_type: str, payload: dict[str, Any]) -> None:
        definition = self.get(event_type)
        missing = [f for f in definition.required_payload_fields if f not in payload]
        if missing:
            raise ValidationError(
                f"Event '{event_type}' payload missing required fields: {missing}"
            )

    def types(self) -> list[str]:
        return sorted(self._types)


#: Process-wide catalog, seeded with the foundation event types.
catalog = EventCatalog()

_FOUNDATION_EVENTS = [
    EventTypeDef(
        "atlas.platform.module.registered",
        "1.0.0",
        "api",
        "Module composed into the platform at startup",
        ("name", "version"),
    ),
    EventTypeDef(
        "atlas.platform.event.dead_lettered",
        "1.0.0",
        "worker",
        "An event exhausted retries and moved to the DLQ",
        ("event_id", "consumer"),
    ),
    EventTypeDef(
        "atlas.platform.event.redriven",
        "1.0.0",
        "api",
        "A dead-lettered event was re-driven by an operator",
        ("event_id", "consumer"),
    ),
    EventTypeDef(
        "atlas.platform.replay.started",
        "1.0.0",
        "api",
        "An event replay was initiated",
        ("replay_id", "event_type"),
    ),
    EventTypeDef(
        "atlas.platform.replay.completed",
        "1.0.0",
        "worker",
        "An event replay finished",
        ("replay_id", "events_replayed"),
    ),
    EventTypeDef(
        "atlas.platform.flag.changed",
        "1.0.0",
        "api",
        "A feature flag definition changed",
        ("flag_key",),
    ),
    EventTypeDef(
        "atlas.sample.echo.requested",
        "1.0.0",
        "api",
        "Throwaway sample-module proof event",
        ("message_length",),
    ),
]

for _definition in _FOUNDATION_EVENTS:
    catalog.register(_definition)
