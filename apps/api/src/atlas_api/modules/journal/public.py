"""Public composition root for Memory, Journal & Learning module (Spec 07 §2, §9)."""

from __future__ import annotations

from atlas_api.modules.journal.router import (
    STATE_KEY,
    JournalModuleContext,
    router,
)
from atlas_api.modules.journal.service import JournalService
from atlas_api.modules.public import ModuleDef


def build_journal_module(env: str = "development") -> ModuleDef:
    """Composition root for the Spec 07 Memory, Journal & Learning module."""
    service = JournalService()
    context = JournalModuleContext(service=service)

    return ModuleDef(
        name="journal",
        version="1.0.0",
        owner="learning-engine",
        router=router,
        app_state={STATE_KEY: context},
        health_probes={},
        subscriptions=(),
    )


__all__ = [
    "build_journal_module",
    "JournalService",
]
