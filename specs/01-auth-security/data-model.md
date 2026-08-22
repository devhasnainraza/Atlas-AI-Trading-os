# Data Model: Authentication, Security & User Management

**Feature**: 01-auth-security | **Date**: 2026-08-04
Conventions per Spec 00: UUIDv7 `id` PKs, `created_at`/`updated_at` timestamptz, snake_case,
enums CHECK-constrained. No SQL here — entities, fields, rules, transitions. Tables live in
the `auth` and `credentials` module migration branches.

## user

| Field | Type | Rules |
|---|---|---|
| email | citext UNIQUE | canonical identity; case-folded |
| email_verified_at | timestamptz NULL | |
| password_hash | text NULL | Argon2id w/ versioned params; NULL = passwordless account |
| status | enum | `pending_verification → active → (suspended \| locked \| deleting \| deleted)` |
| onboarding_state | jsonb | server-driven step machine (§3 of plan) |
| roles_ver | int | bumped on any role/permission change |
| mfa_enabled | boolean | derived convenience flag |
| identity_verification_level | enum | `none \| email \| kyc_pending \| kyc_verified` |
| locked_until / failed_login_count | timestamptz / int | backoff state |
| data_region | text NULL | reserved for future residency |
| deleted_at | timestamptz NULL | soft-delete grace marker |

**Transitions**: `pending_verification→active` (email verified or provider-verified OAuth);
`active→locked` (abuse) and back via recovery; `active→deleting` (privacy request, 14d
grace, cancelable) → `deleted` (hard erasure). All transitions audited + evented.

## user_profile (1:1 user)

display_name, username (citext UNIQUE, 30d change cooldown), avatar_ref, country,
languages text[], timezone, trading_experience enum (`novice|intermediate|advanced|professional`),
preferred_markets text[] (`forex|crypto|indices|commodities|stocks`), risk_preference enum
(`conservative|balanced|aggressive`), bio. All fields optional (data minimization).

## user_preference

(user_id, key) UNIQUE; value jsonb validated against a registered per-key schema; categories:
notification, privacy, ui. Extensible without migration.

## consent_record (append-only)

user_id, document enum (`terms|privacy|risk_disclaimer|marketing`), document_version,
granted boolean, ip, user_agent, occurred_at. Latest row per (user, document) is current
state; history preserved.

## oauth_account

user_id FK, provider enum (`google|github|apple` + reserved `saml|oidc_enterprise`),
provider_subject text, email_at_link citext, scopes text[], linked_at.
UNIQUE (provider, provider_subject). Rule: cannot delete the last sign-in method of a user.

## verification_token

user_id, purpose enum (`email_verify|password_reset|magic_link`), token_hash (SHA-256)
UNIQUE, expires_at (24h/30m/15m by purpose), used_at NULL, invalidated_at NULL, context
jsonb (ip, ua). Single-use; newer issuance invalidates prior same-purpose tokens; purged on
expiry by scheduled job.

## session

| Field | Type | Rules |
|---|---|---|
| user_id | FK | |
| refresh_token_hash | text UNIQUE | SHA-256 of opaque token |
| family_id | uuid | rotation family; reuse ⇒ revoke family |
| parent_id | uuid NULL | previous token in family |
| status | enum | `active → rotated \| revoked \| expired` |
| device_id | FK device | |
| ip / geo / user_agent | inet / jsonb / text | at creation + last refresh |
| mfa_verified_at | timestamptz NULL | step-up freshness source |
| last_used_at | timestamptz | idle timeout basis (14d) |
| absolute_expires_at | timestamptz | 90d hard stop |

**Transitions**: `active→rotated` (refresh); `active/rotated→revoked` (logout, admin,
reuse-detection — family-wide); `active→expired` (janitor). Indexes: (user_id, status),
(family_id). Partition-by-month plan documented for SC-008 scale.

## device

user_id, device_key_hash (from signed cookie) UNIQUE per user, label (auto from UA),
platform, first_seen_at, last_seen_at, trusted boolean, trusted_until (30d sliding),
revoked_at NULL. Trust skips MFA only while unexpired.

## mfa_totp_factor

user_id (one active per user now; table allows multiple for future), secret_ciphertext +
wrapped_dek (vault crypto), status enum (`pending → active → disabled`), confirmed_at,
last_used_step bigint (blocks step replay).

## recovery_code

user_id, code_hash (Argon2id), batch_id uuid, used_at NULL. Regeneration invalidates the
prior batch (batch_id supersession). Exactly 10 per active batch.

## password_history

