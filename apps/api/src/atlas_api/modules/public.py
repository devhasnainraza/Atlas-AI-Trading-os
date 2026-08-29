"""Module registration contract (Spec 00 FR-002/003, US1).

A module ships a ``ModuleDef`` describing everything the platform needs to compose it:
its router, event subscriptions, and health dependencies. Adding a module is additive —
``create_app`` iterates registered defs; no existing module changes.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field

from fastapi import APIRouter

from atlas_events.bus import Handler


@dataclass(frozen=True)
class EventSubscriptionDef:
    consumer: str
    event_type: str
    handler: Handler
    replay_capable: bool = True


@dataclass(frozen=True)
class ModuleDef:
    """Everything the platform needs to compose a module into the app."""

    name: str
    version: str
    owner: str
    router: APIRouter | None = None
    routers_extra: tuple[APIRouter, ...] = ()
    subscriptions: tuple[EventSubscriptionDef, ...] = ()
    health_probes: dict[str, Callable[[], Awaitable[bool]]] = field(default_factory=dict)
    #: Module-owned objects to attach to ``app.state``, so per-app state lives on the app
    #: rather than in a module-level global. A global would make two composed apps in one
    #: process share whichever was built last — harmless for a single deployment, wrong for
    #: anything holding two apps at once, and the platform stays ignorant of what is inside.
    app_state: Mapping[str, object] = field(default_factory=dict)


class ModuleRegistry:
    """Runtime registry of composed modules (backs /v1/platform module listing)."""

    def __init__(self) -> None:
        self._modules: dict[str, ModuleDef] = {}

    def register(self, module: ModuleDef) -> None:
        if module.name in self._modules:
            raise ValueError(f"Module '{module.name}' already registered")
        self._modules[module.name] = module

    def get(self, name: str) -> ModuleDef:
        return self._modules[name]

    def all_modules(self) -> list[ModuleDef]:
        return sorted(self._modules.values(), key=lambda m: m.name)
