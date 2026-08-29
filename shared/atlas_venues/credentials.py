"""Per-operation credential access for adapters (Spec 03 plan §13, T021).

Spec 01 owns the real credential vault. Until it lands, adapters must still be written
against a stable contract, so this module defines the port they depend on:

    async with use_credential(credential_id, purpose="submit_order") as secret: ...

Three properties hold regardless of which provider is installed:

* material is fetched **per operation** and never cached on an adapter instance (FR-008);
* every access is recorded with its purpose, so the audit trail shows why a secret was read;
* the value never reaches ``__repr__``, logs, or an event payload — :class:`CredentialSecret`
  refuses to render itself.

When Spec 01 ships, its module registers a real provider via :func:`set_credential_provider`
and no adapter code changes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


class CredentialError(RuntimeError):
    """The credential could not be resolved, is revoked, or is not permitted for this use."""


class CredentialSecret:
    """A borrowed secret that refuses to render itself.

    ``str()``, ``repr()``, and f-strings all yield a redaction marker. Reading the real value
    requires the explicit :meth:`reveal` call, which makes every disclosure point greppable.
    """

    __slots__ = ("_fields", "_credential_id")

    def __init__(self, credential_id: str, fields: Mapping[str, str]) -> None:
        self._credential_id = credential_id
        self._fields = dict(fields)

    def reveal(self, field_name: str) -> str:
        try:
            return self._fields[field_name]
        except KeyError as exc:
            raise CredentialError(
                f"credential {self._credential_id} has no field {field_name!r}"
            ) from exc

    def has(self, field_name: str) -> bool:
        return field_name in self._fields

    @property
    def credential_id(self) -> str:
        return self._credential_id

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<CredentialSecret {self._credential_id} [REDACTED]>"

    __str__ = __repr__

    def __format__(self, spec: str) -> str:
        return repr(self)


@dataclass(frozen=True, slots=True)
class CredentialAccessRecord:
    """One audited read of credential material."""

    credential_id: str
    purpose: str
    accessed_at: datetime
    correlation_id: str | None = None


class CredentialProvider(Protocol):
    """The port Spec 01's credential vault will implement."""

    async def fetch(self, credential_id: str, *, purpose: str) -> CredentialSecret: ...

    def access_log(self) -> tuple[CredentialAccessRecord, ...]: ...


@dataclass
class InMemoryCredentialProvider:
    """Reference implementation for tests and local development.

    Holds material in process only. This is *not* the vault: it performs no envelope
    encryption and no KMS round trip, and it is never registered in a deployed environment.
    """

    _store: dict[str, dict[str, str]] = field(default_factory=dict)
    _accesses: list[CredentialAccessRecord] = field(default_factory=list)
    _revoked: set[str] = field(default_factory=set)

    def put(self, credential_id: str, fields: Mapping[str, str]) -> None:
        self._store[credential_id] = dict(fields)
        self._revoked.discard(credential_id)

    def revoke(self, credential_id: str) -> None:
        self._revoked.add(credential_id)
        self._store.pop(credential_id, None)

    async def fetch(self, credential_id: str, *, purpose: str) -> CredentialSecret:
        from atlas_core.correlation import get_correlation_id

        if credential_id in self._revoked:
            raise CredentialError(f"credential {credential_id} has been revoked")
        try:
            fields = self._store[credential_id]
        except KeyError as exc:
            raise CredentialError(f"unknown credential {credential_id}") from exc
        self._accesses.append(
            CredentialAccessRecord(
                credential_id=credential_id,
                purpose=purpose,
                accessed_at=_utcnow(),
                correlation_id=get_correlation_id(),
            )
        )
        return CredentialSecret(credential_id, fields)

    def access_log(self) -> tuple[CredentialAccessRecord, ...]:
        return tuple(self._accesses)


def _utcnow() -> datetime:
    from datetime import UTC

    return datetime.now(UTC)


_provider: CredentialProvider = InMemoryCredentialProvider()


def set_credential_provider(provider: CredentialProvider) -> None:
    """Install the process-wide provider (Spec 01's vault, in a deployed environment)."""
    global _provider
    _provider = provider


def get_credential_provider() -> CredentialProvider:
    return _provider


@asynccontextmanager
async def use_credential(credential_id: str, *, purpose: str) -> AsyncIterator[CredentialSecret]:
    """Borrow credential material for the duration of a single operation.

    The secret is scoped to the ``async with`` block by convention; adapters must not stash
    it on ``self``. ``purpose`` is recorded in the access log and should name the operation
    ("submit_order", "verify_permissions"), not the caller.
    """
    if not purpose:
        raise CredentialError("purpose is required for credential access")
    secret = await _provider.fetch(credential_id, purpose=purpose)
    try:
        yield secret
    finally:
        del secret


__all__ = [
    "CredentialAccessRecord",
    "CredentialError",
    "CredentialProvider",
    "CredentialSecret",
    "InMemoryCredentialProvider",
    "get_credential_provider",
    "set_credential_provider",
    "use_credential",
]
