# `credentials` module

The envelope-encrypted vault for user-owned external secrets: broker and exchange API keys,
AI provider keys, webhook and notification tokens. Spec:
[`specs/002-auth-security`](../../../../../../specs/002-auth-security/spec.md) US3.

## Import surface

Other modules import `credentials.public` only:

| Symbol | Purpose |
|---|---|
| `build_credentials_module()` | `ModuleDef` for `create_app` |
| `use_credential(id, purpose)` | Async context manager yielding a plaintext handle for exactly one operation |

`use_credential` is the *only* way plaintext is ever produced, and it is server-side only.
Spec 03's `atlas_venues.credentials.CredentialProvider` port is satisfied by this module —
registration happens in `build_credentials_module()`, so trading adapters written against
the port get the real vault with no change.

## Why there is no read endpoint

There is no API, for any role including `admin`, that returns a stored secret. Reads return
`masked_hint` (last four characters) and metadata. This is a structural guarantee rather than
a permission check: the response schemas have no field a secret could occupy, and a contract
test asserts that.

## Crypto

```text
plaintext ──AES-256-GCM──► ciphertext        (per-credential 256-bit DEK)
                    DEK ──wrap──► wrapped_dek (KEK held in KMS; env-var KEK for local only)
AAD = {user_id, credential_id, version}      ciphertext cannot be replayed onto another row
```

Deletion is **crypto-shredding**: dropping the wrapped DEK makes the ciphertext
unrecoverable, including in backups taken before the deletion. KEK rotation rewraps DEKs in
the background and never rewrites ciphertext.

## Layers

```text
router.py            /credentials, /connected-accounts. No response field can hold a secret.
public.py            build_credentials_module() + use_credential()
service/
  crypto.py            EnvelopeCrypto, KekProvider (LocalEnvKek, KmsKek)
  vault.py             create / rotate / revoke / delete / validate
  connected_accounts.py Link, status transitions, health probes
domain/              Credential + version + account entities and lifecycle state machines.
repository/          Port implementations: in-memory and SQLAlchemy.
migrations/versions/ Alembic revisions on the `credentials` branch label.
```

## Invariants

1. Plaintext exists only in request memory during create/rotate, and in-process during an
   authorized `use_credential` block. It is never logged, evented, cached, or serialized.
2. Retrieval purpose must be in the credential's `allowed_purposes`. A `read_only` key cannot
   be used to place an order.
3. Revocation takes effect on the next retrieval — no authorization decision or plaintext is
   cached beyond a single request.
4. Every create, rotate, revoke, delete, validate, and retrieve writes an audit entry.
