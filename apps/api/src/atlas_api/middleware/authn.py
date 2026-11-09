"""Authentication middleware (T012; plan §1, §6).

The seam every route can rely on: by the time a request reaches a handler, either it
carries a verified principal or it has been rejected. There is no third state —
deny-by-default means the middleware authenticates everything and the public path list
is an explicit exemption list, not an opt-in.

Token sources, in precedence order:

1. ``Authorization: Bearer <jwt>`` — API clients and mobile.
2. ``__Host-access`` cookie — the browser session. ``__Host-`` is not decoration: it
   pins the cookie to exactly this origin, HTTPS, no Domain, no Path games, so a
   subdomain takeover or a injected ``Set-Cookie`` cannot widen its scope.

A request carrying both is served the bearer token (the more explicit statement of
intent) — but only after it verifies; a bad bearer header never falls through to the
cookie, because that fallback would turn a token bug into a silent downgrade.

Revocation: access JWTs are short-lived (15 min), so normal routes accept a revoked
session for at most that long — the documented tradeoff (plan §6). Sensitive routes
(vault, admin, privacy, MFA, session management) additionally check the session id
against a denylist, and *fail closed*: if the denylist store is unreachable, the
request is refused with 503. A vault read that "might" be a stolen session is not a
degradation anyone should get to choose.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from atlas_api.modules.auth.deps import STATE_KEY as AUTH_STATE_KEY
from atlas_api.modules.auth.deps import AuthModuleContext
from atlas_api.modules.auth.service.tokens import TokenError, VerifiedToken
from atlas_core.correlation import get_correlation_id
from atlas_core.errors import (
    AtlasError,
    AuthenticationError,
    DependencyUnavailableError,
    InternalError,
    TokenInvalidError,
)
from atlas_observability import get_logger

logger = get_logger("atlas_api.authn")

#: The access-token cookie. ``__Host-`` prefix requirements (Secure, no Domain, Path=/)
#: are enforced by the browser; the name here must match what the session service sets.
ACCESS_COOKIE_NAME = "__Host-access"

#: Paths that are reachable without a principal. Exact prefixes; anything not listed
#: requires authentication. The auth endpoints themselves are here — login cannot
#: require being logged in.
PUBLIC_PATHS: tuple[str, ...] = (
    "/v1/auth/",
    "/v1/health",
    "/v1/platform/",
    "/.well-known/",
    "/docs",
    "/openapi.json",
    "/redoc",
)

#: Route classes where a revoked-but-unexpired JWT must not get through, and where a
#: denylist outage means refusal rather than hope (plan §6, Constitution IX fail-closed).
SENSITIVE_PATHS: tuple[str, ...] = (
    "/v1/credentials",
    "/v1/connected-accounts",
    "/v1/admin",
    "/v1/privacy",
    "/v1/security",
    "/v1/sessions",
    "/v1/devices",
    "/v1/mfa",
    "/v1/api-keys",
)


@dataclass(frozen=True)
class Principal:
    """The verified caller, attached to ``request.state.principal``.

    Carries what the JWT proved, nothing more. Permission resolution (RBAC, T035)
    reads ``user_id``/``roles_version`` and consults the role cache; this object is
    authentication, not authorization, and the type name keeps the two visible.
    """

    user_id: str
    session_id: str
    roles_version: int
    mfa: bool

    @classmethod
    def from_token(cls, token: VerifiedToken) -> Principal:
        return cls(
            user_id=token.subject,
            session_id=token.session_id,
            roles_version=token.roles_version,
            mfa=token.mfa,
        )


class RevocationChecker(Protocol):
    """Is this session id revoked? Implementations must be fast (Redis) and the
    middleware treats their exceptions as *revoked* on sensitive routes."""

    async def is_revoked(self, session_id: str) -> bool: ...


class AllowAllRevocations:
    """Local/test stand-in: nothing is ever revoked.

    Not a fail-open shortcut for production — production composition wires the Redis
    implementation (T015/T026); this exists so a local app runs without Redis.
    """

    async def is_revoked(self, session_id: str) -> bool:
        return False


class InMemoryRevocations:
    """A denylist backed by a set — used by tests and single-process dev."""

    def __init__(self, revoked: Iterable[str] = ()) -> None:
        self._revoked = set(revoked)

    def revoke(self, session_id: str) -> None:
        self._revoked.add(session_id)

    async def is_revoked(self, session_id: str) -> bool:
        return session_id in self._revoked


def _error(err: AtlasError) -> JSONResponse:
    """Render an :class:`AtlasError` as the standard envelope.

    The middleware sits outside Starlette's ``ExceptionMiddleware``, so raising an
    ``AtlasError`` here would not reach the app's exception handler — it builds the response
    directly. Driving it from the error instance (not hand-written strings) keeps code,
    message, and status single-sourced in :mod:`atlas_core.errors`.
    """
    return JSONResponse(status_code=err.http_status, content=err.to_envelope(get_correlation_id()))


class AuthMiddleware(BaseHTTPMiddleware):
    """Verify the access token and attach a :class:`Principal`, or reject.

    Constructed per app with the revocation checker injected; the token service is read
    from ``app.state`` lazily so middleware ordering (this runs before module
    composition completes at import time, not request time) does not matter.
    """

    def __init__(
        self,
        app,
        *,
        revocations: RevocationChecker | None = None,
        public_paths: tuple[str, ...] = PUBLIC_PATHS,
        sensitive_paths: tuple[str, ...] = SENSITIVE_PATHS,
    ) -> None:
        super().__init__(app)
        self._revocations = revocations or AllowAllRevocations()
        self._public = public_paths
        self._sensitive = sensitive_paths

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if any(path.startswith(prefix) for prefix in self._public):
            return await call_next(request)

        token = self._extract_token(request)
        if token is None:
            return _error(AuthenticationError())

        ctx: AuthModuleContext | None = getattr(request.app.state, AUTH_STATE_KEY, None)
        if ctx is None:  # pragma: no cover - composition guard
            logger.error("auth_middleware_without_module", path=path)
            return _error(InternalError())

        try:
            verified = ctx.token_service.verify_access_token(token)
        except TokenError:
            # One message for every rejection reason (bad signature, expired, wrong
            # audience, unknown kid): the client does not get to learn which.
            return _error(TokenInvalidError())

        sensitive = any(path.startswith(prefix) for prefix in self._sensitive)
        if sensitive:
            try:
                revoked = await self._revocations.is_revoked(verified.session_id)
            except Exception:
                # Fail closed: an unreachable denylist on a sensitive route is a
                # refusal, not a shrug. Logged loudly because it is an outage signal.
                logger.exception("revocation_store_unreachable", path=path)
                return _error(DependencyUnavailableError())
            if revoked:
                # A revoked session is an invalid token — same code/message as any other
                # rejection, so "revoked" is not distinguishable from "expired" to a caller.
                return _error(TokenInvalidError())

        request.state.principal = Principal.from_token(verified)
        return await call_next(request)

    @staticmethod
    def _extract_token(request: Request) -> str | None:
        header = request.headers.get("authorization")
        if header:
            scheme, _, value = header.partition(" ")
            if scheme.lower() == "bearer" and value.strip():
                return value.strip()
            # A malformed Authorization header is a client bug, not an anonymous
            # request: do not fall through to the cookie and mask it.
            return None
        return request.cookies.get(ACCESS_COOKIE_NAME) or None


__all__ = [
    "ACCESS_COOKIE_NAME",
    "AllowAllRevocations",
    "AuthMiddleware",
    "InMemoryRevocations",
    "Principal",
    "PUBLIC_PATHS",
    "RevocationChecker",
    "SENSITIVE_PATHS",
]
