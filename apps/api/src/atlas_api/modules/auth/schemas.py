"""Auth module request/response schemas — strict validation.

Three module-wide rules:

* **Writes set ``extra="forbid"``.** A typo'd field on a security-relevant request must be a
  422, not a silently ignored instruction — ``mfa_code`` accepted as "no code supplied" is how
  a second factor gets skipped.
* **No response model may declare a field that can hold secret material.** Not the password
  hash, not the TOTP secret, not a token hash, not a credential value. This is enforced
  structurally (the field does not exist) rather than by a runtime check, and asserted by a
  contract test.
* **Secrets inbound are ``SecretStr``.** They must never land in a validation error, a log
  line, or a ``repr`` of the request model — which is exactly what an unhandled 422 prints.

Route models land story by story; the bases below are the shared contract.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AuthRequest(BaseModel):
    """Base for every inbound auth payload.

    ``str_strip_whitespace`` matters for more than tidiness: a trailing space on a pasted
    verification code or email address should not be the reason a legitimate user is rejected.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AuthResponse(BaseModel):
    """Base for every outbound auth payload.

    Also ``extra="forbid"`` — on a response model that turns an accidental extra field into a
    failing test rather than a quiet data leak.
    """

    model_config = ConfigDict(extra="forbid")


class AcknowledgedResponse(AuthResponse):
    """Deliberately uninformative acknowledgement.

    Returned by register, forgot-password, magic-link request, and resend — every endpoint that
    takes an email address. The response is identical whether or not the address exists, which
    is what keeps these endpoints from being an account-enumeration oracle (FR-023).
    """

    #: Always the same string for a given endpoint. Never "user not found", never "email sent
    #: to <address>" — either would leak existence.
    detail: str


__all__ = ["AcknowledgedResponse", "AuthRequest", "AuthResponse"]
