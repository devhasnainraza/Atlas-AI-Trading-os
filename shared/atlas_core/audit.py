"""Audit trail contract (FR-047).

The entry shape and repository port live here, not in a module, because every module writes
audit entries and the composition root must be able to hold one without depending on
whichever module implements storage. The platform module owns the implementation and the
operator read API; anything that merely *records* an action needs only this file.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class AuditLogEntry:
    actor: str
    action: str  # verb.noun, e.g. "dlq.redrive", "flag.change", "replay.start"
    target: str
    correlation_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AuditLogRepository(Protocol):
    """Append-only by contract: no update or delete operation is exposed."""

    def append(self, entry: AuditLogEntry) -> None: ...

    def query(
        self,
        actor: str | None = None,
        action: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditLogEntry]: ...


_SECRET_MARKERS = ("secret", "password", "token", "api_key", "credential")


class InMemoryAuditLog:
    """Reference implementation, alongside the other in-memory adapters. The Postgres
    implementation (no UPDATE/DELETE grants) lands with the first persistent deployment.

    Append-only: no update or delete methods exist, by design.
    """

    def __init__(self) -> None:
        self._entries: list[AuditLogEntry] = []

    def append(self, entry: AuditLogEntry) -> None:
        for key in entry.metadata:
            if any(marker in key.lower() for marker in _SECRET_MARKERS):
                raise ValueError(f"Audit metadata may not contain secret-shaped key '{key}'")
        self._entries.append(entry)

    def query(
        self,
        actor: str | None = None,
        action: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditLogEntry]:
        results = [
            e
            for e in self._entries
            if (actor is None or e.actor == actor)
            and (action is None or e.action == action)
            and (since is None or e.occurred_at >= since)
            and (until is None or e.occurred_at <= until)
        ]
        return results[-limit:]
