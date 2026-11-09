# Spec 01 — Authentication, Security & User Platform

**Project**: Atlas AI Trading OS  
**Status**: Ratified | **Version**: 1.0.0 | **Date**: 2026-09-21  
**Target Path**: `specs/spec-01-auth-security/`  
**Constitutional Compliance**: Core Principles I, II, VIII, XI, XII Verified  

---

## 1. Vision & Goals

### 1.1 System Vision
Spec 01 defines the banking-grade security and identity backbone for Atlas AI Trading OS. In an operating system capable of placing financial market orders and executing capital allocations, user identity, broker credentials, and agent authorization require military-grade defense-in-depth. Spec 01 guarantees that sensitive API secrets are never exposed to clients, sessions cannot be hijacked, and unauthorized actions are barred by default.

### 1.2 Core Business & Technical Goals
- **Zero-Trust Identity**: Granular, role-based authorization where all requests must be authenticated, session-validated, and permission-checked server-side before reaching domain logic.
- **Envelope-Encrypted Credential Vault**: Broker API keys, private exchange secrets, and AI provider credentials are encrypted using AES-256-GCM envelope encryption with a Key Encryption Key (KEK) managed via Hardware Security Module / KMS. Plaintext secrets are never stored and never returned to client interfaces.
- **Frictionless Omnichannel Authentication**: Unified login supporting Password (Argon2id), OAuth2/OIDC (Google, GitHub, Apple), Passwordless Magic Links, and Time-based One-Time Password (TOTP) MFA.
- **Continuous Session & Anomaly Auditing**: Dynamic device fingerprinting, GeoIP travel anomaly detection, rotating refresh tokens with automatic family revocation upon reuse, and tamper-evident security logs.
- **Privacy by Design**: Complete compliance with GDPR and CCPA, providing automated one-click personal data export and event-driven cryptographic shredding for account deletion.

---

## 2. Functional Requirements

- **FR-001**: The platform MUST support email/password registration with mandatory email verification before full trading authorization.
- **FR-002**: Password hashing MUST utilize Argon2id (parameters: 64MiB memory, 3 iterations, 4 parallelism lanes).
- **FR-003**: The platform MUST support OAuth 2.0 / OpenID Connect federation for Google, GitHub, and Apple with automated account linking safeguards.
- **FR-004**: The platform MUST support TOTP (RFC 6238) multi-factor authentication with QR code setup and cryptographically random 8-character single-use backup recovery codes.
- **FR-005**: Authentication tokens MUST use ES256 (ECDSA using P-256 and SHA-256) asymmetric JWTs with a 15-minute access token lifespan and automated public key publishing via `/.well-known/jwks.json`.
- **FR-006**: Long-lived sessions MUST be maintained via rotating refresh tokens delivered exclusively over HTTPS in secure `__Host-` prefixed, `HttpOnly`, `SameSite=Strict` cookies.
- **FR-007**: Refresh token reuse MUST immediately trigger family revocation, invalidating all associated active sessions for that user identity.
- **FR-008**: The Credential Vault MUST encrypt all third-party secrets (broker API keys, exchange secrets, webhook signatures) using per-credential Data Encryption Keys (DEK) wrapped by a root KEK.
- **FR-009**: Client-facing interfaces MUST only ever receive masked references (e.g. `binance_api_****3a9f`) and connection health flags, never raw plaintext keys.
- **FR-010**: The platform MUST enforce Role-Based Access Control (RBAC) supporting roles: `Guest`, `User`, `Trader_Pro`, `Admin`, `Org_Owner`, `Team_Member`, and `Support`.
- **FR-011**: The platform MUST log all security-sensitive events (logins, failed attempts, password changes, credential additions, MFA toggles) to an immutable audit stream with client IP hashing and User-Agent parsing.
- **FR-012**: Anomaly detection engines MUST trigger step-up MFA or temporary account freezes upon detecting impossible travel (>800 km/h between logins) or repetitive failed attempts.
- **FR-013**: The platform MUST support one-click GDPR/CCPA data export (JSON package) and crypto-shredding account deletion, broadcasting `atlas.privacy.user_deleted` events to all downstream databases and vector stores.

---

## 3. Non-Functional Requirements

