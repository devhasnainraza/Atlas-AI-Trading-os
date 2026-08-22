"""atlas_events — event envelope, catalog, bus, outbox, and idempotency primitives.

Application code publishes through the outbox and consumes through subscriptions; it never
touches the broker API directly. The in-memory implementations are the contract-tested
reference; the Kafka adapters plug in behind the same protocols in deployed environments.
"""

from atlas_events.bus import DeadLetterEntry, EventBus, InMemoryEventBus
from atlas_events.catalog import EventCatalog, catalog
from atlas_events.envelope import EventEnvelope, new_event_id
from atlas_events.ledger import InMemoryProcessedLedger, ProcessedEventLedger
from atlas_events.outbox import InMemoryOutbox, OutboxEntry, OutboxStore

__all__ = [
    "DeadLetterEntry",
    "EventBus",
    "EventCatalog",
    "EventEnvelope",
    "InMemoryEventBus",
    "InMemoryOutbox",
    "InMemoryProcessedLedger",
    "OutboxEntry",
    "OutboxStore",
    "ProcessedEventLedger",
    "catalog",
    "new_event_id",
]
