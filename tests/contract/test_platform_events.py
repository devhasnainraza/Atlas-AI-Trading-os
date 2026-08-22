"""US2 — event envelope + catalog contracts (T018 part 1; FR-015/019)."""

import pytest

from atlas_core.errors import ValidationError
from atlas_events import EventEnvelope, InMemoryEventBus, catalog, new_event_id


def test_envelope_carries_required_fields():
    env = EventEnvelope(
        event_type="atlas.sample.echo.requested", producer="test", payload={"message_length": 3}
    )
    assert env.event_id and env.correlation_id
    assert env.schema_version == "1.0.0"
    assert env.occurred_at.tzinfo is not None
    assert env.replay_of is None


def test_event_ids_are_time_ordered():
    ids = [new_event_id() for _ in range(50)]
    assert ids == sorted(ids), "UUIDv7-style ids must sort by creation time"
    assert len(set(ids)) == 50


async def test_unknown_event_type_is_rejected():
    bus = InMemoryEventBus(catalog)
    with pytest.raises(ValidationError):
        await bus.publish(EventEnvelope(event_type="atlas.nope.not.registered", producer="t"))


async def test_missing_required_payload_field_is_rejected():
    bus = InMemoryEventBus(catalog)
    with pytest.raises(ValidationError):
        await bus.publish(
            EventEnvelope(event_type="atlas.sample.echo.requested", producer="t", payload={})
        )


def test_breaking_schema_change_requires_new_type():
    from atlas_events.catalog import EventTypeDef

    with pytest.raises(ValidationError):
        catalog.register(
            EventTypeDef("atlas.sample.echo.requested", "2.0.0", "api", "breaking change")
        )


def test_replay_copy_marks_origin():
    env = EventEnvelope(
        event_type="atlas.sample.echo.requested", producer="t", payload={"message_length": 1}
    )
    replayed = env.as_replay()
    assert replayed.replay_of == env.event_id
    assert replayed.is_replay and not env.is_replay
