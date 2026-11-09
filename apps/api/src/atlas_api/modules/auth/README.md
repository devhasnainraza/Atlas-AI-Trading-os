# `auth` module

Atlas's trust layer: identity, authentication, sessions, MFA, RBAC, security center, and
privacy. Spec: [`specs/002-auth-security`](../../../../../../specs/002-auth-security/spec.md).

## Import surface

Other modules import `auth.public` only. It exposes:

| Symbol | Purpose |
|---|---|
| `build_auth_module()` | `ModuleDef` for `create_app` |
| `Principal` | The authenticated caller (user id, roles, permissions, session id, MFA freshness) |
| `require_permissions(...)` | Route dependency enforcing deny-by-default authorization |
| `current_principal` | Route dependency returning the `Principal` |

Nothing else is importable across the boundary — enforced by `lint-imports`.

## Layers

```text
router.py            HTTP surface; thin. Declares required permissions per route.
service/             Use cases. The only layer that touches repositories or publishes events.
  tokens.py            ES256 mint/verify + JWKS
  hashing.py           Argon2id password + recovery-code hashing
  one_time_tokens.py   Hashed single-use email-verify / reset / magic-link tokens
  registration.py      Register → verify → consents
  sessions.py          Login, refresh rotation, family revocation, logout
  oauth.py             Google / GitHub / Apple via Authlib
  magic_link.py        Passwordless sign-in
  password_policy.py   zxcvbn + breach screening + reuse history
  passwords.py         Forgot / reset / change
  mfa.py               TOTP enrol/activate/disable, recovery codes, step-up
  lockout.py           Per-account backoff and IP throttles
  authorization.py     Role → permission resolution
  admin.py             Admin user search, role grants, lock/unlock
  security_center.py   Score, overview, recommendations, event acknowledgement
  api_keys.py          User-issued platform keys
  privacy.py           Export bundles and erasure orchestration
domain/              Entities, state machines, ports. No framework imports, no I/O.
repository/          Port implementations: in-memory (tests, local) and SQLAlchemy.
migrations/versions/ Alembic revisions on the `auth` branch label.
```

## Invariants

1. **No plaintext secret ever leaves this module.** Password hashes, token hashes, TOTP
   secrets, and recovery codes are write-only; no read path returns them, for any role.
2. **Uniform failure.** "Wrong password" and "no such user" are indistinguishable in
   response body, status, and timing (`ATLAS-AUTH-001`).
3. **Deny by default.** A route with no declared permission is unreachable by any
   authenticated caller, not open to all of them.
4. **Refresh reuse is a theft signal.** Presenting a rotated refresh token revokes the whole
   family and raises a `token_reuse` security event.
5. **Time is injected.** Domain code takes a `Clock`; `datetime.now()` in this module is a bug
   (TOTP windows and lockout arithmetic must be deterministic under test).
