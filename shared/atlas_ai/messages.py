"""Inter-agent message passing protocol (Spec 03 FR-002).

Structured typed envelopes exchanged between agents across the LangGraph mesh and Kafka topics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass(frozen=True)
class AgentMessageEnvelope:
    """Standard message envelope for inter-agent communication."""

    sender: str
    recipient: str
    task_id: str
    message_type: str  # QUERY | PROPOSAL | CRITIQUE | VETO | SYNTHESIS
    payload: dict[str, Any]
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert envelope to dictionary for serialization."""
        return {
            "correlation_id": self.correlation_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "task_id": self.task_id,
            "message_type": self.message_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentMessageEnvelope:
        """Construct envelope from dictionary."""
        ts = data.get("timestamp")
        parsed_ts = datetime.fromisoformat(ts) if isinstance(ts, str) else datetime.now(timezone.utc)
        return cls(
            correlation_id=data.get("correlation_id", str(uuid.uuid4())),
            sender=data["sender"],
            recipient=data["recipient"],
            task_id=data["task_id"],
            message_type=data["message_type"],
            payload=data.get("payload", {}),
            timestamp=parsed_ts,
        )
