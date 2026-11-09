"""Agent orchestration service executing the multi-agent LangGraph pipeline per prompt.md."""

from __future__ import annotations

import logging
import uuid
from typing import Any
from atlas_ai.checkpointer import CheckpointSaver, InMemoryCheckpointSaver
from atlas_ai.providers import ModelProviderRouter
from atlas_ai.tools import ToolExecutor, register_default_tools
from atlas_api.modules.agents.domain.nodes import (
    critic_agent_node,
    decision_agent_node,
    execution_agent_node,
    manager_agent_node,
    market_agent_node,
    news_agent_node,
    policy_engine_node,
    risk_agent_node,
    technical_agent_node,
)
from atlas_api.modules.agents.domain.state import (
    AGENT_PERMISSIONS,
    AgentPermission,
    AgentSystemState,
    create_initial_state,
)
from atlas_core.errors import NotFoundError, ValidationError

logger = logging.getLogger("atlas_api.modules.agents.service")


class AgentOrchestrationService:
    """Coordinates multi-agent execution, state persistence, and human interrupt gates."""

    def __init__(
        self,
        checkpointer: CheckpointSaver | None = None,
        tool_executor: ToolExecutor | None = None,
        model_router: ModelProviderRouter | None = None,
    ) -> None:
        self.checkpointer = checkpointer or InMemoryCheckpointSaver()
        self.tool_executor = tool_executor or ToolExecutor()
        register_default_tools(self.tool_executor)
        self.model_router = model_router or ModelProviderRouter()
        self._active_threads: dict[str, AgentSystemState] = {}

    async def run_analysis(
        self,
        session_id: str | None,
        user_id: str,
        query: str,
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
    ) -> AgentSystemState:
        """Executes the prompt.md multi-agent pipeline:

        Market Agent (READ) + News Agent (READ/ANALYZE)
               ↓
        Risk Agent (ANALYZE)
               ↓
        Decision Agent (ANALYZE)
               ↓
        Critic Agent (CRITIQUE)
               ↓
        Policy / Risk Engine
               ↓
        Manager Agent (COORDINATE - no broker access)
               ↓
        Human Approval Gate (Interrupt if trade action)
               ↓
        Execution Agent (EXECUTE only)
        """
        session_id = session_id or str(uuid.uuid4())
        state = create_initial_state(
            session_id=session_id,
            user_id=user_id,
            user_query=query,
            symbol=symbol,
            timeframe=timeframe,
        )

        # 1. Market Agent (READ)
        market_delta = await market_agent_node(state)
        state.update(market_delta)  # type: ignore
        await self.checkpointer.put(session_id, "", "step-1-market", None, state)

        # 2. News Agent (READ / ANALYZE)
        news_delta = await news_agent_node(state)
        state.update(news_delta)  # type: ignore
        await self.checkpointer.put(session_id, "", "step-2-news", "step-1-market", state)

        # Supporting technical structure
        tech_delta = await technical_agent_node(state)
        state.update(tech_delta)  # type: ignore
        await self.checkpointer.put(session_id, "", "step-3-technical", "step-2-news", state)

        # 3. Risk Agent (ANALYZE - Pre-trade margin limits & constitutional hard veto)
        risk_delta = await risk_agent_node(state)
        state.update(risk_delta)  # type: ignore
        await self.checkpointer.put(session_id, "", "step-4-risk", "step-3-technical", state)

        # 4. Decision Agent (ANALYZE - Trade proposal synthesis)
        decision_delta = await decision_agent_node(state)
        state.update(decision_delta)  # type: ignore
        await self.checkpointer.put(session_id, "", "step-5-decision", "step-4-risk", state)

        # 5. Critic Agent (CRITIQUE - Devil's advocate, vulnerability analysis)
        critic_delta = await critic_agent_node(state)
        state.update(critic_delta)  # type: ignore
        await self.checkpointer.put(session_id, "", "step-6-critic", "step-5-decision", state)

        # 6. Policy / Risk Engine (Pre-execution rule verification)
        policy_delta = await policy_engine_node(state)
        state.update(policy_delta)  # type: ignore
        await self.checkpointer.put(session_id, "", "step-7-policy", "step-6-critic", state)

        # 7. Manager Agent (COORDINATE - Synthesizes 4-part contract and triggers approval)
        manager_delta = await manager_agent_node(state)
        state.update(manager_delta)  # type: ignore
        await self.checkpointer.put(session_id, "", "step-8-manager", "step-7-policy", state)

        # 8. Human Approval Interruption Gate
        if state.get("requires_human_approval", False):
            state["status"] = "PAUSED_APPROVAL"
            state["current_node"] = "human_approval_interrupt"
            self._active_threads[session_id] = state
            await self.checkpointer.put(session_id, "", "step-9-interrupt", "step-8-manager", state)
            logger.info("workflow_interrupted_for_human_approval", extra={"session_id": session_id})
            return state

        # If not paused and not rejected, mark completed
        if state.get("status") != "REJECTED":
            state["status"] = "COMPLETED"

        self._active_threads[session_id] = state
        return state

    async def resume_workflow(
        self,
        session_id: str,
        approved: bool,
        user_notes: str | None = None,
        signature_token: str | None = None,
    ) -> AgentSystemState:
        """Resumes a paused workflow following explicit human sign-off or rejection (prompt.md Feature 2)."""
        state = self._active_threads.get(session_id)
        if not state:
            record = await self.checkpointer.get(session_id)
            if not record:
                raise NotFoundError(
                    message=f"No active workflow found for session '{session_id}'",
                )
            state = record.state  # type: ignore

        if state.get("status") != "PAUSED_APPROVAL":
            raise ValidationError(
                message=f"Workflow '{session_id}' is not in PAUSED_APPROVAL state (current: {state.get('status')})",
            )

        if not approved:
            state["status"] = "REJECTED"
            state["human_approved"] = False
            state["current_node"] = "rejected_by_human"
            self._active_threads[session_id] = state
            await self.checkpointer.put(session_id, "", "step-resume-rejected", "step-9-interrupt", state)
            logger.info("workflow_rejected_by_human", extra={"session_id": session_id})
            return state

        # Approved: Proceed strictly to Execution Agent node (prompt.md Feature 1 & 2)
        state["human_approved"] = True
        exec_delta = await execution_agent_node(state)
        state.update(exec_delta)  # type: ignore
        state["status"] = "COMPLETED"
        self._active_threads[session_id] = state
        await self.checkpointer.put(session_id, "", "step-10-executed", "step-9-interrupt", state)
        logger.info("workflow_resumed_and_executed", extra={"session_id": session_id})
        return state

    async def cancel_workflow(self, session_id: str, reason: str | None = None) -> AgentSystemState:
        """Cancels an active or paused workflow."""
        state = self._active_threads.get(session_id)
        if not state:
            record = await self.checkpointer.get(session_id)
            if not record:
                raise NotFoundError(
                    message=f"Workflow '{session_id}' not found",
                )
            state = record.state  # type: ignore

        state["status"] = "CANCELLED"
        state["current_node"] = "cancelled"
        self._active_threads[session_id] = state
        await self.checkpointer.put(session_id, "", "step-cancelled", None, state)
        return state

    async def list_active_workflows(self) -> list[AgentSystemState]:
        """Returns list of active or paused workflow runs."""
        return list(self._active_threads.values())

    async def recover_workflow(self, session_id: str) -> AgentSystemState:
        """Crash-recovery: Restores agent workflow state from last checkpoint without state loss (prompt.md Feature 4)."""
        record = await self.checkpointer.get(session_id)
        if not record:
            raise NotFoundError(message=f"Checkpoint not found for session '{session_id}'")
        state: AgentSystemState = record.state  # type: ignore
        self._active_threads[session_id] = state
        return state
