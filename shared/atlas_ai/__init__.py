"""atlas_ai — AI platform interfaces and runtime primitives (Spec 00 & Spec 03).

Provides the multi-agent execution abstractions: registries, sandboxed tools, model provider
routing, inter-agent envelopes, and thread checkpointers.
"""

from atlas_ai.checkpointer import (
    CheckpointRecord,
    CheckpointSaver,
    InMemoryCheckpointSaver,
)
from atlas_ai.interfaces import (
    AgentDefinition,
    AgentRegistry,
    InMemoryAgentRegistry,
    InMemoryPromptRegistry,
    InMemoryToolRegistry,
    ModelProvider,
    PromptDefinition,
    PromptRegistry,
    ToolDefinition,
    ToolRegistry,
)
from atlas_ai.messages import AgentMessageEnvelope
from atlas_ai.providers import MockModelProvider, ModelProviderRouter
from atlas_ai.tools import (
    ToolExecutor,
    register_default_tools,
    tool_calc_indicators,
    tool_macro_calendar,
    tool_risk_calculate_exposure,
)

__all__ = [
    "AgentDefinition",
    "AgentMessageEnvelope",
    "AgentRegistry",
    "CheckpointRecord",
    "CheckpointSaver",
    "InMemoryAgentRegistry",
    "InMemoryCheckpointSaver",
    "InMemoryPromptRegistry",
    "InMemoryToolRegistry",
    "MockModelProvider",
    "ModelProvider",
    "ModelProviderRouter",
    "PromptDefinition",
    "PromptRegistry",
    "ToolDefinition",
    "ToolExecutor",
    "ToolRegistry",
    "register_default_tools",
    "tool_calc_indicators",
    "tool_macro_calendar",
    "tool_risk_calculate_exposure",
]
