"""Platform module public interface — the ONLY legal import surface for other modules."""

from __future__ import annotations

from atlas_api.modules.platform.router import build_platform_module

__all__ = ["build_platform_module"]