- **NFR-001 (Authentication Latency)**: JWT validation and session cache check overhead MUST NOT exceed 10ms at p95. Argon2id password hashing is bounded to ~300ms on server CPUs.
- **NFR-002 (Vault Encryption Overhead)**: Credential decryption inside the server execution path MUST complete in < 5ms.
- **NFR-003 (Rate Limiting & Anti-Abuse)**: Login endpoints MUST strictly enforce rate limits (maximum 5 attempts per IP per minute, with exponential backoff and CAPTCHA / bot challenge after 3 failures).
- **NFR-004 (Token Key Rotation)**: The platform MUST support zero-downtime ES256 keypair rotation with overlapping validation grace periods (minimum 24 hours).
- **NFR-005 (Cryptographic Zeroization)**: Decrypted secret buffers in memory MUST be explicitly wiped/zeroized immediately after dispatching requests to external brokers.

---

## 4. User Stories

### US-001: Frictionless & Secure Account Onboarding (Priority: P1)
- **Given** a new trader registering for the platform,
- **When** they register with email/password or Google OAuth and complete verification,
- **Then** their account is activated, a cryptographic session is established, and baseline security defaults (device cookie, default risk role) are provisioned.

### US-002: Broker API Credential Vaulting (Priority: P1)
- **Given** an active trader linking their Binance or MetaTrader broker account,
- **When** they paste their API Key and Secret into the secure credentials modal,
- **Then** the server encrypts the secrets using envelope AES-256-GCM, stores the ciphertext in PostgreSQL, tests the connection health, and displays only a masked identifier.

### US-003: Step-Up Authentication for High-Risk Operations (Priority: P2)
- **Given** a user attempting to increase position leverage, withdraw capital, or rotate API keys,
- **When** the operation is submitted,
- **Then** the platform detects a high-risk security boundary and demands immediate TOTP MFA confirmation before allowing the request to proceed.

### US-004: Suspicious Login Anomaly Defense (Priority: P2)
- **Given** an attacker attempting to access an account from an unrecognised IP in a different country within 10 minutes of a legitimate session,
- **When** the login attempt occurs,
- **Then** the platform blocks the session, dispatches a security warning email to the owner, and requires email-link identity re-verification.

---

## 5. Agent Architecture

Spec 01 defines the **Security Agent** and the **Authorization Policy Guard**:

```text
+-------------------------------------------------------------------------+
|                        Security & Auth Subsystem                        |
|                                                                         |
|   +-----------------------+                +-------------------------+  |
|   |   Security Agent      |                | Authorization Gate      |  |
|   |   - Anomaly monitor   |                | - Scope & RBAC check    |  |
|   |   - Audit analysis    |                | - Rate limit evaluation |  |
|   |   - Threat mitigation |                | - Step-up MFA trigger   |  |
|   +-----------+-----------+                +------------+------------+  |
|               |                                         |               |
|               v                                         v               |
|   +------------------------------------------------------------------+  |
|   |                       Auth Middleware Stack                      |  |
|   |         (Cookie Parser -> JWT Verify -> Session Revocation)      |  |
|   +---------------------------------+--------------------------------+  |
|                                     |                                   |
|                                     v                                   |
|   +------------------------------------------------------------------+  |
|   |                  Envelope Vault Service                          |  |
|   |         (AES-256-GCM + AWS KMS / Vault KEK Provider)             |  |
|   +------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
```

### Agent Authorization Boundaries
- AI Agents operate under delegated permissions granted by the authenticated user.
- Agents CANNOT access raw broker secrets; they dispatch requests through the server-side Execution Gateway which retrieves and injects credentials at the adapter perimeter.
- Any agent action exceeding pre-authorized risk thresholds triggers an automated authorization freeze until human confirmation is received.

---

## 6. State Design

### 6.1 User Account Lifecycle State Machine
```text
[REGISTERED] ---> (Email Verified) ---> [ACTIVE] <---> [STEP_UP_REQUIRED]
      |                                    |
      +---> (Lockout / Anomaly) ---------> [SUSPENDED]
                                           |
                                           v
                                        [DELETED / CRYPTO_SHREDDED]
```

