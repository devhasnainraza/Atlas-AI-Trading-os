"""Credential vault v1 API + module definition.

Two routers, because they answer different questions: ``/credentials`` manages secret material
the user pasted in, ``/connected-accounts`` manages the *relationships* those secrets enable
(which broker, what permissions the key actually has, when it was last reachable). A user
revoking a credential and disconnecting an account are different intents with different
consequences, and the URL should say which.
"""

from __future__ import annotations

from fastapi import APIRouter

from atlas_api.modules.credentials.deps import STATE_KEY, CredentialsModuleContext
from atlas_api.modules.credentials.settings import VaultSettings
from atlas_api.modules.public import ModuleDef
from atlas_core.config import Environment

router = APIRouter(prefix="/credentials", tags=["credentials"])
accounts_router = APIRouter(prefix="/connected-accounts", tags=["credentials:accounts"])


def build_credentials_module(
    *,
    env: Environment,
    settings: VaultSettings | None = None,
) -> ModuleDef:
    """Compose the credential vault module.

    ``env`` is required for the same reason as in the auth module, and here it carries the
    sharpest single check in the codebase: :meth:`VaultSettings.validate_for_environment`
    refuses to start a staging or production process whose vault root key came from an
    environment variable.
    """
    resolved = settings or VaultSettings()
    resolved.validate_for_environment(env)
    context = CredentialsModuleContext(settings=resolved)

    return ModuleDef(
        name="credentials",
        version="1.0.0",
        owner="platform-security",
        router=router,
        routers_extra=(accounts_router,),
        app_state={STATE_KEY: context},
    )


__all__ = ["build_credentials_module"]
