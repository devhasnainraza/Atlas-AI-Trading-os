"""Credential vault request/response schemas.

The load-bearing rule: **no response model in this module declares a field that could carry a
secret value.** Reads expose ``masked_hint`` (trailing characters only) plus metadata. There is
no admin variant, no ``?reveal=true``, and no debug mode that changes this — the field simply
does not exist, so no permission bug can expose it and no logging change can print it.

Inbound secret values are ``SecretStr`` so that a 422, a stack frame, or a model ``repr`` never
renders the plaintext.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class VaultRequest(BaseModel):
    """Base for every inbound vault payload."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class VaultResponse(BaseModel):
    """Base for every outbound vault payload.

    ``extra="forbid"`` on a response is the structural half of the no-plaintext guarantee: a
    field added by accident fails a test instead of shipping.
    """

    model_config = ConfigDict(extra="forbid")


__all__ = ["VaultRequest", "VaultResponse"]