### 6.2 Session Record Schema
```python
@dataclass(frozen=True)
class SessionState:
    session_id: str
    user_id: str
    role: str
    device_id: str
    ip_address_hash: str
    user_agent: str
    mfa_authenticated: bool
    created_at: datetime
    expires_at: datetime
    is_revoked: bool
```

---

## 7. LangGraph Workflow Integration

In LangGraph workflows that interact with trading accounts, the security checkpoint node gates execution:

```text
[Agent Intent Proposed]
         |
         v
+------------------------+
| Security Policy Node   |  Check: Does intent require elevated privileges?
+-----------+------------+
            |
            +--- (No / Safe) ----------> [Execution Node]
            |
            +--- (Yes / Exceeds Risk) -> [Interrupt: Step-Up MFA Challenge]
                                                   |
                                                   v
                                         (User submits TOTP)
                                                   |
                                                   +---> [Resume Execution]
```

- Node uses `interrupt_before=["execute_order"]` when the user has configured mandatory MFA on all trade executions.

---

## 8. Tool Specifications

### 8.1 Credential Vault Tool (`tool_vault_store_credential`)
- **Description**: Securely envelopes and saves external broker or exchange API credentials.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["venue_id", "credential_type", "key", "secret"],
    "properties": {
      "venue_id": { "type": "string" },
      "credential_type": { "type": "string", "enum": ["api_key", "oauth_token", "private_key"] },
      "key": { "type": "string" },
      "secret": { "type": "string" },
      "passphrase": { "type": "string" },
      "environment": { "type": "string", "enum": ["live", "demo"] }
    }
  }
  ```
- **Output Schema**: Returns `{ "credential_id": "c_...", "masked_key": "abc...123", "status": "active" }`.
- **Security**: Strict write-only. Plaintext parameters are sanitized from execution traces immediately.

### 8.2 Session Invalidation Tool (`tool_auth_revoke_session`)
- **Description**: Revokes one or all active user sessions across devices.
- **Input Schema**:
  ```json
  {
    "type": "object",
    "required": ["user_id"],
    "properties": {
      "user_id": { "type": "string" },
      "session_id": { "type": "string" },
      "revoke_all": { "type": "boolean", "default": false }
    }
  }
  ```

---

## 9. API Specifications

### 9.1 Authentication & Session Routes
- **`POST /api/v1/auth/register`**: Account creation with password strength validation.
- **`POST /api/v1/auth/login`**: Authenticates user; returns user profile and sets secure `__Host-atlas_rf` cookie.
- **`POST /api/v1/auth/refresh`**: Rotates refresh token; issues new 15-minute ES256 access JWT.
- **`POST /api/v1/auth/logout`**: Invalidates current session and clears cookies.
- **`GET /api/v1/auth/.well-known/jwks.json`**: Public JSON Web Key Set containing active ES256 signing keys.

### 9.2 MFA Operations
- **`POST /api/v1/auth/mfa/totp/setup`**: Generates new TOTP secret and QR code URI.
- **`POST /api/v1/auth/mfa/totp/verify`**: Verifies 6-digit code; activates MFA and returns 10 backup codes.
- **`POST /api/v1/auth/mfa/challenge`**: Resolves step-up MFA challenge during sensitive operations.

### 9.3 Credential Vault Operations
- **`POST /api/v1/vault/credentials`**: Saves and encrypts a venue credential.
- **`GET /api/v1/vault/credentials`**: Lists all connected credentials with masked identifiers and health status.
- **`DELETE /api/v1/vault/credentials/{id}`**: Revokes and deletes a credential with crypto-shredding.

---

## 10. Database Schema

### 10.1 Users Table (`auth_users`)
```sql
CREATE TABLE auth_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255),
    role VARCHAR(32) NOT NULL DEFAULT 'User',
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING_VERIFICATION',
    mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    failed_login_attempts INT NOT NULL DEFAULT 0,
    lockout_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON auth_users (email);
```

### 10.2 Sessions Table (`auth_sessions`)
```sql
CREATE TABLE auth_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(64) NOT NULL UNIQUE,
    device_id VARCHAR(128) NOT NULL,
    ip_hash VARCHAR(64) NOT NULL,
    user_agent VARCHAR(256),
    mfa_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_user_active ON auth_sessions (user_id) WHERE is_revoked = FALSE;
