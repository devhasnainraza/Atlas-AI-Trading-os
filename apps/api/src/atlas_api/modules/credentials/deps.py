"""Credential vault dependencies and per-app composition context."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from atlas_api.modules.credentials.settings import VaultSettings
from atlas_core.errors import InternalError

#: ``app.state`` key holding this module's :class:`CredentialsModuleContext`.
STATE_KEY = "credentials_context"


@dataclass(frozen=True)
class CredentialsModuleContext:
    """Per-build vault state. One instance per composed app.

    Holds the crypto layer (added in T010) so that key material is created once per app and
    never as a module-level global — a test that swaps in an ephemeral KEK must not leave that
    KEK visible to the next test.
    """

    settings: VaultSettings


def get_credentials_context(request: Request) -> CredentialsModuleContext:
    """The module's composition root, read off the app it belongs to."""
    context = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(context, CredentialsModuleContext):  # pragma: no cover - guard
        raise InternalError(
            internal_context={"detail": "credentials module accessed before composition"}
        )
    return context


__all__ = ["STATE_KEY", "CredentialsModuleContext", "get_credentials_context"]
