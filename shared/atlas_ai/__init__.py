"""atlas_ai — AI platform interfaces (Spec 00 FR-020..026).

Interfaces plus in-memory reference implementations only. No agent logic, no live model
calls exist at foundation stage; future agent specs bind LangGraph/LiteLLM behind these
same protocols.
"""

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

__all__ = [
    "AgentDefinition",
    "AgentRegistry",
    "InMemoryAgentRegistry",
    "InMemoryPromptRegistry",
    "InMemoryToolRegistry",
    "ModelProvider",
    "PromptDefinition",
    "PromptRegistry",
    "ToolDefinition",
    "ToolRegistry",
]
