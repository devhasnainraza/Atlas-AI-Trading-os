"""Public interface and composition root for Trading Automation module (Spec 06 §2, §9)."""

from __future__ import annotations

from atlas_api.modules.automation.router import (
    STATE_KEY,
    AutomationModuleContext,
    router,
)
from atlas_api.modules.automation.service import AutomationService
from atlas_api.modules.public import ModuleDef


def build_automation_module(env: str = "development") -> ModuleDef:
    """Composition root for the Spec 06 Trading Automation module."""
    service = AutomationService()
    context = AutomationModuleContext(service=service)

    return ModuleDef(
        name="automation",
        version="1.0.0",
        owner="automation-engine",
        router=router,
        app_state={STATE_KEY: context},
        health_probes={},
        subscriptions=(),
    )


__all__ = [
    "build_automation_module",
    "AutomationService",
]
