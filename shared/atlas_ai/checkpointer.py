"""LangGraph checkpoint persistence adapters (Spec 03 FR-004, NFR-003)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class CheckpointRecord:
    thread_id: str
    checkpoint_ns: str
    checkpoint_id: str
    parent_checkpoint_id: str | None
    state: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CheckpointSaver:
    """Interface for saving and retrieving LangGraph execution thread states."""

    async def put(
        self,
        thread_id: str,
        checkpoint_ns: str,
        checkpoint_id: str,
        parent_checkpoint_id: str | None,
        state: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError

    async def get(
        self,
        thread_id: str,
        checkpoint_ns: str = "",
        checkpoint_id: str | None = None,
    ) -> CheckpointRecord | None:
        raise NotImplementedError

    async def list_checkpoints(self, thread_id: str) -> list[CheckpointRecord]:
        raise NotImplementedError


class InMemoryCheckpointSaver(CheckpointSaver):
    """In-memory checkpointer for testing and lightweight execution."""

    def __init__(self) -> None:
        # Key: (thread_id, checkpoint_ns, checkpoint_id)
        self._storage: dict[tuple[str, str, str], CheckpointRecord] = {}

    async def put(
        self,
        thread_id: str,
        checkpoint_ns: str,
        checkpoint_id: str,
        parent_checkpoint_id: str | None,
        state: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        record = CheckpointRecord(
            thread_id=thread_id,
            checkpoint_ns=checkpoint_ns,
            checkpoint_id=checkpoint_id,
            parent_checkpoint_id=parent_checkpoint_id,
            state=state.copy(),
            metadata=metadata or {},
        )
        self._storage[(thread_id, checkpoint_ns, checkpoint_id)] = record

    async def get(
        self,
        thread_id: str,
        checkpoint_ns: str = "",
        checkpoint_id: str | None = None,
    ) -> CheckpointRecord | None:
        if checkpoint_id:
            return self._storage.get((thread_id, checkpoint_ns, checkpoint_id))

        # Get the latest checkpoint for the thread
        matching = [
            r for (t, ns, _), r in self._storage.items()
            if t == thread_id and ns == checkpoint_ns
        ]
        if not matching:
            return None
        matching.sort(key=lambda x: x.created_at, reverse=True)
        return matching[0]

    async def list_checkpoints(self, thread_id: str) -> list[CheckpointRecord]:
        matching = [
            r for (t, _, _), r in self._storage.items()
            if t == thread_id
        ]
        matching.sort(key=lambda x: x.created_at)
        return matching
