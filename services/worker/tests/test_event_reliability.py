"""US2 — retry, DLQ, re-drive, replay, idempotency, and outbox relay (T018 part 2).

Covers the spec edge cases: poison events dead-letter instead of blocking; duplicate
deliveries are detectable; replays are distinguishable from live events; zero silent loss
(SC-005).
"""

from atlas_events import (
    EventEnvelope,
    InMemoryEventBus,
    InMemoryOutbox,
    InMemoryProcessedLedger,
    catalog,
)
from atlas_events.ledger import idempotent
from atlas_worker.events import OutboxRelay

ECHO = "atlas.sample.echo.requested"


def _echo_event(n: int = 1) -> EventEnvelope:
    return EventEnvelope(event_type=ECHO, producer="test", payload={"message_length": n})


async def test_poison_event_retries_then_dead_letters():
    bus = InMemoryEventBus(catalog)
    attempts = []

    async def always_fails(env: EventEnvelope) -> None:
        attempts.append(env.event_id)
        raise RuntimeError("boom")

    bus.subscribe("poison.consumer", ECHO, always_fails, max_attempts=3)
    await bus.publish(_echo_event())

    assert len(attempts) == 3, "retry policy must be exhausted"
    dlq = bus.dead_letters()
    assert len(dlq) == 1
    assert dlq[0].consumer == "poison.consumer"
    assert dlq[0].failure_reason == "boom"
    assert len(dlq[0].attempts) == 3


async def test_redrive_delivers_and_marks_entry():
    bus = InMemoryEventBus(catalog)
    calls = {"n": 0}

    async def fails_then_succeeds(env: EventEnvelope) -> None:
        calls["n"] += 1
        if calls["n"] <= 2:  # fail both initial attempts → DLQ
            raise RuntimeError("transient")

    bus.subscribe("flaky.consumer", ECHO, fails_then_succeeds, max_attempts=2)
    event = _echo_event()
    await bus.publish(event)
    assert len(bus.dead_letters()) == 1

    ok = await bus.redrive(event.event_id, "flaky.consumer")
    assert ok
    assert bus.dead_letters(status="dead") == []
    assert bus.dead_letters(status="redriven")[0].envelope.event_id == event.event_id


async def test_replay_reaches_new_subscriber_marked_as_replay():
    bus = InMemoryEventBus(catalog)
    live_seen: list[EventEnvelope] = []

    async def first(env: EventEnvelope) -> None:
        live_seen.append(env)

    bus.subscribe("first.consumer", ECHO, first)
    for n in (1, 2, 3):
        await bus.publish(_echo_event(n))

    replay_seen: list[EventEnvelope] = []

    async def late_joiner(env: EventEnvelope) -> None:
        replay_seen.append(env)

    bus.subscribe("late.consumer", ECHO, late_joiner)
    count = await bus.replay(ECHO)

    assert count == 3
    assert all(e.is_replay for e in replay_seen if e.replay_of)
    assert len([e for e in replay_seen if e.is_replay]) == 3
    # Live consumer also receives the replayed copies — its ledger dedupes in real use.
    assert all(not e.is_replay for e in live_seen[:3])


async def test_idempotent_handler_skips_duplicate_delivery():
    ledger = InMemoryProcessedLedger()
    effects = []

    @idempotent("dedup.consumer", ledger)
    async def handler(env: EventEnvelope) -> None:
        effects.append(env.event_id)

    event = _echo_event()
    await handler(event)
    await handler(event)  # duplicate delivery (retry/replay)
    assert effects == [event.event_id], "duplicate must be a no-op"


async def test_outbox_relay_publishes_all_pending_exactly_once():
    bus = InMemoryEventBus(catalog)
    outbox = InMemoryOutbox()
    received: list[str] = []

    async def consumer(env: EventEnvelope) -> None:
        received.append(env.event_id)

    bus.subscribe("relay.consumer", ECHO, consumer)
    for n in range(5):
        outbox.add(_echo_event(n + 1))

    relay = OutboxRelay(outbox, bus)
    first_pass = await relay.run_once()
    second_pass = await relay.run_once()

    assert first_pass == 5 and second_pass == 0
    assert len(received) == 5
    assert outbox.pending() == []
    assert all(e.status == "published" for e in outbox.all_entries())
