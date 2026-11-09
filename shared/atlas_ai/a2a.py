"""Agent-to-Agent (A2A) protocol and remote specialist delegation (prompt.md Feature 6).

Enables discovery, delegation, and peer-to-peer collaboration with remote specialist agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
import uuid


@dataclass(frozen=True)
class AgentCard:
    """Public discovery card of an independent external or internal specialist agent."""

    agent_id: str
    name: str
    specialty: str  # e.g. "MACRO_SENTIMENT", "ON_CHAIN_WHALES", "QUANT_VOLATILITY"
    endpoint_url: str
    supported_tasks: tuple[str, ...]
    authority_level: str  # "ADVISORY" | "ANALYTICAL" | "CRITIQUE"
    reputation_score: Decimal = Decimal("95.00")
    status: str = "ONLINE"  # "ONLINE" | "BUSY" | "OFFLINE"


@dataclass
class A2ADelegationRequest:
    """Delegation payload sent to an external specialist agent."""

    delegation_id: str
    originator_agent: str
    target_agent_id: str
    task_type: str
    context_payload: dict[str, Any]
    timeout_seconds: int = 15
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class A2ADelegationResponse:
    """Structured response returned by a specialist agent under A2A protocol."""

    delegation_id: str
    responder_agent_id: str
    status: str  # "COMPLETED" | "REJECTED" | "TIMEOUT"
    findings: dict[str, Any]
    confidence: Decimal
    execution_time_ms: int
    signature: str


class A2ARegistry:
    """Central directory for discovering registered specialist agents."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentCard] = {}
        self._register_default_specialists()

    def _register_default_specialists(self) -> None:
        specialists = [
            AgentCard(
                agent_id="agent-macro-global",
                name="Global Macro Sentinel",
                specialty="MACRO_SENTIMENT",
                endpoint_url="https://agents.atlas.internal/macro-sentinel",
                supported_tasks=("cpi_analysis", "fomc_sentiment", "bond_yield_correlation"),
                authority_level="ANALYTICAL",
                reputation_score=Decimal("98.50"),
            ),
            AgentCard(
                agent_id="agent-onchain-whales",
                name="On-Chain Liquidity & Whale Tracker",
                specialty="ON_CHAIN_WHALES",
                endpoint_url="https://agents.atlas.internal/whale-tracker",
                supported_tasks=("exchange_inflow_spike", "whale_wallet_cluster", "stablecoin_supply_delta"),
                authority_level="ANALYTICAL",
                reputation_score=Decimal("96.20"),
            ),
            AgentCard(
                agent_id="agent-volatility-quant",
                name="Implied Volatility Surface Quant",
                specialty="QUANT_VOLATILITY",
                endpoint_url="https://agents.atlas.internal/vol-surface",
                supported_tasks=("gamma_exposure", "skew_inversion", "volatility_regime_classification"),
                authority_level="CRITIQUE",
                reputation_score=Decimal("99.10"),
            ),
        ]
        for s in specialists:
            self._agents[s.agent_id] = s

    def discover_specialists(self, specialty: str | None = None) -> list[AgentCard]:
        """Discovers active specialist agents by domain."""
        if specialty:
            return [a for a in self._agents.values() if a.specialty == specialty.upper() and a.status == "ONLINE"]
        return list(self._agents.values())

    def get_agent(self, agent_id: str) -> AgentCard | None:
        return self._agents.get(agent_id)


class A2ADelegationClient:
    """Dispatches asynchronous sub-tasks to discovered remote agents."""

    def __init__(self, registry: A2ARegistry) -> None:
        self.registry = registry

    async def delegate(
        self,
        originator_agent: str,
        target_agent_id: str,
        task_type: str,
        payload: dict[str, Any],
    ) -> A2ADelegationResponse:
        agent = self.registry.get_agent(target_agent_id)
        if not agent:
            return A2ADelegationResponse(
                delegation_id=str(uuid.uuid4()),
                responder_agent_id=target_agent_id,
                status="REJECTED",
                findings={"error": f"Specialist agent '{target_agent_id}' not found in registry"},
                confidence=Decimal("0.00"),
                execution_time_ms=0,
                signature="",
            )

        # Simulated remote A2A RPC dispatch
        del_id = str(uuid.uuid4())
        findings: dict[str, Any] = {}
        confidence = Decimal("88.00")

        if agent.specialty == "MACRO_SENTIMENT":
            findings = {
                "macro_regime": "RISK_ON",
                "bond_yield_pressure": "NEUTRAL",
                "recommended_stance": "FAVOR_UPSIDE_MOMENTUM",
            }
            confidence = Decimal("91.50")
        elif agent.specialty == "ON_CHAIN_WHALES":
            findings = {
                "net_exchange_flow_24h": "-4200 BTC (Outflow Accumulation)",
                "top_100_whale_delta": "+1.2% (Accumulating)",
                "liquidity_draw_cluster": "68200.00",
            }
            confidence = Decimal("89.00")
        elif agent.specialty == "QUANT_VOLATILITY":
            findings = {
                "gamma_flip_level": "66800.00",
                "market_maker_stance": "LONG_GAMMA (Volatility dampening above 67000)",
                "iv_rank_30d": "34.5% (Fair value / not stretched)",
            }
            confidence = Decimal("94.00")

        return A2ADelegationResponse(
            delegation_id=del_id,
            responder_agent_id=target_agent_id,
            status="COMPLETED",
            findings=findings,
            confidence=confidence,
            execution_time_ms=45,
            signature=f"ed25519-sig-{del_id[:8]}",
        )
