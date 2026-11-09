"""The intelligence module's only legal import surface (docs/module-conventions.md)."""

from atlas_api.modules.intelligence.router import build_intelligence_module

__all__ = ["build_intelligence_module"]
