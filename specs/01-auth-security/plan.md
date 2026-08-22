# Implementation Plan: Authentication, Security & User Management Platform

**Branch**: `002-auth-security` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/01-auth-security/spec.md`

## Summary

Deliver Atlas's trust layer as a first-class `auth` module (plus `credentials` vault module)
on the Spec 00 foundation: email/password + Google/GitHub/Apple/magic-link authentication,
short-lived ES256 JWT access tokens with rotating opaque refresh sessions, TOTP MFA with
recovery codes, deny-by-default RBAC (org-ready), an envelope-encrypted credential vault for
broker/exchange/AI-provider secrets with zero plaintext exposure after save, a security
center, immutable audit trail, privacy export/deletion, and abuse monitoring — all built as
a custom FastAPI IAM on vetted libraries (Authlib, argon2-cffi, pyotp), not an external
identity SaaS.

## Technical Context

**Language/Version**: Python 3.12 (auth + credentials modules in `apps/api`), TypeScript 5.x (web auth UI in `apps/web`)
**Primary Dependencies**: FastAPI + Pydantic v2, Authlib (OAuth/OIDC clients), argon2-cffi (Argon2id), PyJWT[crypto] (ES256), pyotp (TOTP), SQLAlchemy 2 async + Alembic, Redis 7 (rate limits, revocation cache), cryptography (AES-256-GCM envelope encryption), user-agents/GeoIP lib (device + travel signals)
**Storage**: PostgreSQL 16 (identities, sessions, vault ciphertexts, RBAC, audit/security events), Redis (login throttles, token revocation cache, device challenges), Kafka (`atlas.auth.*` events), S3 (privacy export bundles)
**Testing**: pytest + testcontainers (full auth flows against real PG/Redis), Schemathesis vs contracts/auth-api.openapi.yaml, Playwright E2E (register→verify→login→MFA→revoke), abuse-case suite (lockout, replay, CSRF), pip-audit/Bandit/gitleaks
**Target Platform**: Same as Spec 00 — containers on Compose (local) and Kubernetes (cloud)
**Project Type**: web — extends `apps/api` (modules) + `apps/web` (features) + `services/worker` (async auth jobs)
**Performance Goals**: p95 sign-in < 2s (SC-002); token verification O(1) local (JWKS cached); 100k+ users, millions of session rows (SC-008)
**Constraints**: Zero plaintext credential exposure after save (SC-005/FR-011/012); every sensitive action audited (SC-004); rate limits on all auth endpoints (FR-020); no breaking future org/team/passkey model (FR-024/SC-010)
**Scale/Scope**: 2 new backend modules (`auth`, `credentials`), ~35 API operations, ~20 entities, ~17 domain events, 5 user stories

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance in this plan | Status |
|---|-----------|------------------------|--------|
| I | Human First | All destructive actions (revoke, delete account) are explicit user choices with confirmation + undo-safe design; support/admin cannot silently impersonate (audited, consent-gated). | ✅ |
| II | Security First | The entire spec: Argon2id, envelope-encrypted vault, TLS-only, HttpOnly cookies, broker credentials never reach the client (write-only masked API). | ✅ |
| III | Transparency | Security center exposes score, sessions, devices, alerts with reasons; every denial has a stable error code. | ✅ |
| IV | Multi-Agent Collab | Future agents obtain credentials only via server-side vault interface with tool-permission checks — never raw secrets. | ✅ |
| V | Explainability | Every auth decision (denial, lockout, alert) is reconstructable from audit + security events with correlation IDs. | ✅ |
| VI | Risk Before Profit | Fail-closed authorization (deny-by-default); lockout prefers blocking over convenience. | ✅ |
| VII | Continuous Learning | Login/security telemetry feeds future risk models, scoped per Principle VIII. | ✅ |
| VIII | Privacy by Design | Data minimization (no unnecessary PII), export + deletion flows, consent records, per-user vault isolation. | ✅ |
| IX | Reliability | Auth degrades safely: if Redis down → conservative rate limits + full DB checks; if email down → queued retries; never fail-open. | ✅ |
| X | Modular Architecture | `auth` and `credentials` are standard Spec 00 modules with `public.py` interfaces + events; no other module touches their tables. | ✅ |
| XI | Observability | Dedicated auth metrics/dashboards/alerts; audit log append-only (Spec 00 FR-047 extended). | ✅ |
| XII | Scalability | Stateless verification (JWT + cached JWKS), Redis-backed hot paths, session table partition-ready. | ✅ |

**Gate result (pre-Phase-0)**: PASS. **Post-Phase-1 re-check**: PASS — one complexity entry
(custom IAM vs hosted provider) justified in Complexity Tracking.

## 1. High-Level Architecture

```text
Browser/Mobile ──HTTPS──► Ingress ──► apps/api middleware chain
                                        │  (rate-limit → CSRF(cookie flows) → authN → authZ)
   cookies: __Host-access (JWT 15m)     ▼
            __Host-refresh (opaque)   auth module ──────────► credentials module (vault)
            __Host-csrf               │ router/service/domain │ write-only API, masked reads
                                      │                       │ envelope crypto (KMS KEK)
                                      ▼                       ▼
                    PostgreSQL (users, sessions, RBAC,   Redis (throttles, revocation
                    vault ciphertext, audit, events)     cache, challenges)
                                      │
                                      ▼
                    Kafka atlas.auth.* / atlas.credentials.* events
                    → worker (emails, geo-enrichment, alerting, export jobs)
