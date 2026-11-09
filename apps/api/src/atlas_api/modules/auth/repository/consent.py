"""Consent-record persistence (T024).

Append-only by design (data-model.md): a consent decision is a legal fact, so it is never
updated — a new decision is a new row, and the *latest* row per ``(user, document)`` is the
current state while the full history is preserved. There is no ``update`` on this port on
purpose; the only writes are :meth:`ConsentRepository.record` (append) and reads.

The queries the registration service (T025) and the re-consent prompt need:

* :meth:`latest_for_user` — the current grant state of every document, for the "have you
  accepted the current terms?" check.
* :meth:`latest` — one document's current row, for a targeted re-consent decision.

Both resolve "latest" by ``occurred_at`` (the append timestamp), which is why the index is on
``(user_id, document)`` and the read sorts within it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atlas_api.modules.auth.repository.tables import ConsentRecordTable


@dataclass(frozen=True)
class ConsentRecord:
    id: uuid.UUID
    user_id: uuid.UUID
    document: str
    document_version: str
    granted: bool
    ip: str | None = None
    user_agent: str | None = None
    occurred_at: datetime | None = None


def _to_domain(row: ConsentRecordTable) -> ConsentRecord:
    return ConsentRecord(
        id=row.id,
        user_id=row.user_id,
        document=row.document,
        document_version=row.document_version,
        granted=row.granted,
        ip=row.ip,
        user_agent=row.user_agent,
        occurred_at=row.occurred_at,
    )


class ConsentRepository(Protocol):
    """Port for the append-only consent ledger. No update method exists — by design."""

    async def record(self, consent: ConsentRecord) -> ConsentRecord: ...

    async def latest(self, *, user_id: uuid.UUID, document: str) -> ConsentRecord | None: ...

    async def latest_for_user(self, user_id: uuid.UUID) -> dict[str, ConsentRecord]: ...

    async def history(self, *, user_id: uuid.UUID, document: str) -> list[ConsentRecord]: ...


class InMemoryConsentRepository:
    def __init__(self) -> None:
        self._rows: list[ConsentRecord] = []

    async def record(self, consent: ConsentRecord) -> ConsentRecord:
        self._rows.append(consent)
        return consent

    async def latest(self, *, user_id: uuid.UUID, document: str) -> ConsentRecord | None:
        matches = [r for r in self._rows if r.user_id == user_id and r.document == document]
        if not matches:
            return None
        return max(matches, key=_occurred)

    async def latest_for_user(self, user_id: uuid.UUID) -> dict[str, ConsentRecord]:
        current: dict[str, ConsentRecord] = {}
        for record in self._rows:
            if record.user_id != user_id:
                continue
            existing = current.get(record.document)
            if existing is None or _occurred(record) >= _occurred(existing):
                current[record.document] = record
        return current

    async def history(self, *, user_id: uuid.UUID, document: str) -> list[ConsentRecord]:
        matches = [r for r in self._rows if r.user_id == user_id and r.document == document]
        return sorted(matches, key=_occurred)


def _occurred(record: ConsentRecord) -> datetime:
    """A record appended through this port always carries ``occurred_at``; the fallback only
    covers a hand-built test fixture and never fires in production."""
    return record.occurred_at or datetime.min


class SqlConsentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, consent: ConsentRecord) -> ConsentRecord:
        row = ConsentRecordTable(
            id=consent.id,
            user_id=consent.user_id,
            document=consent.document,
            document_version=consent.document_version,
            granted=consent.granted,
            ip=consent.ip,
            user_agent=consent.user_agent,
        )
        # Only set occurred_at when the caller supplied one; otherwise leave the attribute
        # unset so the column's ``server_default now()`` applies. Passing None explicitly
        # would insert NULL and defeat the append timestamp.
        if consent.occurred_at is not None:
            row.occurred_at = consent.occurred_at
        self._session.add(row)
        await self._session.flush()
        return consent

    async def latest(self, *, user_id: uuid.UUID, document: str) -> ConsentRecord | None:
        result = await self._session.execute(
            select(ConsentRecordTable)
            .where(ConsentRecordTable.user_id == user_id, ConsentRecordTable.document == document)
            .order_by(ConsentRecordTable.occurred_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row is not None else None

    async def latest_for_user(self, user_id: uuid.UUID) -> dict[str, ConsentRecord]:
        # One query, then reduce to the newest per document in Python. A DISTINCT ON would do
        # it in SQL but ties the repository to the Postgres dialect; the row count per user is
        # small (a handful of documents × a few re-consents), so the reduce is cheaper than the
        # dialect lock-in.
        result = await self._session.execute(
            select(ConsentRecordTable)
            .where(ConsentRecordTable.user_id == user_id)
            .order_by(ConsentRecordTable.document, ConsentRecordTable.occurred_at)
        )
        current: dict[str, ConsentRecord] = {}
        for row in result.scalars().all():
            domain = _to_domain(row)
            current[domain.document] = domain  # ascending order → last write per doc is newest
        return current

    async def history(self, *, user_id: uuid.UUID, document: str) -> list[ConsentRecord]:
        result = await self._session.execute(
            select(ConsentRecordTable)
            .where(ConsentRecordTable.user_id == user_id, ConsentRecordTable.document == document)
            .order_by(ConsentRecordTable.occurred_at)
        )
        return [_to_domain(row) for row in result.scalars().all()]


__all__ = [
    "ConsentRecord",
    "ConsentRepository",
    "InMemoryConsentRepository",
    "SqlConsentRepository",
]
