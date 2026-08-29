# Event Contract: atlas.auth.* / atlas.credentials.* / atlas.privacy.*

**Feature**: 01-auth-security | **Date**: 2026-08-04
Extends the Spec 00 event catalog (envelope v1, naming/versioning/idempotency rules apply
unchanged). Topics: `atlas.auth`, `atlas.credentials`, `atlas.privacy` (+ standard retry/
DLQ/replay companions). **Payload rule**: user_id + non-secret metadata only — never
emails-in-clear where avoidable (use user_id; email only in events whose consumers need it
for delivery), never tokens, hashes, or secret material.

## Catalog (v1.0.0)

| event_type | Producer | Payload (summary) | Primary consumers |
|---|---|---|---|
| atlas.auth.user.registered | api/auth | {user_id, method, requires_verification} | worker (verification email), analytics |
| atlas.auth.user.email_verified | api/auth | {user_id} | worker (welcome email), onboarding |
| atlas.auth.user.login_succeeded | api/auth | {user_id, method, device_id, geo, new_device} | security analyzer (travel/device rules) |
| atlas.auth.user.login_failed | api/auth | {email_hash, ip, reason_class} | abuse detector (stuffing patterns) |
| atlas.auth.user.locked_out | api/auth | {user_id, until, trigger} | worker (notify user), alerting |
| atlas.auth.session.revoked | api/auth | {user_id, session_id, scope: one\|family\|all, cause} | realtime (force client logout) |
| atlas.auth.password.changed | api/auth | {user_id, via: change\|reset} | worker (notify), security analyzer |
| atlas.auth.password.reset_requested | api/auth | {user_id} | worker (reset email) |
| atlas.auth.mfa.enrolled | api/auth | {user_id, factor: totp} | worker (notify), security score |
| atlas.auth.mfa.disabled | api/auth | {user_id} | worker (notify — high-signal), analyzer |
| atlas.auth.mfa.recovery_code_used | api/auth | {user_id, remaining} | worker (notify), security event |
| atlas.auth.account.linked | api/auth | {user_id, provider} | connected-accounts sync |
| atlas.auth.account.unlinked | api/auth | {user_id, provider} | connected-accounts sync |
| atlas.auth.role.assigned / .revoked | api/auth | {user_id, role, scope?, actor} | audit consumers, cache invalidation |
| atlas.auth.security_event.raised | worker/api | {user_id?, type, severity, event_id} | alerting, Security Center realtime |
| atlas.auth.connected_account.status_changed | worker | {user_id, account_id, old, new} | future notifications, dashboards |
| atlas.credentials.credential.stored | api/credentials | {user_id, credential_id, kind, provider} | audit, connected-accounts |
| atlas.credentials.credential.rotated | api/credentials | {user_id, credential_id, version} | future broker/AI modules (refresh handles) |
| atlas.credentials.credential.revoked | api/credentials | {user_id, credential_id, cause} | future broker/AI modules (stop use NOW) |
| atlas.credentials.credential.retrieved | credentials/public | {user_id, credential_id, purpose, caller} | audit anomaly detection |
| atlas.privacy.export.completed | worker | {user_id, request_id} | worker (notify with link) |
| atlas.privacy.user_erasure.requested | api/privacy | {user_id, request_id, hard_delete_at} | **EVERY PII-holding module — mandatory subscription, contract-tested** |
| atlas.privacy.user_erasure.completed | worker | {user_id_tombstone, request_id} | audit, compliance reporting |

## Consumer obligations

- `atlas.privacy.user_erasure.requested`: any module storing user-linked data (now or in
  future specs — AI memory, journals, portfolios, notifications) MUST subscribe, erase or
  pseudonymize its records, and emit its own `…erasure_ack` within the deletion SLA. A CI
  contract test walks the module registry and fails if a module declares user-linked tables
  without an erasure subscription.
- `atlas.credentials.credential.revoked`: consumers holding credential handles MUST drop
  them immediately; handles are single-request anyway (no caching allowed).
- `login_failed` uses `email_hash` (HMAC with server key), not plaintext email — abuse
  detection works on stable pseudonyms.

## Versioning

Same rules as Spec 00 catalog: additive = minor bump; breaking = new `.v2` type with
migration window. This file is the source of truth until the registry service supersedes it.
