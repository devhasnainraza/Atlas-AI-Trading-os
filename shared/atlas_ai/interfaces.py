"""AI platform interfaces with in-memory reference implementations.

Contract rules every implementation must honor:
- Registries are versioned; (name, version) rows are immutable once registered.
- Memory access is always scoped per user (Constitution VIII) — no cross-user reads.
- Model providers are addressed by alias, never by vendor model name (FR-024).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from atlas_core.errors import ConflictError, NotFoundError


# -- Definitions -------------------------------------------------------------
@dataclass(frozen=True)
class AgentDefinition:
    name: str
    version: str
    capabilities: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    status: str = "registered"  # registered | active | suspended


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    version: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    required_permissions: tuple[str, ...] = ()


@dataclass(frozen=True)
class PromptDefinition:
    name: str
    version: str
    body: str
    status: str = "draft"  # draft | stable | deprecated
    metadata: dict[str, Any] = field(default_factory=dict)


# -- Registry protocols ------------------------------------------------------
class AgentRegistry(Protocol):
    def register(self, definition: AgentDefinition) -> None: ...

    def get(self, name: str, version: str | None = None) -> AgentDefinition: ...

    def list_all(self) -> list[AgentDefinition]: ...


class ToolRegistry(Protocol):
    def register(self, definition: ToolDefinition) -> None: ...

    def get(self, name: str, version: str | None = None) -> ToolDefinition: ...

    def tools_for_agent(self, agent: AgentDefinition) -> list[ToolDefinition]: ...


class PromptRegistry(Protocol):
    def register(self, definition: PromptDefinition) -> None: ...

    def get(self, name: str, version: str | None = None) -> PromptDefinition: ...


class MemoryStore(Protocol):
    """Per-user scoped agent memory. ``scope`` is (user_id, agent_id, kind)."""

    async def write(
        self, user_id: str, agent_id: str, kind: str, content: dict[str, Any]
    ) -> str: ...

    async def read(self, user_id: str, agent_id: str, kind: str) -> list[dict[str, Any]]: ...

    async def delete_user(self, user_id: str) -> int: ...


class ModelProvider(Protocol):
    """Alias-addressed model access; implementations resolve aliases from config."""

    async def complete(self, alias: str, prompt: str, **options: Any) -> str: ...

    async def embed(self, alias: str, text: str) -> list[float]: ...


class WorkflowEngine(Protocol):
    async def run(self, workflow: str, version: str, inputs: dict[str, Any]) -> str: ...

    async def pause(self, run_id: str) -> None: ...

    async def resume(self, run_id: str) -> None: ...

    async def cancel(self, run_id: str) -> None: ...


# -- In-memory reference implementations --------------------------------------
class _VersionedRegistry[DefinitionT]:
    """Shared (name, version) storage; the type parameter is the definition it holds."""

    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._items: dict[tuple[str, str], DefinitionT] = {}

    def _register(self, name: str, version: str, item: DefinitionT) -> None:
        key = (name, version)
        if key in self._items:
            raise ConflictError(f"{self._kind} '{name}' v{version} already registered (immutable)")
        self._items[key] = item

    def _get(self, name: str, version: str | None) -> DefinitionT:
        if version is not None:
            item = self._items.get((name, version))
            if item is None:
                raise NotFoundError(f"{self._kind} '{name}' v{version} not found")
            return item
        versions = sorted(v for (n, v) in self._items if n == name)
        if not versions:
            raise NotFoundError(f"{self._kind} '{name}' not found")
        return self._items[(name, versions[-1])]


class InMemoryAgentRegistry(_VersionedRegistry[AgentDefinition]):
    def __init__(self) -> None:
        super().__init__("agent")

    def register(self, definition: AgentDefinition) -> None:
        self._register(definition.name, definition.version, definition)

    def get(self, name: str, version: str | None = None) -> AgentDefinition:
        return self._get(name, version)

    def list_all(self) -> list[AgentDefinition]:
        return sorted(self._items.values(), key=lambda a: (a.name, a.version))


class InMemoryToolRegistry(_VersionedRegistry[ToolDefinition]):
    def __init__(self) -> None:
        super().__init__("tool")

    def register(self, definition: ToolDefinition) -> None:
        self._register(definition.name, definition.version, definition)

    def get(self, name: str, version: str | None = None) -> ToolDefinition:
        return self._get(name, version)

    def tools_for_agent(self, agent: AgentDefinition) -> list[ToolDefinition]:
        return [self.get(name) for name in agent.allowed_tools]


class InMemoryPromptRegistry(_VersionedRegistry[PromptDefinition]):
    def __init__(self) -> None:
        super().__init__("prompt")

    def register(self, definition: PromptDefinition) -> None:
        self._register(definition.name, definition.version, definition)

    def get(self, name: str, version: str | None = None) -> PromptDefinition:
        return self._get(name, version)
