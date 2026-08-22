"""Audit log entry — re-exported from the shared contract (FR-047).

The canonical definition lives in ``atlas_core.audit`` so the composition root and other
modules can record audit entries without importing this module's internals. This module
keeps the platform module's domain surface intact for readers who start here.
"""

from __future__ import annotations

from atlas_core.audit import AuditLogEntry

__all__ = ["AuditLogEntry"]