user_id, password_hash, created_at. Keep last 5; checked on change (FR-005).

## role / permission / role_permission / user_role

- **role**: name UNIQUE (`guest|user|premium|support|admin|org_owner|org_admin|team_member`),
  is_system boolean, mfa_required boolean, description.
- **permission**: key UNIQUE `domain:resource:action`, description. Seeded from route
  declarations; unknown keys fail CI.
- **role_permission**: (role_id, permission_id) UNIQUE.
- **user_role**: user_id, role_id, scope_type enum NULL (`org|team` reserved), scope_id uuid
  NULL, granted_by, granted_at. UNIQUE (user_id, role_id, scope_type, scope_id).
  Every grant/revoke audited + bumps user.roles_ver.

## api_key (user-issued platform keys)

user_id, name, key_prefix (first 8 chars, shown in UI), key_hash (SHA-256; full value shown
once at creation), scopes text[] ⊆ owner permissions, status enum (`active|revoked|expired`),
expires_at NULL, last_used_at, created_ip. Usable only with `Authorization: Bearer atlas_…`
on API paths; never grants web session.

## credential (vault metadata) + credential_version (ciphertext)

- **credential**: user_id, kind enum (`broker|exchange|ai_provider|webhook|notification`),
  provider text (e.g. `binance`, `oanda`, `anthropic`), label, masked_hint (last 4),
  allowed_purposes text[] (`read_only|trade|inference|notify`), status enum
  (`active → retiring → revoked → deleted`), health enum (`unknown|healthy|degraded|failed`),
  last_validated_at, last_used_at, expires_at NULL (alert before expiry).
- **credential_version**: credential_id, version int, ciphertext bytea (AES-256-GCM),
  wrapped_dek bytea, kek_version text, aad_context jsonb {user_id, credential_id, version},
  status enum (`active|retiring|destroyed`), created_at, destroyed_at NULL.
  Exactly one `active` version per credential (partial unique). Deletion = destroy wrapped
  DEKs (crypto-shred) then purge rows per retention.

**Rules**: plaintext exists only in request memory during create/rotate and in-process
during authorized `use_credential(purpose)`; every version state change audited.

## connected_account

user_id, kind enum (`broker|exchange|social_login|notification_channel|ai_provider`),
credential_id FK NULL, oauth_account_id FK NULL (exactly one set), display_name, status enum
(`connected|degraded|expired|revoked|error`), scopes_snapshot jsonb, last_sync_at,
last_error text (sanitized), health_policy jsonb (probe kind + cadence). Status changes emit
`atlas.auth.connected_account.status_changed`.

## security_event

user_id NULL (platform-level events allowed), type enum (`login_new_device|
impossible_travel|token_reuse|lockout|stuffing_suspected|mfa_recovery_used|
credential_anomaly|admin_burst`), severity enum (`info|warning|critical`), details jsonb
(redacted), correlation_id, status enum (`open → acknowledged → resolved`), acked_by NULL.
Feeds Security Center alerts (FR-018/021) and Alertmanager routing for `critical`.

## privacy_request

user_id, type enum (`export|deletion`), status enum
(`requested → processing → completed \| canceled \| failed`), requested_at, completed_at,
artifact_ref text NULL (S3 key for exports, 7d TTL), cancelable_until (deletion: +14d).
One active request per (user, type).

## webauthn_credential (RESERVED — no implementation this spec)

user_id, credential_id bytea, public_key, sign_count, transports[], label, created_at.
Exists so passkeys (FR-024) arrive without user-model change.

## Cross-cutting rules

- Every table above: user_id indexed; erasure handler defined (delete, crypto-shred, or
  pseudonymize) and registered against `atlas.privacy.user_erasure.requested` — CI contract
  test asserts coverage.
- No column ever stores plaintext secrets, full tokens, or reversible PII beyond declared
  fields; audit writer + logger enforce redaction.
- Retention: sessions 90d post-expiry; verification tokens on expiry; security events 1y;
  exports 7d; audit ≥1y (pseudonymized on erasure).

## Relationships (summary)

```text
user 1─1 user_profile · 1─n user_preference · 1─n consent_record
user 1─n oauth_account · 1─n session ─ n─1 device · 1─n api_key
user 1─1 mfa_totp_factor(active) · 1─n recovery_code · 1─n password_history
user n─n role (user_role, scope-ready) · role n─n permission
user 1─n credential 1─n credential_version
connected_account ─→ credential | oauth_account (xor)
security_event / privacy_request / audit_log_entry ─ user_id + correlation_id joins
```
