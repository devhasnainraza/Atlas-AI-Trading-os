"""Auth module v1 API + module definition.

The module owns its own composition root: :func:`build_auth_module` resolves settings once,
validates them against the deployment environment, and hands the result to the app as module
state. Routes read it back off ``request.app.state``, so two composed apps never share a token
signer or a lockout counter.

Routers are split by surface rather than kept in one object because they carry different
authorization and rate-limit classes: ``/auth/*`` is unauthenticated and rate-limited hardest,
``/admin/*`` requires admin permissions plus fresh step-up, ``/privacy/*`` is per-user and
slow. Splitting them makes the class of each route visible in the file layout.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from atlas_api.modules.auth.deps import STATE_KEY, AuthModuleContext, get_auth_context
from atlas_api.modules.auth.settings import AuthSettings, OAuthSettings
from atlas_api.modules.public import ModuleDef
from atlas_core.config import Environment

if TYPE_CHECKING:
    from atlas_api.modules.auth.service.tokens import TokenService

#: Unauthenticated entry points: register, verify, login, refresh, logout, magic link, OAuth.
router = APIRouter(prefix="/auth", tags=["auth"])

#: Session and device management. Declares full paths (``/sessions``, ``/devices``) so both
#: live under one authorization class without nesting them under ``/auth``.
sessions_router = APIRouter(tags=["auth:sessions"])

mfa_router = APIRouter(prefix="/mfa", tags=["auth:mfa"])
security_router = APIRouter(prefix="/security", tags=["auth:security"])
admin_router = APIRouter(prefix="/admin", tags=["auth:admin"])
api_keys_router = APIRouter(prefix="/api-keys", tags=["auth:api-keys"])
privacy_router = APIRouter(prefix="/privacy", tags=["auth:privacy"])

#: Mounted at the application root so OIDC-compatible verifiers find it at the expected
#: ``/.well-known/jwks.json`` path. The composer includes this via ``root_routers``.
jwks_router = APIRouter(tags=["auth:jwks"])


@jwks_router.get("/.well-known/jwks.json", include_in_schema=False)
async def jwks(request: Request) -> JSONResponse:
    """Public JWKS endpoint. Returns the set of active signing keys.

    ``include_in_schema=False`` because the path is a well-known URL, not a versioned API route.
    OpenAPI would list it under the version prefix otherwise.
    """
    ctx = get_auth_context(request)
    return JSONResponse(ctx.token_service.ring.jwks())


def build_auth_module(
    *,
    env: Environment,
    settings: AuthSettings | None = None,
    oauth: OAuthSettings | None = None,
    token_service: TokenService | None = None,
) -> ModuleDef:
    """Compose the auth module.

    ``env`` is required rather than defaulted. A default would mean a deployment that forgot to
    pass it silently skips the key-material checks in
    :meth:`AuthSettings.validate_for_environment` — the exact failure that check exists to
    prevent. A missing argument is a ``TypeError`` at composition time instead.

    ``token_service`` is injected so tests can supply a seeded mock. When omitted, the factory
    builds one from ``settings`` — with an ephemeral in-memory key for local/test environments
    (where ``validate_for_environment`` permits absent key files) and from the configured paths
    for deployed environments.
    """
    from atlas_api.modules.auth.service.tokens import TokenService as _TokenService

    resolved = settings or AuthSettings()
    resolved.validate_for_environment(env)
    resolved_oauth = oauth or OAuthSettings()

    if token_service is None:
        allow_ephemeral = env in (Environment.LOCAL, Environment.TEST)
        token_service = _TokenService.from_settings(resolved, allow_ephemeral=allow_ephemeral)

    context = AuthModuleContext(
        settings=resolved, oauth=resolved_oauth, token_service=token_service
    )

    return ModuleDef(
        name="auth",
        version="1.0.0",
        owner="platform-security",
        router=router,
        routers_extra=(
            sessions_router,
            mfa_router,
            security_router,
            admin_router,
            api_keys_router,
            privacy_router,
        ),
        root_routers=(jwks_router,),
        app_state={STATE_KEY: context},
    )


__all__ = ["build_auth_module"]
