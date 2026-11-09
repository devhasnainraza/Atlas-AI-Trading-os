"""Public composition root for Dashboard & Analytics module (Spec 09 §2, §9)."""

from __future__ import annotations

from atlas_api.modules.dashboard.router import (
    STATE_KEY,
    DashboardModuleContext,
    router,
)
from atlas_api.modules.dashboard.service import DashboardService
from atlas_api.modules.public import ModuleDef


def build_dashboard_module(env: str = "development") -> ModuleDef:
    """Composition root for the Spec 09 Dashboard & Analytics module."""
    service = DashboardService()
    context = DashboardModuleContext(service=service)

    return ModuleDef(
        name="dashboard",
        version="1.0.0",
        owner="cockpit-engine",
        router=router,
        app_state={STATE_KEY: context},
        health_probes={},
        subscriptions=(),
    )


__all__ = [
    "build_dashboard_module",
    "DashboardService",
]
