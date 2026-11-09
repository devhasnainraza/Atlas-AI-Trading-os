"""Public composition root for Infrastructure & SRE module (Spec 11 §2, §9)."""

from __future__ import annotations

from atlas_api.modules.infrastructure.router import (
    STATE_KEY,
    InfrastructureModuleContext,
    router,
)
from atlas_api.modules.infrastructure.service import InfrastructureService
from atlas_api.modules.public import ModuleDef


def build_infrastructure_module(env: str = "development") -> ModuleDef:
    """Composition root for the Spec 11 Infrastructure & SRE module."""
    service = InfrastructureService()
    context = InfrastructureModuleContext(service=service)

    return ModuleDef(
        name="infrastructure",
        version="1.0.0",
        owner="sre-platform",
        router=router,
        app_state={STATE_KEY: context},
        health_probes={},
        subscriptions=(),
    )


__all__ = [
    "build_infrastructure_module",
    "InfrastructureService",
]
