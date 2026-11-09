"""CSRF double-submit middleware (T013; plan §6).

The threat: a browser sends cookies automatically, so a page on ``evil.example`` can make
the user's browser fire a state-changing request at our API with the ``__Host-access``
session cookie attached. SameSite=Lax already blocks the cross-site *POST* case, but
double-submit is defense-in-depth and the plan calls for both (plan §6, risk table).

The mechanism, and why it needs no server state:

* At login the session service sets a ``__Host-csrf`` cookie whose value is a random token
  (:func:`issue_csrf_token` / :func:`set_csrf_cookie`). It is *not* stored anywhere server-side.
* The client echoes that value in the ``X-CSRF-Token`` header on every mutating request.
* We check that the header equals the cookie. An attacker's cross-origin page can *send* the
  cookie (browsers do that) but cannot *read* it to copy into a header — the same-origin policy
  is the whole security argument. Forging a matching pair requires setting a cookie on our
  origin, which ``__Host-`` (Secure, no Domain, Path=/) makes impossible from a subdomain.

Scope: only cookie-authenticated mutations are checked. A bearer-token request cannot be
CSRF'd (a browser will not attach an ``Authorization`` header to a cross-site request), so
requiring CSRF there would only burden API clients for no security. We detect the cookie case
by the presence of the access cookie, keeping this middleware independent of authN ordering.
"""

from __future__ import annotations

import hmac
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from atlas_api.middleware.authn import ACCESS_COOKIE_NAME
from atlas_core.correlation import get_correlation_id
from atlas_core.errors import AtlasError, CsrfValidationError
from atlas_observability import get_logger

logger = get_logger("atlas_api.csrf")

#: The double-submit cookie and its matching header. Names are part of the client contract.
CSRF_COOKIE_NAME = "__Host-csrf"
CSRF_HEADER_NAME = "x-csrf-token"

#: Methods that never change state and are therefore exempt. OPTIONS is the CORS preflight,
#: which by design cannot carry custom headers, so checking it would break every preflight.
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

#: Token entropy. 32 bytes urlsafe-encoded — same shape as one-time tokens; the value is a
#: capability the browser holds, not a secret we derive, so plain CSPRNG output is correct.
_TOKEN_BYTES = 32


def issue_csrf_token() -> str:
    """A fresh CSRF token. Called by the session service at login, not by this middleware."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def set_csrf_cookie(response: Response, token: str) -> None:
    """Attach the ``__Host-csrf`` cookie to a response.

    ``__Host-`` requirements are enforced by the browser and are non-negotiable here:
    ``secure=True``, ``httponly=False`` (the client JS must read it to echo the header),
    ``samesite="Lax"``, ``path="/"``, and no domain. A ``domain`` argument would break the
    prefix, so there is deliberately none to pass.
    """
    response.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        secure=True,
        httponly=False,
        samesite="lax",
        path="/",
    )


def _error(err: AtlasError) -> JSONResponse:
    """Render an :class:`AtlasError` as the standard envelope (see middleware/authn.py for
    why the middleware builds the response rather than raising)."""
    return JSONResponse(status_code=err.http_status, content=err.to_envelope(get_correlation_id()))


class CsrfMiddleware(BaseHTTPMiddleware):
    """Reject cookie-authenticated mutations that lack a matching CSRF token.

    Runs after authN in the chain (plan §6: rate-limit → CSRF → authN → authZ), but does not
    depend on that: it decides "is this a cookie flow?" from the presence of the access cookie,
    so it behaves correctly wherever it sits relative to authN.
    """

    def __init__(
        self,
        app,
        *,
        exempt_paths: tuple[str, ...] = (),
    ) -> None:
        super().__init__(app)
        # Endpoints that authenticate by other means and carry no session cookie to protect —
        # e.g. the login endpoint itself, which sets the cookie rather than relying on one.
        self._exempt = exempt_paths

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in _SAFE_METHODS:
            return await call_next(request)

        if any(request.url.path.startswith(prefix) for prefix in self._exempt):
            return await call_next(request)

        # Bearer-authenticated requests cannot be forged cross-site; nothing to check. Only
        # the cookie case (access cookie present, no bearer header) is a CSRF surface.
        has_bearer = self._has_bearer(request)
        if has_bearer or request.cookies.get(ACCESS_COOKIE_NAME) is None:
            return await call_next(request)

        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)
        if not cookie_token or not header_token:
            return _error(CsrfValidationError())
        if not hmac.compare_digest(cookie_token, header_token):
            # Same error as missing: distinguishing them tells an attacker nothing useful,
            # and a mismatch is the interesting case to log.
            logger.warning("csrf_mismatch", path=request.url.path)
            return _error(CsrfValidationError())

        return await call_next(request)

    @staticmethod
    def _has_bearer(request: Request) -> bool:
        header = request.headers.get("authorization", "")
        scheme, _, value = header.partition(" ")
        return scheme.lower() == "bearer" and bool(value.strip())


__all__ = [
    "CSRF_COOKIE_NAME",
    "CSRF_HEADER_NAME",
    "CsrfMiddleware",
    "issue_csrf_token",
    "set_csrf_cookie",
]
