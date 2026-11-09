"""Auth event publication and handlers.

Two rules govern everything in this file, both from ``contracts/auth-events.md``:

* **Payloads carry ``user_id`` plus non-secret metadata only** — never a token, a token hash, a
  password hash, a TOTP secret, or a credential value. An event log is replayed, exported,
  fanned out to consumers that do not exist yet, and retained longer than any request log.
* **``login_failed`` carries ``email_hash``, not the address.** Abuse analysis needs to group
  attempts against one account; it does not need the account's identity, and an event stream
  full of plaintext addresses is a breach waiting for a misconfigured consumer.

Handlers are idempotent by construction — every one runs under ``atlas_events.ledger.idempotent``
so a redelivered event cannot double-apply.

Publication and handlers land with their stories: US1 events (T030) first, then US2–US5.
"""

from __future__ import annotations

from atlas_observability import get_logger

logger = get_logger("atlas_api.modules.auth")

__all__ = ["logger"]
