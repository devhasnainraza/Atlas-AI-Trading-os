"""Auth module dependencies and per-app composition context.

Split out from ``router.py`` because this module has many routers (auth, sessions, MFA,
security, admin, API keys, privacy) that all need the same context, and a shared accessor is
better than each router reaching into app state itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import Request

from atlas_api.modules.auth.settings import AuthSettings, OAuthSettings
from atlas_core.errors import InternalError

if TYPE_CHECKING:
    from atlas_api.modules.auth.service.tokens import TokenService

#: ``app.state`` key holding this module's :class:`AuthModuleContext`.
STATE_KEY = "auth_context"


@dataclass(frozen=True)
class AuthModuleContext:
    """Per-build auth state. One instance per composed app.

    Frozen and per-app rather than a module-level singleton: two apps composed in one test
    process must not share a token signer, a session store, or a lockout counter, or a test
    that locks an account would lock it for every other test too.
    """

    settings: AuthSettings
    oauth: OAuthSettings
    token_service: TokenService


def get_auth_context(request: Request) -> AuthModuleContext:
    """The module's composition root, read off the app it belongs to.

    Raises rather than lazily building one: a route reachable before the module was composed
    means the app was assembled wrong, and a second context would sign tokens with a different
    key than the JWKS endpoint publishes.
    """
    context = getattr(request.app.state, STATE_KEY, None)
    if not isinstance(context, AuthModuleContext):  # pragma: no cover - composition guard
        raise InternalError(internal_context={"detail": "auth module accessed before composition"})
    return context


__all__ = ["STATE_KEY", "AuthModuleContext", "get_auth_context"]
