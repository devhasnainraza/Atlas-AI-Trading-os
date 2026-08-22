"""Scheduler entrypoint — job registry heartbeat.

Celery Beat integration arrives with the first real scheduled workload (Spec 01 health
probes); this keeps the deployable unit alive and observable until then.
"""

from __future__ import annotations

import asyncio

from atlas_core.config import load_settings
from atlas_observability import configure_observability, get_logger


async def main() -> None:
    settings = load_settings(service_name="atlas-scheduler")
    configure_observability(settings.service_name, settings.log_level)
    logger = get_logger("atlas_scheduler")
    logger.info("scheduler_started", env=str(settings.env))
    while True:  # heartbeat until first registered job lands
        await asyncio.sleep(60)
        logger.info("scheduler_heartbeat")


if __name__ == "__main__":
    asyncio.run(main())
