"""Credential vault event publication and handlers.

Vault events describe *that* something happened to a credential, never *what* the credential
is: ``credential_id``, ``provider``, ``purpose``, ``version`` — no value, no ciphertext, no
wrapped DEK, not even a hash. ``credential.retrieved`` is the sensitive one: it fires on every
authorized use, so it must stay cheap and it must stay clean.

Consumers of ``atlas.credentials.credential.revoked`` MUST drop any handle immediately.
Handles are single-request by contract; nothing may cache one across requests, which is what
makes revocation take effect on the next operation rather than on the next cache expiry.

Publication and handlers land with US3 (T048–T050).
"""

from __future__ import annotations

from atlas_observability import get_logger

logger = get_logger("atlas_api.modules.credentials")

__all__ = ["logger"]