```

### 10.3 Credential Vault Table (`credentials_vault`)
```sql
CREATE TABLE credentials_vault (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    venue_id VARCHAR(64) NOT NULL,
    credential_type VARCHAR(32) NOT NULL,
    masked_identifier VARCHAR(64) NOT NULL,
    encrypted_payload BYTEA NOT NULL, -- AES-256-GCM ciphertext
    payload_nonce BYTEA NOT NULL,     -- 12-byte IV
    auth_tag BYTEA NOT NULL,          -- 16-byte authentication tag
    encrypted_dek BYTEA NOT NULL,     -- DEK wrapped with KEK
    kek_version VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'HEALTHY',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_venue_type UNIQUE (user_id, venue_id, credential_type)
);

CREATE INDEX idx_vault_user ON credentials_vault (user_id);
```

---

## 11. Frontend Screens & Components

### 11.1 Modern Glassmorphic Login & Sign-Up
- Single card layout with dark obsidian backing (`#0D0F17`), subtle ambient blue border glow, tabbed toggle between Sign In / Sign Up.
- Social buttons: Google, GitHub, Apple with SVG brand icons.
- Real-time password strength meter utilizing `zxcvbn` estimation with helpful entropy suggestions.

### 11.2 Security Center Dashboard
- **Connected Devices Panel**: Shows current session with green badge, lists all other active devices with browser, OS, GeoIP country flag, and "Revoke" button.
- **Two-Factor Authentication Widget**: Status toggle, QR code modal with manual entry fallback, backup code regenerator.
- **Credential Vault Manager**: Grid of connected venues (Binance, Bybit, MT5) showing connection ping, API rate limit status, and key rotation dates.

---

## 12. Security Requirements

- **SEC-001 (OWASP ASVS Level 3 Compliance)**: Strict defense against credential stuffing, session fixation, timing attacks, and CSRF.
- **SEC-002 (Constant-Time Comparisons)**: All token hash comparisons, password checks, and authentication tags use `hmac.compare_digest` to prevent timing attacks.
- **SEC-003 (Cookie Security)**: Refresh tokens use `__Host-` prefix, `Secure`, `HttpOnly`, `SameSite=Strict`, and `Path=/api/v1/auth`.
- **SEC-004 (Key Encryption Key Isolation)**: Root KEK is stored in AWS KMS / HashiCorp Vault. Under no circumstances is the KEK stored in application code or the application database.
- **SEC-005 (Audit Immutability)**: All audit records are write-only append logs; modification or deletion is blocked by database triggers and IAM privileges.

---

## 13. Testing Strategy

- **Argon2id Benchmarking**: Automated tests verify password hashing computation meets memory and CPU timing thresholds.
- **Refresh Token Rotation Abuse Tests**: Simulate concurrent requests with stale refresh tokens; verify entire token family is invalidated immediately.
- **Envelope Encryption Conformance**: Validate that modifying even a single bit in the ciphertext or nonce causes decryption failure (`InvalidTagException`).
- **CSRF Double-Submit Validation**: Mutation requests lacking valid CSRF headers are rejected with HTTP 403.
- **Schemathesis OpenAPI Testing**: Fuzz all auth endpoints with invalid input schemas to verify zero unhandled exceptions.

---

## 14. Deployment Plan

- **KMS Configuration**: Automated Terraform provisioning of AWS KMS symmetric encryption key with key rotation enabled.
- **Redis Cluster Session Cache**: High-availability Redis instance with replication for sub-millisecond session state lookup and token revocation denylists.
- **Email Infrastructure**: Mailpit integration for local Docker Compose testing; AWS SES / Resend with DKIM, SPF, and DMARC for production dispatch.

---

## 15. Future Enhancements

- **FIDO2 / WebAuthn Passkeys**: Native biometric login using Touch ID, Face ID, and YubiKeys.
- **Decentralized Identity (DID)**: Self-sovereign identity login using Ethereum / Solana wallet signatures (EIP-4361 Sign-in with Ethereum).
- **Zero-Knowledge Proof Audit Queries**: Verify compliance and solvency without disclosing trading strategies or account balances.
