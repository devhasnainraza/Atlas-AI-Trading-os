# Phase 0 Research: Authentication & Security Decisions

**Feature**: 01-auth-security (branch `002-auth-security`) | **Date**: 2026-08-04
All Technical Context unknowns resolved below. Format: Decision / Rationale / Alternatives.

## 1. Build vs buy — custom FastAPI IAM

- **Decision**: Build the IAM as in-house `auth` + `credentials` modules on vetted libraries.
- **Rationale**: (a) The credential vault for broker/exchange/AI keys is unavoidably custom
  and must sit under the same threat model, audit trail, and zero-trust boundary as
  authentication; (b) "world's most secure trading OS" positioning makes a third-party data
  path for identity a product liability; (c) per-MAU SaaS pricing at the 100k-user target is
  material; (d) backend is Python — Better Auth (TS) would split the security estate across
  runtimes.
- **Alternatives**: Auth0/Clerk (fast, but external data path + cost + still need vault/RBAC/
  audit in-house), Keycloak (self-hosted control but heavy Java ops for a small team; theming
  and API ergonomics costly), Better Auth (excellent, but Node-only — wrong runtime),
  fastapi-users library (thin; we exceed it immediately on sessions/MFA/vault).
- **Tradeoffs**: We own the security bugs — mitigated by vetted primitives (Authlib,
  argon2-cffi, pyotp, cryptography), an abuse-focused test suite, and an external pentest
  gate before production.

## 2. Token model — ES256 JWT access + opaque rotating refresh

- **Decision**: 15-min ES256 JWTs (JWKS published, kid rotation 90d) + opaque 256-bit
  refresh tokens hashed (SHA-256) in the session table, rotate-on-use with reuse-detection
  family revocation.
- **Rationale**: Local JWT verification keeps p95 <2s at scale (no DB hit on hot paths);
  opaque refresh in DB gives real revocation + session listing (FR-008/009); rotation +
  family kill is current OWASP-recommended refresh handling; ES256 over RS256 for smaller
  tokens/keys, over HS256 for asymmetric verification (future services verify without the
  signing secret).
- **Alternatives**: Pure server sessions (simplest revocation but DB/Redis hit every
  request + poor future service-to-service story), long-lived JWTs with denylist (revocation
  list grows unbounded), PASETO (nicer design, thinner ecosystem/tooling).
- **Tradeoffs**: ≤15-min revocation lag on non-sensitive routes — accepted and documented;
  sensitive routes (vault/admin/privacy) always check the Redis `sid` denylist.

## 3. Browser transport — `__Host-` HttpOnly cookies + CSRF double-submit

- **Decision**: Access + refresh JWT/cookie pair as `__Host-`-prefixed HttpOnly Secure
  SameSite=Lax cookies; CSRF token via double-submit on state-changing cookie-authenticated
  routes; mobile/API clients use Authorization bearer.
- **Rationale**: HttpOnly removes token theft via XSS (biggest web risk); `__Host-` prefix
  pins path/secure/no-domain; SameSite=Lax + double-submit covers CSRF including the Lax
  top-level-GET gap.
- **Alternatives**: localStorage tokens (XSS-stealable — rejected), SameSite=Strict (breaks
  OAuth redirect UX), stateless CSRF (signed) — chosen double-submit is simpler and adequate.

## 4. Password hashing — Argon2id via argon2-cffi

- **Decision**: Argon2id, 64 MiB / t=3 / p=4, parameters versioned per hash; transparent
  rehash-on-login when params change.
- **Rationale**: OWASP first choice; memory-hardness counters GPU cracking; ~100ms fits the
  sign-in latency budget.
