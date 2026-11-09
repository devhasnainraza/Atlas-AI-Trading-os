"""State definitions for the LangGraph multi-agent system matching prompt.md specifications."""

from __future__ import annotations

from enum import Enum
from typing import Any, TypedDict


class AgentPermission(str, Enum):
    """Explicit capability boundaries enforced per agent per prompt.md."""

    READ = "READ"
    ANALYZE = "ANALYZE"
    READ_ANALYZE = "READ / ANALYZE"
    CRITIQUE = "CRITIQUE"
    EXECUTE = "EXECUTE"
    COORDINATE = "COORDINATE"


#: Constitutional agent permission matrix per prompt.md
AGENT_PERMISSIONS: dict[str, AgentPermission] = {
    "manager_agent": AgentPermission.COORDINATE,  # No direct broker access!
    "market_agent": AgentPermission.READ,
    "news_agent": AgentPermission.READ_ANALYZE,
    "risk_agent": AgentPermission.ANALYZE,
    "decision_agent": AgentPermission.ANALYZE,
    "critic_agent": AgentPermission.CRITIQUE,
    "policy_engine": AgentPermission.ANALYZE,
    "execution_agent": AgentPermission.EXECUTE,
}


class AgentSystemState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes during multi-agent analysis."""

    session_id: str
    user_id: str
    symbol: str
    timeframe: str
    user_query: str

    # Agent Observation & Intelligence (prompt.md architecture)
    market_data: dict[str, Any]  # Market Agent (READ)
    news_analysis: dict[str, Any]  # News Agent (READ/ANALYZE)
    technical_analysis: dict[str, Any]  # Market/Technical supporting metrics
    risk_evaluation: dict[str, Any]  # Risk Agent (ANALYZE)
    decision_proposal: dict[str, Any]  # Decision Agent (ANALYZE)
    critic_critique: dict[str, Any]  # Critic Agent (CRITIQUE)
    policy_validation: dict[str, Any]  # Policy Engine (VALIDATION)

    # Synthesis & Recommendation (Constitutional 4-Part Contract)
    confidence_score: str  # Stored as string-encoded Decimal (e.g. "78.50")
    evidence: list[str]
    risks: list[str]
    alternative_scenarios: list[str]
    synthesized_recommendation: str

    # Human Gate & Execution
    requires_human_approval: bool
    human_approved: bool | None
    approval_ticket_id: str | None
    execution_result: dict[str, Any] | None

    # Step tracing & permissions
    current_node: str
    status: str  # ACTIVE | PAUSED_APPROVAL | COMPLETED | CANCELLED | REJECTED
    messages: list[dict[str, Any]]
    agent_permissions: dict[str, str]


def create_initial_state(
    session_id: str,
    user_id: str,
    user_query: str,
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
) -> AgentSystemState:
    """Initializes a blank state envelope for graph execution per prompt.md."""
    return {
        "session_id": session_id,
        "user_id": user_id,
        "symbol": symbol,
        "timeframe": timeframe,
        "user_query": user_query,
        "market_data": {},
        "news_analysis": {},
        "technical_analysis": {},
        "risk_evaluation": {},
        "decision_proposal": {},
        "critic_critique": {},
        "policy_validation": {},
        "confidence_score": "0.00",
        "evidence": [],
        "risks": [],
        "alternative_scenarios": [],
        "synthesized_recommendation": "",
        "requires_human_approval": False,
        "human_approved": None,
        "approval_ticket_id": None,
        "execution_result": None,
        "current_node": "start",
        "status": "ACTIVE",
        "messages": [{"role": "user", "content": user_query}],
        "agent_permissions": {k: v.value for k, v in AGENT_PERMISSIONS.items()},
    }
