"""Public composition root for Evaluation module (prompt.md Feature 8)."""

from __future__ import annotations

from atlas_api.modules.evaluation.router import (
    STATE_KEY,
    EvaluationModuleContext,
    router,
)
from atlas_api.modules.evaluation.service import EvaluationService
from atlas_api.modules.public import ModuleDef


def build_evaluation_module(env: str = "development") -> ModuleDef:
    """Composition root for the Historical Scenario Evaluation module."""
    service = EvaluationService()
    context = EvaluationModuleContext(service=service)

    return ModuleDef(
        name="evaluation",
        version="1.0.0",
        owner="evaluation-core",
        router=router,
        app_state={STATE_KEY: context},
        health_probes={},
        subscriptions=(),
    )


__all__ = [
    "build_evaluation_module",
    "EvaluationService",
]
