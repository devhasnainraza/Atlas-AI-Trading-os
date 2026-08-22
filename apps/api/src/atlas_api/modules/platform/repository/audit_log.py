"""Platform module audit-log repository surface.

The port, entry shape, and in-memory reference adapter live in ``atlas_core.audit``
alongside the other in-memory adapters, so the composition root can hold an audit log
without depending on this module. This module is where the platform module's storage
implementation goes — the Postgres adapter (no UPDATE/DELETE grants) lands here with the
first persistent deployment.
"""

from __future__ import annotations

from atlas_core.audit import AuditLogEntry, AuditLogRepository, InMemoryAuditLog

__all__ = ["AuditLogEntry", "AuditLogRepository", "InMemoryAuditLog"]
