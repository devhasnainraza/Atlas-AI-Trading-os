"""Public composition root for Enterprise Features module (Spec 10 §2, §9)."""

from __future__ import annotations

from atlas_api.modules.enterprise.router import (
    STATE_KEY,
    EnterpriseModuleContext,
    router,
)
from atlas_api.modules.enterprise.service import EnterpriseService
from atlas_api.modules.public import ModuleDef


def build_enterprise_module(env: str = "development") -> ModuleDef:
    """Composition root for the Spec 10 Enterprise Features module."""
    service = EnterpriseService()
    context = EnterpriseModuleContext(service=service)

    return ModuleDef(
        name="enterprise",
        version="1.0.0",
        owner="enterprise-platform",
        router=router,
        app_state={STATE_KEY: context},
        health_probes={},
        subscriptions=(),
    )


__all__ = [
    "build_enterprise_module",
    "EnterpriseService",
]
