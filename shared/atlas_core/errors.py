"""Platform error taxonomy (Spec 00 FR-038/039).

Every service returns errors in one envelope with a stable machine code. Internal detail
never crosses the API boundary — the middleware maps exceptions to envelopes and logs the
full context server-side only.
"""

from __future__ import annotations

from typing import Any


class AtlasError(Exception):
    """Base class for all platform errors.

    Subclasses define a stable ``code`` (never renumbered) and the HTTP status they map
    to. ``message`` must always be user-safe; put internals in ``internal_context`` which
    is logged but never serialized to clients.
    """

    code: str = "ATLAS-INT-001"
    http_status: int = 500
    default_message: str = "An internal error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: list[dict[str, Any]] | None = None,
        internal_context: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or []
        self.internal_context = internal_context or {}
        super().__init__(self.message)

    def to_envelope(self, correlation_id: str) -> dict[str, Any]:
        error: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "correlation_id": correlation_id,
        }
        if self.details:
            error["details"] = self.details
        return {"error": error}


class ValidationError(AtlasError):
    code = "ATLAS-VAL-001"
    http_status = 422
    default_message = "The request is invalid."


class AuthenticationError(AtlasError):
    code = "ATLAS-AUTHN-001"
    http_status = 401
    default_message = "Authentication required."


class AuthorizationError(AtlasError):
    code = "ATLAS-AUTHZ-001"
    http_status = 403
    default_message = "You do not have permission to perform this action."


class NotFoundError(AtlasError):
    code = "ATLAS-NF-001"
    http_status = 404
    default_message = "The requested resource was not found."


class ConflictError(AtlasError):
    code = "ATLAS-CON-001"
    http_status = 409
    default_message = "The request conflicts with the current state."


class RateLimitedError(AtlasError):
    code = "ATLAS-RL-001"
    http_status = 429
    default_message = "Too many requests. Please retry later."

    def __init__(self, message: str | None = None, *, retry_after_seconds: int = 60, **kw: Any):
        super().__init__(message, **kw)
        self.retry_after_seconds = retry_after_seconds


class DependencyUnavailableError(AtlasError):
    code = "ATLAS-DEP-001"
    http_status = 503
    default_message = "A required dependency is temporarily unavailable."


class InternalError(AtlasError):
    code = "ATLAS-INT-001"
    http_status = 500
    default_message = "An internal error occurred."


# --- Auth & credential-vault taxonomy (Spec 02 plan §20; T014) ---------------------------
#
# Enumeration resistance is a design constraint on these messages, not a nicety: the login
# path answers "wrong password" and "no such user" with the *same* code and the *same*
# message (InvalidCredentialsError), so a caller cannot probe which emails are registered.
# Likewise, lockout and MFA states must not leak remaining-attempt counts or which factor is
# enrolled beyond what the UX strictly requires. Codes are stable — never renumbered.


class InvalidCredentialsError(AtlasError):
    """Wrong password *or* unknown user — deliberately one code, one message (FR-023)."""

    code = "ATLAS-AUTH-001"
    http_status = 401
    default_message = "Invalid email or password."


class AccountLockedError(AtlasError):
    """Too many failed attempts. Message reveals only that the account is temporarily
    locked — never the attempt count or the exact unlock time."""

    code = "ATLAS-AUTH-002"
    http_status = 403
    default_message = "This account is temporarily locked. Please try again later."


class MfaRequiredError(AtlasError):
    """Password verified; a second factor must still be presented. The response carries an
    ``mfa_token`` (details) so the client can continue the challenge."""

    code = "ATLAS-AUTH-003"
    http_status = 403
    default_message = "Multi-factor authentication is required."


class MfaInvalidError(AtlasError):
    """The submitted factor code/recovery code is wrong or expired. Same message whether the
    factor is TOTP or a recovery code, so it does not enumerate which factors are enrolled."""

    code = "ATLAS-AUTH-004"
    http_status = 401
    default_message = "The authentication code is invalid or has expired."


class TokenExpiredError(AtlasError):
    """A refresh/access token is past its expiry. Distinct from invalid-token so the client
    knows a silent refresh is worth attempting rather than a full re-login."""

    code = "ATLAS-AUTH-005"
    http_status = 401
    default_message = "Your session has expired. Please sign in again."


class TokenInvalidError(AtlasError):
    """Signature, audience, issuer, or key-id check failed, or the session was revoked. One
    message for all of these: telling a caller *why* a token is rejected is an oracle."""

    code = "ATLAS-AUTH-006"
    http_status = 401
    default_message = "Invalid or expired credentials."


class ConsentRequiredError(AtlasError):
    """The action needs a consent the user has not granted (e.g. data-processing terms)."""

    code = "ATLAS-AUTH-007"
    http_status = 403
    default_message = "Additional consent is required to continue."


class VerificationRequiredError(AtlasError):
    """The account's email is not yet verified and the action requires it."""

    code = "ATLAS-AUTH-008"
    http_status = 403
    default_message = "Please verify your email address to continue."


class CsrfValidationError(AtlasError):
    """A cookie-authenticated mutation lacked a matching CSRF token. One message for
    missing and mismatched alike (see middleware/csrf.py)."""

    code = "ATLAS-CSRF-001"
    http_status = 403
    default_message = "The request could not be verified. Please reload and try again."


class CredentialNotFoundError(AtlasError):
    """No credential with that id for this user. Same response whether the id is unknown or
    belongs to another user, so it does not enumerate other tenants' identifiers."""

    code = "ATLAS-CRED-001"
    http_status = 404
    default_message = "The credential was not found."


class CredentialUnavailableError(AtlasError):
    """The credential exists but cannot be used now (revoked, or its account is disconnected)."""

    code = "ATLAS-CRED-002"
    http_status = 409
    default_message = "This credential is not available."


class VaultCryptoError(AtlasError):
    """Envelope encrypt/decrypt failed — tampering, wrong KEK, or AAD mismatch. Deliberately
    generic (FR-023): the client is never told *which* crypto check failed; that lives in
    ``internal_context`` server-side only."""

    code = "ATLAS-CRED-003"
    http_status = 500
    default_message = "The credential could not be processed."


class VaultKeyError(AtlasError):
    """The key-management layer is unavailable or misconfigured (KEK unreachable). Fail-closed:
    a vault that cannot reach its root key refuses rather than serving stale material."""

    code = "ATLAS-CRED-004"
    http_status = 503
    default_message = "The secure vault is temporarily unavailable."
