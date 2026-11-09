# Implementation Plan: Authentication, Security & User Management Platform

**Branch**: `01-auth-security` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/spec-01-auth-security/spec.md`

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

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Compliance in this plan | Status |
|---|-----------|------------------------|--------|
| I | Human First | All destructive actions are explicit user choices with confirmation + undo-safe design; support/admin cannot silently impersonate. | ✅ |
| II | Security First | Argon2id, envelope-encrypted vault, TLS-only, HttpOnly cookies, broker credentials never reach the client. | ✅ |
| III | Transparency | Security center exposes score, sessions, devices, alerts with reasons; every denial has a stable error code. | ✅ |
| IV | Multi-Agent Collab | Future agents obtain credentials only via server-side vault interface with tool-permission checks — never raw secrets. | ✅ |
| V | Explainability | Every auth decision is reconstructable from audit + security events with correlation IDs. | ✅ |
| VI | Risk Before Profit | Fail-closed authorization (deny-by-default); lockout prefers blocking over convenience. | ✅ |
| VII | Continuous Learning | Login/security telemetry feeds future risk models, scoped per Principle VIII. | ✅ |
| VIII | Privacy by Design | Data minimization, export + deletion flows, consent records, per-user vault isolation. | ✅ |
| IX | Reliability | Auth degrades safely: if Redis down → conservative rate limits + full DB checks; never fail-open. | ✅ |
| X | Modular Architecture | `auth` and `credentials` are standard Spec 00 modules with `public.py` interfaces + events. | ✅ |
| XI | Observability | Dedicated auth metrics/dashboards/alerts; audit log append-only. | ✅ |
| XII | Scalability | Stateless verification (JWT + cached JWKS), Redis-backed hot paths, session table partition-ready. | ✅ |

**Gate result**: PASS.

## 1. High-Level Architecture

```text
Browser/Mobile ──HTTPS──► Ingress ──► apps/api middleware chain
                                        │  (rate-limit → CSRF(cookie flows) → authN → authZ)
   cookies: __Host-access (JWT 15m)     ▼
            __Host-refresh (opaque)   auth module ──────────► credentials module (vault)
            __Host-csrf               │ router/service/domain │ write-only API, masked reads
                                      │                       │ envelope crypto (KMS KEK)
                                      ▼                       ▼
                                   PostgreSQL 16           PostgreSQL 16
                                 (identities, RBAC,       (ciphertexts, wrapped DEKs,
                                  sessions, audit)         connected accounts)
```

## 2. Directory Structure

```text
specs/spec-01-auth-security/
├── spec.md              # Specification document
├── plan.md              # This architecture plan
├── data-model.md        # Data models (user, session, credential, vault)
└── tasks.md             # Test-first task breakdown
```