- **Alternatives**: bcrypt (no memory hardness, 72-byte truncation), scrypt (fine, weaker
  library ergonomics), PBKDF2 (only for FIPS constraints we don't have).

## 5. Breach detection — HIBP k-anonymity + zxcvbn

- **Decision**: zxcvbn score ≥3 locally + HIBP range API (5-char prefix k-anonymity) on
  set/change; HIBP outage degrades to zxcvbn-only (logged, flag-controlled).
- **Rationale**: NIST 800-63B requires breached-password screening; k-anonymity keeps the
  password (and even its full hash) off the wire.
- **Alternatives**: Offline breach corpus (large, stale), no check (non-compliant with our
  own bar).

## 6. OAuth/OIDC clients — Authlib

- **Decision**: Authlib for Google (OIDC), GitHub (OAuth2), Apple (OIDC with client-secret
  JWT); always code flow + PKCE + `state` + `nonce`; provider config via settings.
- **Rationale**: Mature Python implementation of the full spec family; Apple's signed-JWT
  client secret is supported; one library for all providers.
- **Alternatives**: python-social-auth (framework-coupled), hand-rolled flows (crypto
  footguns — rejected on principle).

## 7. MFA — TOTP (pyotp) + Argon2id-hashed recovery codes

- **Decision**: RFC 6238 TOTP with ±1 step window, encrypted secret at rest (vault crypto);
  10 single-use hashed recovery codes; step-up freshness claim (`mfa` ≤5 min) for sensitive
  ops; SMS explicitly excluded.
- **Rationale**: TOTP is phishing-resistant-enough, offline, and free; SMS is SIM-swap-prone
  and adds a vendor; recovery codes cover device loss; step-up satisfies vault/admin
  protection without constant friction.
- **Alternatives**: SMS OTP (rejected — SIM swap), email OTP (kept only inside the account-
  recovery cooling flow), WebAuthn/passkeys (deferred by spec; schema reserved).

## 8. Vault crypto — envelope encryption, AES-256-GCM + cloud KMS KEK

- **Decision**: Per-credential 256-bit DEK encrypts secret with AES-256-GCM (AAD =
  user_id/credential_id/version); DEK wrapped by KMS KEK (cloud KMS in deployed envs; env-var
  KEK for local dev only); KEK rotation = background rewrap of wrapped DEKs; deletion =
  crypto-shredding (drop wrapped DEK).
- **Rationale**: Industry-standard envelope pattern; per-credential DEKs bound blast radius;
  AAD prevents ciphertext transplant; KMS keeps the root key in HSM, out of app memory and
  backups; crypto-shredding makes privacy deletion real even in old backups.
- **Alternatives**: pgcrypto (key lives too close to data), HashiCorp Vault transit (strong,
  but new stateful service to operate now — revisit when dynamic DB creds/PKI needed; our
  interface allows swapping the wrap provider), client-side encryption (breaks server-side
  trading use).

## 9. RBAC — flat roles → permission strings, scope-ready assignments

- **Decision**: `domain:resource:action` permission strings; system roles seeded
  (guest/user/premium/support/admin + reserved org roles); `user_role` carries nullable
  scope columns; `roles_ver` on user for instant permission refresh against 15-min JWTs.
- **Rationale**: Flat sets are auditable and predictable (no diamond-inheritance surprises);
  scope columns satisfy FR-024 without building orgs now; version bump gives "changes apply
  immediately" (US4) without killing sessions.
- **Alternatives**: Hierarchical RBAC (resolution ambiguity), ABAC/OPA (overkill now; can
  layer later for org policies), Casbin (extra DSL surface for what 3 tables express).

## 10. Rate limiting & lockout — Redis sliding window + exponential account backoff

- **Decision**: Reuse Spec 00 Redis sliding-window middleware with per-route-class configs;
  add per-account exponential backoff (5 free → 1m/5m/15m/1h) and IP-scoped pre-lockout
  throttles; CAPTCHA integration point behind a feature flag (provider chosen later).
- **Rationale**: Layered controls stop both brute force and lockout-DoS; Redis failure
  degrades to conservative deny-leaning limits (fail-safe, Constitution IX).
- **Alternatives**: WAF-only (no account context), fail2ban-style IP bans only (VPN/CGNAT
  false positives).

## 11. Device & anomaly signals — soft fingerprint + GeoIP velocity

- **Decision**: Device identity from a signed long-lived cookie + UA/platform metadata;
  GeoIP (MaxMind GeoLite2, weekly refresh job) for login geo; impossible-travel rule at
  >900 km/h between consecutive logins; new-device and token-reuse events feed
  `security_event` + notifications.
- **Rationale**: Meets FR-021 with privacy-respecting signals (no canvas fingerprinting —
  Principle VIII); rules are explainable (Principle V).
- **Alternatives**: Commercial device-intel SDKs (cost + privacy posture), ML risk scoring
  (future — needs data we don't have yet).

## 12. Email delivery — via Spec 00 notification interface

- **Decision**: Auth emails (verify, reset, magic link, security alerts) go through the
  Spec 00 `Notifier` interface; first concrete provider adapter (e.g. Resend/Postmark/SES)
  is chosen at implementation via config — the interface keeps it swappable; sends are
  queued through the worker with retries.
- **Rationale**: Spec 00 deliberately left channels to future specs; auth only needs the
  seam + one adapter; queuing tolerates provider outage (fail-safe onboarding).
- **Alternatives**: Direct SMTP in-process (blocks request path, poor retries).

## 13. Verification/reset/magic tokens — hashed single-use rows

- **Decision**: One `verification_token` table for email-verify (24h), password-reset
  (30m), magic-link (15m): random 256-bit value sent to user, only SHA-256 stored,
  single-use, purpose-bound, invalidated on use and on newer issuance.
- **Rationale**: DB leak exposes no usable tokens; uniform machinery, three policies.
- **Alternatives**: Signed stateless tokens (can't single-use without a store anyway).

## 14. Session store — Postgres rows + Redis denylist cache

- **Decision**: Sessions are PG rows (listing, audit, analytics) with Redis holding only the
  revocation denylist (`sid`, TTL = remaining JWT life) and hot counters.
- **Rationale**: PG gives durable session management UX (SC-003); Redis makes sensitive-
  route revocation checks O(1); Redis loss degrades safely (deny-leaning, PG fallback).
- **Alternatives**: Redis-only sessions (loses durable history + complicates SC-008 audit),
  JWT-only (no revocation).

## 15. Privacy export/delete — async jobs + erasure event contract

- **Decision**: Export and deletion run as Spec 00 background tasks; deletion publishes
  `atlas.privacy.user_erasure.requested` that ALL current and future PII-holding modules
  must consume (contract-tested); 14-day cancelable grace before hard delete;
  crypto-shredding for vault items; audit rows pseudonymized, not deleted.
- **Rationale**: Bounded-time completion (SC-007) without blocking requests; the event
  contract future-proofs erasure against modules that don't exist yet.
- **Alternatives**: Synchronous cascade delete (timeouts, partial failures), full audit
  erasure (breaks the append-only integrity requirement + legal retention assumption).
