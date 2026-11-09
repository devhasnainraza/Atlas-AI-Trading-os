"""The decision module's only legal import surface (docs/module-conventions.md)."""

from atlas_api.modules.decision.router import build_decision_module

__all__ = ["build_decision_module"]
