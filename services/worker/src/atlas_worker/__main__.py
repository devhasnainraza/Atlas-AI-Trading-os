"""Worker entrypoint — runs the outbox relay loop.

Foundation stage: in-memory stores mean the relay is a heartbeat proving the deployable
unit; the Kafka/SQLAlchemy adapters swap in behind the same protocols (Spec 01+).
"""

from __future__ import annotations

import asyncio

from atlas_core.config import load_settings
from atlas_events import InMemoryEventBus, InMemoryOutbox, catalog
from atlas_observability import configure_observability, get_logger
from atlas_worker.events import OutboxRelay


async def main() -> None:
    settings = load_settings(service_name="atlas-worker")
    configure_observability(settings.service_name, settings.log_level)
    logger = get_logger("atlas_worker")
    logger.info("worker_started", env=str(settings.env))

    relay = OutboxRelay(InMemoryOutbox(), InMemoryEventBus(catalog))
    await relay.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