```

- **Identity flow**: person → `user` aggregate → 1..n auth methods (password, OAuth links,
  magic link) → single canonical `user_id` used everywhere else in Atlas.
- **Authentication flow**: credential proof → risk checks (lockout, throttle) → optional MFA
  step-up → session created (refresh token) → access JWT minted with `sid`, `roles_ver`.
- **Authorization flow**: route declares `required_permissions` (Spec 00 seam) → middleware
  resolves JWT claims → permission set from cached role bindings → deny-by-default.
- **Session flow**: refresh token (opaque, hashed at rest) rotates on every use; reuse of a
  rotated token ⇒ family revocation (theft signal). Access JWTs die in ≤15 min; instant
  revocation via Redis `sid` denylist checked on sensitive routes.
- **API key flow** (user-issued platform keys): generated once, shown once, stored hashed;
  scoped permissions ⊆ owner's; usable only on `/v1` API paths, never web session paths.
- **Broker credential flow**: client POSTs secret over TLS → vault encrypts in-process
  (AES-256-GCM data key, KMS-wrapped) → ciphertext to PG → response returns masked ref only.
  Future trading services request decryption server-side through `credentials/public.py`
  with permission + audit; plaintext never serializes to any client-facing surface or log.
- **Security/trust boundaries**: (1) public internet ↔ ingress (TLS, WAF headers);
  (2) API layer ↔ modules (authN/authZ enforced before module code); (3) modules ↔ vault
  (only `credentials` holds crypto; callers get typed handles, not keys); (4) platform ↔ KMS
  (KEK never leaves KMS); (5) humans ↔ secrets (support/admin see masked metadata only).

## 2. Authentication Strategy

| Method | Why it exists | Notes |
|---|---|---|
| Email + password | Universal baseline, no third-party dependency | Argon2id; strength + breach checks (§8) |
| Google OAuth | Lowest-friction consumer sign-in | OIDC code flow + PKCE via Authlib |
| GitHub OAuth | Developer/algo-trader audience | OAuth2 code flow + PKCE |
| Apple Login | iOS requirement for future mobile app; privacy-relay emails supported | OIDC; handle private relay addresses as first-class emails |
| Magic link | Passwordless recovery-friendly option; reduces weak passwords | 15-min single-use token, hashed at rest |
| Passkeys | FUTURE — schema reserves `webauthn_credential` entity; not shipped | FR-024 compatibility only |

- **Lifecycle**: anonymous → registered (pending verification) → active → (suspended |
  locked | deleted). All transitions emit events + audit entries.
- **Onboarding**: §3. **Email verification**: single-use hashed token, 24h expiry, resend
  with cooldown (FR-006); unverified accounts can log in only to a verification-gated shell.
- **Account linking**: OAuth identity with verified email matching an existing account
  requires an authenticated confirmation (or fresh login) before linking — never silent
  auto-merge (pre-empts pre-registration account-takeover). Users manage links in Connected
  Accounts; cannot unlink the last remaining sign-in method.

## 3. User Registration Flow

1. Submit email (+ password, or choose OAuth/magic link) → account `pending_verification`.
2. Verify email (token link) → `active`; OAuth with provider-verified email skips step 2.
3. Required acceptances recorded as versioned **consent records**: Terms, Privacy Policy,
   Trading Risk Disclaimer — each stores document version + timestamp + IP; re-prompt on
   version bump (FR-001).
4. Profile creation (name, username, timezone, language) — deferred-allowed; minimal
   required set is email only (data minimization, Principle VIII).
5. Initial preferences wizard (optional, skippable): trading experience, preferred markets,
   risk preference (`conservative | balanced | aggressive`), notification defaults.
6. Welcome flow: security checklist nudge (enable MFA, add recovery codes) surfaced in
   Security Center; welcome email via notification interface.
7. **Extensibility**: onboarding steps are a declared ordered list (server-driven state
   machine `onboarding_state` on user) so future steps (org invite, KYC) insert without
   schema change.

## 4. Identity Management

- **User Identity**: one `user` row = one human; immutable `user_id` (UUIDv7) is the sole
  foreign identity key platform-wide.
- **Identity providers**: `oauth_account` rows (provider, provider_subject, email at link
  time) — n per user. Password/magic-link are method flags on the user, not providers.
- **Primary identity**: the account's canonical email (unique, case-folded). **Secondary
  identities**: linked OAuth subjects + additional verified emails (schema-ready, UI later).
- **Identity verification**: email now; document/KYC verification is a future module —
  `identity_verification_level` enum on user (`none|email|kyc_pending|kyc_verified`)
  reserves the path.
- **Enterprise/SSO future**: `user` never embeds org data; future `organization`,
  `org_membership` tables reference `user_id` (FR-024). SSO lands as another provider type
  (`saml|oidc-enterprise`) on `oauth_account` + per-org enforced-auth-policy — no redesign.

## 5. Authorization (RBAC)

- **Model**: `permission` (string `domain:resource:action`, e.g. `credentials:broker:write`,
  `admin:users:read`) ← `role_permission` → `role` ← `user_role` (with optional
  `scope_type/scope_id` for future org/team scoping) → user.
- **Built-in roles**: `guest` (unauthenticated: public endpoints only), `user` (free tier),
  `premium` (adds premium feature permissions), `support` (read-only user metadata, no
  secrets, no impersonation), `admin` (platform administration; secrets still masked),
  `org_owner`, `org_admin`, `team_member` (defined now, activated by future org spec).
  Custom roles: schema supports non-system roles; UI deferred.
- **Inheritance**: roles are flat permission sets — "inheritance" is expressed by seeding
  (premium ⊇ user) at definition time, not runtime hierarchy → no ambiguous resolution.
- **Boundaries**: deny-by-default; server-side only (client hints are cosmetic); permission
  changes bump `roles_ver` on the user → outstanding JWTs with older `roles_ver` are
  re-resolved against DB on next request (immediate effect, FR-015/US4); support/admin
  actions always audited; nobody — including admin — has a permission that returns
  credential plaintext.

## 6. Session Management

| Control | Decision |
|---|---|
| Access token | ES256 JWT, 15 min TTL, claims: `sub`, `sid`, `roles_ver`, `mfa`, `iat/exp/iss/aud`; JWKS at `/.well-known/jwks.json`; keys rotated 90d (kid-based, 2 active) |
| Refresh token | Opaque 256-bit random, SHA-256 hash at rest, bound to session row; browser: `__Host-` HttpOnly Secure SameSite=Lax cookie; mobile: secure storage |
| Rotation | Rotate on every refresh; parent marked `rotated`; presenting a rotated token revokes the whole session family + raises `security_event(token_reuse)` |
| Expiration | Idle timeout 14 days (refresh unused); absolute timeout 90 days (re-auth required); both configurable per environment |
| Remember device | Signed `device_id` cookie (365d) → skips MFA on trusted devices only |
| Device fingerprinting | Soft signals only (UA, platform, IP-derived geo) stored on `device`; no invasive canvas/fp — privacy principle |
| Trusted devices | User marks device trusted post-MFA; revocable in Security Center; trust expires 30d without use |
| Logout / logout-all | Deletes session (and family) + Redis `sid` denylist entry; logout-all iterates user sessions (FR-003/009) |
| Revocation | Sensitive routes (vault, admin, privacy) always check `sid` against Redis denylist; normal routes rely on 15-min JWT expiry — documented tradeoff |
| Concurrent sessions | Unlimited by default, listed in Security Center; per-user cap (default 20) to bound abuse |

## 7. Multi-Factor Authentication

- **TOTP**: pyotp, RFC 6238, 30s window ±1 step; secret encrypted via vault crypto;
  enrollment = QR provisioning → confirm code → active. Disable requires password + current
  code (or recovery code).
- **Recovery codes**: 10 single-use codes, Argon2id-hashed, shown once; regeneration
  invalidates prior set; usage raises a security event + email notification.
- **Step-up**: sensitive operations (vault writes, credential reveal-window ops, role
  grants, account deletion, disabling MFA) require MFA re-verification ≤5 min old (`mfa`
  claim freshness).
- **Enforcement**: per-user opt-in now; `mfa_required` policy flag per role (admins:
  enforced) and — future — per organization (Enterprise MFA).
- **Recovery flow (lost device + lost codes)**: identity re-proof via email + 7-day cooling
  period + notification to all channels + security event; support can only *initiate* the
  same flow, never bypass it (insider-threat control; spec edge case "must not permanently
  lock out").

## 8. Password Security

- **Hashing**: Argon2id (memory 64 MiB, t=3, p=4 — tuned to ~100ms server budget), unique
  salt per hash, versioned params for future migration.
- **Policy**: min 12 chars, max 128, no composition rules (NIST 800-63B), zxcvbn score ≥3,
  reject top-breached passwords via HIBP k-anonymity range API (fail-open to zxcvbn-only if
  HIBP unreachable — availability over hard dependency, logged).
- **Reset**: single-use hashed token, 30-min expiry, invalidated on use/password change;
  reset revokes all sessions except (optionally) the current verified one; notification sent.
- **History**: last 5 password hashes retained (Argon2id) — reuse rejected (FR-005).
- **Expiration**: none (NIST) — except forced reset on breach/compromise events.
- **Brute force**: per-account exponential backoff (5 free attempts → 1m/5m/15m/1h),
  per-IP sliding-window rate limits (Redis), lockout event + email at threshold; CAPTCHA
  integration point (flag-gated) before hard lockout; credential-stuffing detection via
  distributed-IP failure patterns (§19).

## 9. Broker Credential Protection

- **Scope**: broker API keys, exchange API keys + secrets, trading passwords, broker OAuth
  tokens — all stored ONLY through the vault (§11); one `credential` row per secret set.
- **Encryption**: AES-256-GCM with per-credential data key; data key wrapped by KMS-held
  KEK (envelope); AAD = (user_id, credential_id, version) so ciphertext can't be replayed
  across rows; local dev KEK from env with loud non-prod warning.
- **Zero frontend exposure**: write-only semantics — POST accepts plaintext once over TLS;
  all reads return `masked_hint` (last 4) + metadata only; no API exists that returns
  plaintext to any client, any role (FR-011/012, SC-005).
- **Secure retrieval**: future trading/AI services call
  `credentials.public.use_credential(credential_id, purpose)` in-process → decrypts,
  passes to the outbound adapter, zeroizes; every retrieval writes an audit entry with
  purpose + correlation_id (Constitution II + V).
- **Rotation**: new version row written, old version kept `retiring` for grace window then
  destroyed; **revocation**: immediate `revoked` status → retrieval denied; both audited +
  emit events (FR-013).
- **Least privilege**: credential records carry `allowed_purposes` (e.g. `read_only`,
  `trade`) — retrieval purpose must match; UI nudges users to store read-only exchange keys
  where possible.
- **Lifecycle**: created → active → (retiring) → revoked/deleted; deletion cryptographically
  effective (drop wrapped data key = ciphertext unrecoverable) plus row purge per retention.

## 10. AI Provider Credentials

Same vault, `credential.kind = ai_provider`, `provider ∈ {openai, anthropic, gemini, groq,
openrouter, azure_openai, custom}`. User-owned: stored per user, used only for that user's
future agent runs via the Spec 00 ModelProvider interface (LiteLLM receives the key
server-side per request, never persists it). Validation ping on save (provider `models`
list call) sets health status. Platform-owned provider keys (if any) live in infrastructure
secrets (ESO), NOT in the user vault — clean separation.

## 11. API Key Vault (internal design)

- **Tables**: `credential` (metadata, status, kind, provider, allowed_purposes, masked_hint)
  + `credential_version` (ciphertext, wrapped_dek, kek_version, aad_context, status).
- **Versioning**: rotation appends versions; exactly one `active` version per credential.
- **Metadata**: label, environment tag, expiry date (optional, alerts before expiry),
  created/last_used/last_validated timestamps, health status.
- **Permissions**: owner-only CRUD (`credentials:own:*`); no admin read of values;
  service-side retrieval gated by purpose + caller module identity.
- **Audit**: every create/rotate/revoke/retrieve/validate → audit_log + `atlas.credentials.*`
  event (FR-017).
- **Revocation**: instant status flip checked on every retrieval (no caching of plaintext or
  authorization decisions beyond request scope).
- **KEK rotation**: re-wrap DEKs in background job (KMS rewrap), no ciphertext rewrite needed.

## 12. User Profile

`user_profile` (1:1 with user): display name, username (unique, changeable with cooldown),
avatar ref, country/location (optional), languages, timezone, trading_experience enum,
preferred_markets[] (forex, crypto, indices…), risk_preference enum, bio. Preferences split
into `user_preference` key-value (typed JSON schema per key) for notification, privacy, UI
prefs — extensible without migrations (future personalization). All PII fields included in
privacy export; profile edits audited (low-sensitivity class).

## 13. Connected Accounts

`connected_account` unifies external links: kind (`broker | exchange | social_login |
notification_channel | ai_provider`), reference to `credential` (if secret-backed) or
`oauth_account` (if identity), display name, status (`connected | degraded | expired |
revoked | error`), granted permissions/scopes snapshot, last_sync_at, last_error (sanitized),
health check policy. UI actions: view detail, reconnect (re-auth/re-key), disconnect
(revokes credential + link). Health checks run as scheduled jobs (Spec 00 scheduler) with
per-kind probes; status changes emit events → future notifications (FR-014, US3).

## 14. Security Center

Single aggregate endpoint + web page (US5/FR-018): security score (0–100 from: MFA on,
recovery codes fresh, password strength/age, no active alerts, trusted-device hygiene),
recent logins (time, geo, device, method), active sessions (revoke buttons), trusted
devices, user API keys, connected brokers/providers with health, MFA status, password
health, open risk alerts, prioritized recommendations (rule-driven list, server-computed).
All data comes from existing entities — no new stores; score formula versioned so it can
evolve without breaking the UI.

## 15. Audit Logging

Extends Spec 00 append-only `audit_log_entry` with auth taxonomy:
`auth.login.succeeded/failed`, `auth.logout`, `auth.password.changed/reset`,
`auth.mfa.enrolled/disabled/recovery_used`, `auth.session.revoked`, `auth.account.locked/
unlocked/deleted`, `credentials.created/rotated/revoked/retrieved`, `rbac.role.assigned/
revoked`, `admin.*` (every admin/support action), `privacy.export/delete`. Entries carry
actor, target, correlation_id, IP, device_id, result; no secret material ever (redaction
enforced in the audit writer). Retention ≥ 1 year, immutable (no UPDATE/DELETE grants);
tamper-evidence via daily hash-chain checkpoint stored in object storage (lightweight, no
blockchain theater).

## 16. Privacy & Compliance

- **Export**: async job assembles JSON bundle (profile, preferences, sessions metadata,
  connected accounts metadata, audit entries about the user, consent history — never secret
  values) → encrypted zip in S3 → time-limited presigned link → notification (SC-007).
- **Account deletion**: soft-delete grace 14 days (cancelable) → hard delete: credentials
  crypto-shredded, sessions purged, profile/PII erased, OAuth links deleted, AI memory
  purge event published (`atlas.privacy.user_erasure.requested` — future agent-memory spec
  must subscribe); audit entries retained but pseudonymized (user_id → tombstone) per
  legal-retention assumption in spec.
- **Consent management**: versioned consent records (terms, privacy, risk disclaimer,
  marketing opt-in); cookie preferences stored client-side + server record for logged-in
  users.
- **GDPR/CCPA future**: export/delete/consent are the mechanical 80%; remaining work
  (DPA, records of processing, regional storage) explicitly future — schema keeps
  `data_region` nullable on user for later.
- **Retention**: sessions 90d after expiry, security events 1y, audit ≥1y, exports 7d,
  verification tokens purged on expiry.

## 17. Security Architecture

Encryption at rest: DB volumes (cloud) + envelope encryption for secrets (§9) + Argon2id
for verifiers. In transit: TLS 1.2+ everywhere; HSTS. Secrets management: platform secrets
via ESO (Spec 00); user secrets via vault. Key management: KMS KEK (rotation 1y, rewrap
job), JWT signing keys 90d rotation via JWKS, cookie-signing keys 180d. Certificates:
cert-manager/Let's Encrypt (Spec 00). Headers: HSTS, CSP (web), X-Content-Type-Options,
Referrer-Policy, frame-ancestors 'none', Permissions-Policy minimal. CSRF: `__Host-` cookies
SameSite=Lax + double-submit token required on all cookie-authenticated state-changing
routes (bearer-token API calls exempt). CORS: strict per-environment allowlist, credentials
allowed only for the web origin. Input validation: strict Pydantic (unknown fields
rejected); output sanitization: masked hints only, uniform "invalid credentials" wording
(no user-enumeration), React default escaping + CSP as XSS backstop. Zero trust: every
request authenticated/authorized at middleware regardless of origin (Spec 00 seam now
enforced for real).

## 18. Threat Modeling

| Threat | Impact | Mitigation | Monitoring | Recovery |
|---|---|---|---|---|
| Credential theft (user passwords) | Account takeover | Argon2id, HIBP checks, MFA, no enumeration | Failed-login + stuffing patterns | Forced reset, session purge, notify |
| Token theft (XSS/exfil) | Session hijack | HttpOnly `__Host-` cookies, 15-min JWTs, CSP | `token_reuse` events | Family revocation, key rotation |
| Session hijacking (refresh reuse) | Persistent access | Rotation + reuse-detection → family kill | security_event(token_reuse) alert | Auto-revoke + user notify |
| Brute force / stuffing | Takeover at scale | Backoff, IP+account limits, CAPTCHA hook | Distributed-failure detector | Lockouts, IP blocks, comms |
| Replay | Duplicate ops | Single-use hashed tokens (verify/reset/magic), GCM AAD, idempotency keys | Token-reuse metrics | Invalidate token class |
| CSRF | Forged state changes | SameSite + double-submit, no GET mutations | CSRF-failure counter | Rotate csrf secret |
| XSS | Token/PII theft | CSP, React escaping, no secrets in JS-readable storage | CSP report endpoint | Purge sessions, patch |
| SSRF (OAuth/webhook fetches) | Internal exposure | Allowlisted provider URLs only, no user-supplied fetch URLs in this spec, egress policy | Egress anomaly logs | Block + rotate internal creds |
| SQL injection | Data breach | SQLAlchemy bound params only, no raw SQL gate in review, Schemathesis fuzz | WAF/error anomaly | Standard IR runbook |
| API abuse (scraping, key abuse) | Cost, enumeration | Per-key + per-user rate classes, scoped keys | Per-key usage metrics | Key revocation |
| Bot signups | Spam, fraud | Email verification, rate limits, CAPTCHA hook, disposable-email flag list | Signup velocity | Purge + tighten flags |
| Insider threat | Secret exposure | No plaintext path exists for any role; least-privilege roles; all admin actions audited; hash-chained audit | Audit review alerts on admin bursts | Revoke role, rotate KEK, IR |

## 19. Monitoring

Metrics + alerts (extends Spec 00 stack): failed-login rate per account/IP (alert on
distributed spikes = stuffing), lockout count, impossible travel (geo-velocity between
consecutive logins > 900 km/h → security_event + user notify), new-device logins,
MFA-bypass attempts, token-reuse events (page severity), vault retrieval volume per user
and per purpose (broker credential access anomalies), rate-limit saturation, HIBP/OAuth
provider availability. Dashboards: Auth overview (logins, failures, latency), Abuse
(throttles, lockouts, stuffing score), Vault (operations, retrievals by purpose, KEK age).
Every alert → runbook in `docs/runbooks/auth/`.

## 20. Error Handling

Spec 00 taxonomy extended with auth codes (`ATLAS-AUTH-001` invalid credentials,
`-002` account locked, `-003` MFA required, `-004` MFA invalid, `-005` token expired,
`-006` token invalid, `-007` consent required, `-008` verification required,
`ATLAS-CRED-00x` for vault). Rules: identical response/timing for "wrong password" vs
"no such user" (enumeration resistance); lockout responses don't reveal remaining attempts
beyond UX minimum; never expose stack traces, DB errors, token values, broker identifiers,
or infrastructure details (FR-023); vault errors return generic failure + correlation_id,
details live server-side only.

## 21. Database Planning (entities — detail in data-model.md)

`user`, `user_profile`, `user_preference`, `consent_record`, `oauth_account`,
`verification_token` (email/reset/magic, hashed, single-use), `session` (+ family fields),
`device`, `mfa_totp_factor`, `recovery_code`, `password_history`, `role`, `permission`,
`role_permission`, `user_role` (scope-ready), `api_key` (user platform keys, hashed),
`credential` + `credential_version` (vault), `connected_account`, `security_event`,
`privacy_request`, plus reserved `webauthn_credential`. Audit reuses Spec 00
`audit_log_entry`. All auth tables in `auth`/`credentials` module migration branches.

## 22. API Planning (contract in contracts/auth-api.openapi.yaml)

- **Auth**: register, verify-email (+resend), login, login/mfa (step), refresh, logout,
  logout-all, magic-link request/consume, oauth {provider} start/callback,
  password forgot/reset/change.
- **MFA**: totp enroll/activate/disable, recovery-codes regenerate, step-up verify.
- **Profile**: GET/PATCH me, preferences GET/PUT, consents GET/POST.
- **Sessions/Devices**: list sessions, revoke one/all, list devices, trust/untrust, revoke.
- **Credentials (vault)**: list (masked), create, rotate, revoke, delete, validate;
  connected-accounts list/detail/reconnect/disconnect.
- **Security**: overview (security center aggregate), events list, alerts ack.
- **API keys**: list/create(show-once)/revoke.
- **Privacy**: export request/status, account deletion request/cancel.
- **Admin**: users search/detail (masked), role assign/revoke, account lock/unlock,
  audit query. All under `/v1`, standard error envelope, rate-limit classes per group.

## 23. Testing Strategy

Unit: domain rules (lockout math, rotation state machine, score formula) with fakes.
Integration (testcontainers): full flows — register→verify→login→refresh-rotation→reuse-
detection→family-revocation; MFA enroll/verify/recovery; vault encrypt/rotate/revoke with
real PG; RBAC matrix table-driven (every role × representative endpoints). Contract:
Schemathesis vs auth OpenAPI; event schema compat for `atlas.auth.*`. Security: abuse suite
(brute force → lockout, CSRF negative, enumeration timing, replay of used tokens), Bandit/
gitleaks/pip-audit in CI, ZAP baseline nightly, external penetration test before production
launch (roadmap gate). E2E (Playwright): US1–US5 happy paths + revocation UX. Load (k6):
login storm 1k VU (SC-002 p95 <2s), token refresh throughput, vault ops. Recovery: DB
restore drill includes vault decrypt verification with rewrapped keys.

## 24. Deployment Strategy

Rides Spec 00 infrastructure unchanged: same environments (local/dev/staging/prod), images,
Helm, ESO secrets (adds: JWT signing keys, cookie keys, KMS KEK alias, OAuth client
secrets, HIBP toggle). New infra needs: KMS key (Terraform), GeoIP database refresh job,
email provider credentials (via notification interface config). Scaling: auth is stateless
(JWT verify local; Redis for hot counters) — HPA as Spec 00; session table indexes +
partition plan documented for millions of rows (SC-008). HA/DR: PG PITR covers vault
ciphertext; KMS keys are region-replicated per provider capability; losing Redis degrades
to conservative limits, never fail-open. Rollback: expand→migrate→contract migrations;
auth module flag-gated per method (e.g. disable Apple login independently). Backups tested
with quarterly restore drill including a credential decrypt canary.

## 25. Risks

| Risk | Type | Impact | Mitigation |
|------|------|--------|-----------|
| Custom IAM bug (vs battle-tested SaaS) | Security | Takeover, breach | Vetted libs only, abuse test suite, external pentest gate, threat-model reviews per PR touching auth, bug-bounty later |
| KEK/KMS misconfig or loss | Security/Op | Vault unrecoverable or exposed | Terraform-managed KMS, rewrap drills, decrypt canary in restore tests, alias indirection |
| OAuth provider changes/outage | Operational | Sign-in method down | Per-method flags, magic-link fallback, provider health alerts |
| Email deliverability | Operational | Blocked onboarding/recovery | Reputable provider, resend + cooldown UX, deliverability monitoring |
| Session-table growth (millions) | Perf/Scale | Slow queries | TTL purge jobs, partitioning plan, covering indexes, Redis hot path |
| Enumeration/timing leaks | Privacy | Account discovery | Uniform responses + constant-time compares, timing tests in CI |
| Lockout DoS (attacker locks victims) | Operational | User lockouts | IP-scoped throttles before account lockout, CAPTCHA hook, unlock via verified email |
| Privacy deletion misses future stores | Compliance | Residual PII | Erasure event contract — every future module MUST subscribe; deletion checklist in DoD |
| Scope creep into org/teams now | Delivery | Delay | Org tables deferred; only `scope_*` columns + role names reserved (FR-024) |
| Support workflows leak secrets | Security | Insider exposure | Masked-only admin surfaces, no impersonation, audited support role, quarterly access review |

## Complexity Tracking

| Choice | Why Needed | Simpler Alternative Rejected Because |
|--------|------------|--------------------------------------|
| Custom FastAPI IAM (vs Auth0/Clerk/Keycloak/Better Auth) | Broker/AI credential vault, trading-grade audit, and zero-third-party data path are core product trust promises; Better Auth is TS-only (backend is Python); IAM must live beside the vault under one threat model | Hosted IdP puts the most sensitive flow outside our zero-trust boundary, adds per-MAU cost at 100k users, and still leaves vault/RBAC/audit to build; Keycloak = heavy ops + Java estate for a small team |
| Envelope encryption with KMS (vs pgcrypto column encryption) | Per-credential DEKs, crypto-shredding deletion, KEK rotation without ciphertext rewrite, HSM-backed root | pgcrypto keys end up in DB/app config — one SQL injection or backup leak exposes everything; no clean rotation story |

---

**Phase 0 output**: [research.md](./research.md) · **Phase 1 outputs**:
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)
