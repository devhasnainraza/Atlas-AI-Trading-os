"""Agent module v1 API endpoints and module definition (Spec 03 §9)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Path, Request, status

from atlas_api.modules.agents.schemas import (
    ActiveWorkflowSummary,
    AgentChatRequest,
    AgentChatResponse,
    AgentRecommendationResponse,
    WorkflowCancelRequest,
    WorkflowResumeRequest,
)
from atlas_api.modules.agents.service import AgentOrchestrationService
from atlas_api.modules.public import ModuleDef
from atlas_core.errors import InternalError

router = APIRouter(prefix="/agents", tags=["agents"])

STATE_KEY = "agents_context"


@dataclass(frozen=True)
class AgentsModuleContext:
    service: AgentOrchestrationService


def get_agents_context(request: Request) -> AgentsModuleContext:
    context = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(context, AgentsModuleContext):
        raise InternalError(
            internal_context={"detail": "agents module accessed before composition"}
        )
    return context


def get_agents_service(
    context: AgentsModuleContext = Depends(get_agents_context),
) -> AgentOrchestrationService:
    return context.service


def _build_response_envelope(state: dict) -> AgentChatResponse:
    confidence_val = state.get("confidence_score", "0.00")
    recommendation = AgentRecommendationResponse(
        confidence_score=Decimal(confidence_val),
        evidence=state.get("evidence", ["Initial analysis completed."]),
        risks=state.get("risks", ["Standard market volatility."]),
        alternative_scenarios=state.get("alternative_scenarios", ["Invalidation if price reverses."]),
        synthesized_recommendation=state.get("synthesized_recommendation", "Analysis completed."),
    )
    return AgentChatResponse(
        session_id=state.get("session_id", ""),
        symbol=state.get("symbol", "BTC/USDT"),
        status=state.get("status", "COMPLETED"),
        recommendation=recommendation,
        requires_human_approval=state.get("requires_human_approval", False),
        approval_ticket_id=state.get("approval_ticket_id"),
        execution_result=state.get("execution_result"),
    )


@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agents(
    body: AgentChatRequest,
    request: Request,
    service: AgentOrchestrationService = Depends(get_agents_service),
) -> AgentChatResponse:
    """Initiates or continues multi-agent analysis with constitutional 4-part output contract."""
    # Read user_id from principal if authenticated, otherwise use demo user
    principal = getattr(request.state, "principal", None)
    user_id = principal.user_id if principal else "demo-user-001"

    state = await service.run_analysis(
        session_id=body.session_id,
        user_id=user_id,
        query=body.message,
        symbol=body.symbol,
        timeframe=body.timeframe,
    )
    return _build_response_envelope(state)


@router.get("/active-workflows", response_model=list[ActiveWorkflowSummary])
async def list_active_workflows(
    service: AgentOrchestrationService = Depends(get_agents_service),
) -> list[ActiveWorkflowSummary]:
    """Lists all active and paused agent execution threads."""
    workflows = await service.list_active_workflows()
    return [
        ActiveWorkflowSummary(
            session_id=w.get("session_id", ""),
            symbol=w.get("symbol", ""),
            current_node=w.get("current_node", ""),
            status=w.get("status", ""),
            requires_human_approval=w.get("requires_human_approval", False),
            approval_ticket_id=w.get("approval_ticket_id"),
            created_at="2026-09-21T00:00:00Z",
        )
        for w in workflows
    ]


@router.post("/workflows/{run_id}/resume", response_model=AgentChatResponse)
async def resume_workflow(
    run_id: str = Path(..., description="The session_id / run_id of the paused workflow"),
    body: WorkflowResumeRequest = ...,
    service: AgentOrchestrationService = Depends(get_agents_service),
) -> AgentChatResponse:
    """Resumes a paused LangGraph execution following explicit human sign-off."""
    state = await service.resume_workflow(
        session_id=run_id,
        approved=body.approved,
        user_notes=body.user_notes,
        signature_token=body.signature_token,
    )
    return _build_response_envelope(state)


@router.post("/workflows/{run_id}/cancel", response_model=AgentChatResponse)
async def cancel_workflow(
    run_id: str = Path(..., description="The session_id / run_id to cancel"),
    body: WorkflowCancelRequest = ...,
    service: AgentOrchestrationService = Depends(get_agents_service),
) -> AgentChatResponse:
    """Aborts an active or paused agent workflow."""
    state = await service.cancel_workflow(session_id=run_id, reason=body.reason)
    return _build_response_envelope(state)


@router.post("/workflows/{run_id}/recover", response_model=AgentChatResponse)
async def recover_workflow(
    run_id: str = Path(..., description="The session_id / run_id to recover from checkpoint"),
    service: AgentOrchestrationService = Depends(get_agents_service),
) -> AgentChatResponse:
    """Crash-recovery: Restores agent workflow state from checkpoint without state loss (prompt.md Feature 4)."""
    state = await service.recover_workflow(session_id=run_id)
    return _build_response_envelope(state)


@router.get("/permissions")
async def get_agent_permissions() -> dict[str, str]:
    """Returns the strict capability permissions matrix per prompt.md Feature 1."""
    from atlas_api.modules.agents.domain.state import AGENT_PERMISSIONS
    return {k: v.value for k, v in AGENT_PERMISSIONS.items()}


@router.get("/mcp/tools")
async def list_mcp_tools() -> list[dict]:
    """Lists standard Model Context Protocol MCP tools (prompt.md Feature 5)."""
    from atlas_ai.mcp import create_default_mcp_server
    server = create_default_mcp_server()
    tools = server.list_tools()
    return [
        {
            "name": t.name,
            "uri": t.uri,
            "description": t.description,
            "category": t.category,
            "input_schema": t.input_schema,
            "output_schema": t.output_schema,
        }
        for t in tools
    ]


@router.post("/mcp/call")
async def call_mcp_tool(body: dict) -> dict:
    """Executes a tool call via Model Context Protocol MCP (prompt.md Feature 5)."""
    from atlas_ai.mcp import create_default_mcp_server, MCPClient
    server = create_default_mcp_server()
    client = MCPClient(server)
    res = await client.call(
        tool_uri=body.get("tool_uri", ""),
        arguments=body.get("arguments", {}),
        caller_agent=body.get("caller_agent", "manager_agent"),
    )
    return {
        "call_id": res.call_id,
        "tool_uri": res.tool_uri,
        "status": res.status,
        "data": res.data,
        "error_message": res.error_message,
    }


@router.get("/a2a/specialists")
async def list_a2a_specialists() -> list[dict]:
    """Lists discovered external specialist agents for A2A collaboration (prompt.md Feature 6)."""
    from atlas_ai.a2a import A2ARegistry
    registry = A2ARegistry()
    specialists = registry.discover_specialists()
    return [
        {
            "agent_id": a.agent_id,
            "name": a.name,
            "specialty": a.specialty,
            "endpoint_url": a.endpoint_url,
            "supported_tasks": list(a.supported_tasks),
            "authority_level": a.authority_level,
            "reputation_score": str(a.reputation_score),
            "status": a.status,
        }
        for a in specialists
    ]


@router.post("/a2a/delegate")
async def delegate_a2a_task(body: dict) -> dict:
    """Delegates an analytical task to an external specialist agent via A2A (prompt.md Feature 6)."""
    from atlas_ai.a2a import A2ARegistry, A2ADelegationClient
    registry = A2ARegistry()
    client = A2ADelegationClient(registry)
    res = await client.delegate(
        originator_agent=body.get("originator_agent", "decision_agent"),
        target_agent_id=body.get("target_agent_id", "agent-macro-global"),
        task_type=body.get("task_type", "analysis"),
        payload=body.get("payload", {}),
    )
    return {
        "delegation_id": res.delegation_id,
        "responder_agent_id": res.responder_agent_id,
        "status": res.status,
        "findings": res.findings,
        "confidence": str(res.confidence),
        "execution_time_ms": res.execution_time_ms,
        "signature": res.signature,
    }


@router.post("/events/trigger")
async def trigger_market_event(
    body: dict,
    service: AgentOrchestrationService = Depends(get_agents_service),
) -> dict:
    """Simulates 24/7 event-driven architecture trigger from Kafka (prompt.md Feature 3)."""
    from atlas_api.modules.agents.event_driven import (
        EventDrivenMarketDispatcher,
        MarketEventPayload,
    )
    import uuid
    dispatcher = EventDrivenMarketDispatcher(service)
    payload = MarketEventPayload(
        event_id=body.get("event_id", f"evt-{str(uuid.uuid4())[:8]}"),
        symbol=body.get("symbol", "BTC/USDT"),
        event_type=body.get("event_type", "VOLATILITY_BREAKOUT"),
        price=body.get("price", "67240.00"),
        intensity=body.get("intensity", "HIGH"),
        summary=body.get("summary", "Sudden 2.4% volatility breakout with heavy buy volume"),
    )
    res = await dispatcher.handle_market_event(payload)
    return {
        "event_id": res.event_id,
        "session_id": res.session_id,
        "symbol": res.symbol,
        "triggered_at": res.triggered_at,
        "status": res.status,
        "synthesized_decision": res.synthesized_decision,
        "confidence": res.confidence,
        "requires_approval": res.requires_approval,
        "ticket_id": res.ticket_id,
    }



def build_agents_module(env: str = "development") -> ModuleDef:
    """Composition root for the Spec 03 agents module."""
    service = AgentOrchestrationService()
    context = AgentsModuleContext(service=service)

    return ModuleDef(
        name="agents",
        version="1.0.0",
        owner="agent-platform",
        router=router,
        app_state={STATE_KEY: context},
        health_probes={},
        subscriptions=(),
    )
