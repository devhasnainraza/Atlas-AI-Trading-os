"""Public interface and composition root for AI Marketplace module (Spec 12 §2, §5)."""

from __future__ import annotations

from atlas_api.modules.marketplace.router import (
    STATE_KEY,
    MarketplaceModuleContext,
    router,
)
from atlas_api.modules.marketplace.service import MarketplaceService
from atlas_api.modules.public import ModuleDef


def build_marketplace_module(env: str = "development") -> ModuleDef:
    """Composition root for the Spec 12 AI Marketplace module."""
    service = MarketplaceService()
    context = MarketplaceModuleContext(service=service)

    return ModuleDef(
        name="marketplace",
        version="1.0.0",
        owner="marketplace-core",
        router=router,
        app_state={STATE_KEY: context},
        health_probes={},
        subscriptions=(),
    )


__all__ = [
    "build_marketplace_module",
    "MarketplaceService",
]
