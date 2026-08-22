---
id: 0002
title: Plan auth security blueprint
stage: plan
date: 2026-08-04
surface: agent
model: claude-fable-5
feature: 002-auth-security
branch: 002-auth-security
user: user
command: /sp.plan
labels: ["plan", "authentication", "security", "iam", "vault", "rbac", "mfa"]
links:
  spec: specs/01-auth-security/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/01-auth-security/plan.md
 - specs/01-auth-security/research.md
 - specs/01-auth-security/data-model.md
 - specs/01-auth-security/contracts/auth-api.openapi.yaml
 - specs/01-auth-security/contracts/auth-events.md
 - specs/01-auth-security/quickstart.md
 - CLAUDE.md (agent context updated manually; script expects branch-named spec dir)
tests:
 - none (planning artifacts; Constitution Check PASS pre- and post-design)
---

## Prompt

# /sp.plan

You are acting as a Principal Security Engineer, Principal Software Architect, Staff Backend Engineer, Platform Engineer, Identity & Access Management (IAM) Architect, and Cloud Security Architect.

Your task is to create the complete implementation plan for:

# Spec 01 — Authentication, Security & User Platform

This is NOT a coding task. This is NOT an implementation. Your responsibility is to design
the complete technical implementation plan that future developers and AI coding agents will
follow. The output should be detailed enough for an engineering team to implement without
making architectural decisions themselves.

Project: Atlas AI Trading OS — "Build the world's most secure AI-powered Trading Operating
System for Forex & Crypto Trading using Multi-Agent AI, LangGraph workflows, secure broker
integrations, and enterprise-grade cloud architecture." Spec 00 already established the
platform foundation, project structure, event system, infrastructure, and development
standards. This specification focuses only on Authentication, Identity, Authorization,
User Security, API Credential Protection, Privacy, and User Management.

Required sections (25): 1 High-Level Architecture (identity/auth/authz/session/API-key/
broker-credential flows, security & trust boundaries, diagrams); 2 Authentication Strategy
(email+password, Google, GitHub, Apple, magic links, passwordless, passkeys future;
lifecycle, onboarding, account linking, email verification); 3 User Registration Flow
(verification, profile, terms/privacy/risk acceptance, initial preferences & risk profile,
welcome, extensibility); 4 Identity Management (identity, providers, linked accounts,
verification, primary/secondary identity, enterprise identity & SSO future); 5
Authorization (RBAC: Guest, Free, Premium, Admin, Support, Org Owner, Org Admin, Team
Member, custom future; inheritance + boundaries); 6 Session Management (access/refresh
tokens, rotation, expiration, remember device, fingerprinting, trusted devices, logout/
logout-all, revocation, concurrent sessions, idle/absolute timeout); 7 MFA (TOTP, recovery
codes, trusted devices, enforced/enterprise MFA, backup auth, recovery flow); 8 Password
Security (policies, hashing, reset, history, compromised detection, expiration, rate
limiting, brute force); 9 Broker Credential Protection (broker/exchange API keys, secrets,
trading passwords, OAuth tokens; encryption, rotation, revocation, least privilege, secure
retrieval, zero frontend exposure, lifecycle); 10 AI Provider Credentials (OpenAI,
Anthropic, Gemini, Groq, OpenRouter, Azure OpenAI, future; user-owned, never exposed);
11 API Key Vault (encryption, versioning, metadata, expiration, rotation, permissions,
audit, revocation); 12 User Profile (personal info, trading experience, markets, languages,
timezone, risk/notification/privacy preferences, personalization future); 13 Connected
Accounts (brokers, exchanges, social, notification, API providers; status/health/
permissions/last-sync/errors/reconnect); 14 Security Center (score, recent logins, trusted
devices, sessions, API keys, brokers, MFA, password health, risk alerts, recommendations);
15 Audit Logging (immutable; login/logout, password changes, API changes, broker
connections, permission changes, security events, admin actions, sensitive operations);
16 Privacy & Compliance (export, account/data deletion, consent, privacy settings, cookies,
GDPR/CCPA future, retention); 17 Security Architecture (encryption at rest/in transit,
secrets & key management, certificates, headers, CSRF, CORS, input validation, output
sanitization, zero trust); 18 Threat Modeling (credential theft, token theft, session
hijacking, brute force, replay, CSRF, XSS, SSRF, SQLi, API abuse, bots, insiders — each
with attack/impact/mitigation/monitoring/recovery); 19 Monitoring (failed logins,
suspicious activity, impossible travel, multiple devices, credential/token/API abuse,
broker credential access); 20 Error Handling (never expose secrets, stack traces, DB
errors, infrastructure, token values, broker info); 21 Database Planning (entities only,
no SQL: users, sessions, devices, roles, permissions, audit logs, API keys, broker
connections, OAuth accounts, security events); 22 API Planning (REST surface: auth,
profile, security, session, connected account, API key, admin APIs); 23 Testing Strategy
(unit, integration, security, penetration, authn/authz, load, recovery); 24 Deployment
Strategy (environment separation, secrets, infrastructure, scaling, HA, DR, rollback,
backups); 25 Risks (security, operational, performance, privacy, scalability, compliance,
future — with mitigation for every risk).

