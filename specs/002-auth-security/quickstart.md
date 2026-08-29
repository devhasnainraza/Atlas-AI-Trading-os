# Quickstart: Auth & Security Module (Local Development)

**Feature**: 01-auth-security | Builds on the Spec 00 local stack
(`specs/001-platform-foundation/quickstart.md`) — complete that first.

## Extra prerequisites

- OAuth sandbox apps (optional for local): Google/GitHub/Apple client IDs; without them,
  email/password + magic-link flows are fully testable.
- Mail viewing: local stack includes Mailpit (SMTP catcher) at http://localhost:8025 —
  all verification/reset/magic emails land there.
- Local crypto: `ATLAS_VAULT_KEK_LOCAL` (32-byte base64) in `.env` — dev only; deployed
  environments use KMS and refuse this variable.

## 1. Configure

```bash
cp infra/docker/.env.example .env      # includes AUTH_* and VAULT_* placeholder sections
./scripts/bootstrap                    # generates local JWT signing keypair + cookie keys
./scripts/db migrate                   # applies auth + credentials migration branches
uv run python -m atlas_api.modules.auth.seed   # seeds roles/permissions + dev admin
```

Startup fails fast if any required auth variable is missing — the error names the field.

## 2. Smoke the flows (scripts wrap curl; all against http://localhost:8000/v1)

| Flow | Command | Expect |
|---|---|---|
| Register + verify | `./scripts/auth-smoke register` | 202 → email in Mailpit → verify → active session |
| Login + refresh rotation | `./scripts/auth-smoke login` | cookies set; second refresh rotates; reusing old token revokes family (check `security_event`) |
| MFA | `./scripts/auth-smoke mfa` | enroll TOTP → activate → recovery codes printed once → step-up works |
| Lockout | `./scripts/auth-smoke lockout` | 5 bad passwords → backoff responses → lockout event + Mailpit notice |
| Vault | `./scripts/auth-smoke vault` | store fake exchange key → masked list → rotate → revoke → retrieval denied |
| Privacy | `./scripts/auth-smoke privacy` | export job → presigned link; deletion request → grace state → cancel |

## 3. Web UI

`apps/web` routes: `/register`, `/login`, `/verify`, `/settings/security` (Security
Center), `/settings/credentials`, `/settings/sessions`, `/settings/privacy`. Dev identity
banner shows when `ENV=local` and DevIdentityProvider is active for non-auth modules.

## 4. Tests

```bash
uv run pytest apps/api/src/atlas_api/modules/auth -m "not slow"   # unit + integration
uv run pytest tests/contract/auth                                  # Schemathesis + event compat
uv run pytest tests/security/auth_abuse                            # lockout/CSRF/enumeration/replay suite
pnpm exec playwright test tests/e2e/auth                           # US1–US5 journeys
```

## Troubleshooting

- **JWKS 404**: run `./scripts/bootstrap` — signing keys not generated.
- **Emails missing**: check Mailpit container; worker must be running (emails are queued).
- **`VAULT_KEK` error in staging/prod**: expected — those environments require KMS config,
  the local env var is rejected by design.
- **Clock-dependent TOTP failures in tests**: test suite uses the injected clock; never
  `datetime.now()` in auth domain code (Spec 00 standard).
