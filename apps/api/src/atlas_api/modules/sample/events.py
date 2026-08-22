"""Sample module event handlers — proof consumer for the echo event."""

from __future__ import annotations

from atlas_events import EventEnvelope
from atlas_observability import get_logger

logger = get_logger("atlas_api.modules.sample")

#: Events observed by the sample consumer (inspectable in tests).
received: list[EventEnvelope] = []


async def on_echo_requested(envelope: EventEnvelope) -> None:
    received.append(envelope)
    logger.info(
        "sample_echo_consumed",
        event_id=envelope.event_id,
        replay=envelope.is_replay,
        message_length=envelope.payload.get("message_length"),
    )