Expected output: enterprise-grade, startup-ready, security-first, AI-ready, cloud-native,
highly detailed, future-proof, maintainable. Avoid implementation code. The final document
becomes the official implementation blueprint for Spec 01.

## Response snapshot

Produced the Spec 01 blueprint (all 25 sections) plus Phase 0/1 artifacts on branch
`002-auth-security` against `specs/01-auth-security/`:

- **plan.md** — custom FastAPI IAM as `auth` + `credentials` modules (build-over-buy
  justified in Complexity Tracking vs Auth0/Clerk/Keycloak/Better Auth); ES256 15-min JWTs
  (JWKS, 90d kid rotation) + opaque rotating refresh tokens with reuse-detection family
  revocation; `__Host-` HttpOnly cookies + CSRF double-submit; Argon2id (64MiB/t3/p4) +
  zxcvbn + HIBP k-anonymity; TOTP MFA + hashed recovery codes + step-up freshness for
  sensitive ops; flat RBAC (`domain:resource:action`) with scope-ready assignments and
  `roles_ver` instant permission refresh; envelope-encrypted vault (per-credential AES-256-
  GCM DEKs wrapped by KMS KEK, AAD-bound, crypto-shredding deletion, zero plaintext read
  path for any role); connected accounts w/ health probes; Security Center aggregate with
  versioned score; append-only audit with hash-chain checkpoints; privacy export/deletion
  with mandatory `atlas.privacy.user_erasure.requested` consumer contract; threat model
  (12 threats × mitigation/monitoring/recovery); monitoring incl. impossible travel and
  vault-access anomalies; enumeration-resistant error handling; testing incl. abuse suite
  and pentest gate; deployment on Spec 00 infra + KMS/GeoIP/Mailpit additions; 10-risk
  register. Constitution Check 12/12 PASS pre and post design.
- **research.md** — 15 decision records (build-vs-buy, token model, cookie transport,
  Argon2id, HIBP, Authlib, TOTP, envelope crypto, RBAC shape, rate limiting, device/geo
  signals, email via notification seam, hashed one-time tokens, PG+Redis session store,
  async privacy jobs).
- **data-model.md** — 22 entities with fields, rules, state machines (user status, session
  family, credential lifecycle), erasure-handler coverage rule, retention windows.
- **contracts/auth-api.openapi.yaml** — ~40 operations across auth/MFA/profile/sessions/
  vault/connected-accounts/security/api-keys/privacy/admin with enumeration-safe response
  patterns and write-only SecretPayload.
- **contracts/auth-events.md** — 23-event catalog for atlas.auth/credentials/privacy with
  consumer obligations (mandatory erasure subscription, no-caching credential handles).
- **quickstart.md** — local flows (Mailpit, dev KEK guard, smoke scripts, test suites).
CLAUDE.md agent context updated manually (script expects branch-named specs dir —
mismatch between branch `002-auth-security` and dir `specs/01-auth-security` noted).

## Outcome

- ✅ Impact: Official Spec 01 engineering blueprint complete; ready for /sp.tasks decomposition; Spec 00 SC-011 (auth plannable without foundational rework) validated in practice.
- 🧪 Tests: None run — planning stage; abuse/contract/E2E strategy defined in plan §23.
- 📁 Files: plan.md, research.md, data-model.md, contracts/auth-api.openapi.yaml, contracts/auth-events.md, quickstart.md, CLAUDE.md
- 🔁 Next prompts: /sp.tasks for 01-auth-security; /sp.adr for build-vs-buy IAM + vault crypto decisions (suggested).
- 🧠 Reflection: Branch (002-auth-security) vs specs dir (01-auth-security) naming divergence broke both helper scripts — standardize one convention before /sp.implement to keep tooling deterministic.

## Evaluation notes (flywheel)

- Failure modes observed: update-agent-context.sh and create-phr.sh both assume specs/<branch-name>; repo was reorganized to 0N-prefixed dirs — handled manually.
- Graders run and results (PASS/FAIL): Constitution Check PASS (12/12); 25/25 required sections present; artifact completeness vs command outline PASS.
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Align scripts or dir naming (rename specs dirs to match branches, or patch scripts' dir resolution) — propose in next /sp.tasks run.
