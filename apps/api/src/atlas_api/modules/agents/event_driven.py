"""24/7 Event-Driven Architecture dispatcher for Atlas AI (prompt.md Feature 3).

Flow:
    Market Event (Breakout / Price Shock / Liquidity Imbalance)
            ↓
    Kafka / Redpanda Event Bus
            ↓
    Multi-Agent Workflow (Market + News + Risk + Decision + Critic)
            ↓
    Decision Synthesis
            ↓
    Action / User Alert Broadcast
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid

from atlas_api.modules.agents.service import AgentOrchestrationService
from atlas_core.event_bus import EventEnvelope


@dataclass
class MarketEventPayload:
    """Incoming market anomaly or structure shift detected by the stream processors."""

    event_id: str
    symbol: str
    event_type: str  # "VOLATILITY_BREAKOUT" | "PRICE_SHOCK" | "ORDERBOOK_IMBALANCE" | "SESSION_OPEN"
    price: str
    intensity: str  # "MODERATE" | "HIGH" | "CRITICAL"
    summary: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EventDrivenDecisionResult:
    """Synthesized outcome of the event-driven workflow."""

    event_id: str
    session_id: str
    symbol: str
    triggered_at: str
    status: str  # "ACTION_DISPATCHED" | "ALERT_BROADCAST" | "AWAITING_APPROVAL" | "REJECTED_RISK"
    synthesized_decision: str
    confidence: str
    requires_approval: bool
    ticket_id: str | None


class EventDrivenMarketDispatcher:
    """Consumes real-time market events from the event bus and executes the 24/7 autonomous loop."""

    def __init__(self, agent_service: AgentOrchestrationService) -> None:
        self.agent_service = agent_service
        self._history: list[EventDrivenDecisionResult] = []

    async def handle_market_event(self, event: MarketEventPayload) -> EventDrivenDecisionResult:
        session_id = f"auto-event-{str(uuid.uuid4())[:8]}"
        query = f"Evaluate urgent market trigger: {event.event_type} on {event.symbol} at price {event.price}. {event.summary}"

        state = await self.agent_service.run_analysis(
            session_id=session_id,
            user_id="autonomous-system",
            query=query,
            symbol=event.symbol,
        )

        requires_approval = state.get("requires_human_approval", False)
        status = (
            "AWAITING_APPROVAL"
            if requires_approval
            else ("REJECTED_RISK" if state.get("status") == "REJECTED" else "ACTION_DISPATCHED")
        )

        result = EventDrivenDecisionResult(
            event_id=event.event_id,
            session_id=session_id,
            symbol=event.symbol,
            triggered_at=event.timestamp.isoformat(),
            status=status,
            synthesized_decision=state.get("synthesized_recommendation", "Awaiting review"),
            confidence=state.get("confidence_score", "0.00"),
            requires_approval=requires_approval,
            ticket_id=state.get("approval_ticket_id"),
        )
        self._history.append(result)
        return result

    def get_event_history(self) -> list[EventDrivenDecisionResult]:
        return sorted(self._history, key=lambda h: h.triggered_at, reverse=True)
