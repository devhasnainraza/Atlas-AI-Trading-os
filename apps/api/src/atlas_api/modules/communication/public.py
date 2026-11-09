"""Public composition root for Communication Platform module (Spec 08 §2, §9)."""

from __future__ import annotations

from atlas_api.modules.communication.router import (
    STATE_KEY,
    CommunicationModuleContext,
    router,
)
from atlas_api.modules.communication.service import CommunicationService
from atlas_api.modules.public import ModuleDef


def build_communication_module(env: str = "development") -> ModuleDef:
    """Composition root for the Spec 08 Communication Platform module."""
    service = CommunicationService()
    context = CommunicationModuleContext(service=service)

    return ModuleDef(
        name="communication",
        version="1.0.0",
        owner="communication-engine",
        router=router,
        app_state={STATE_KEY: context},
        health_probes={},
        subscriptions=(),
    )


__all__ = [
    "build_communication_module",
    "CommunicationService",
]
