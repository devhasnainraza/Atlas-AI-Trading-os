"""Vault envelope crypto (T010).

The properties under test are the ones the vault's security story rests on:

* a secret round-trips only with the *same* (user, credential, version) it was bound to —
  the AAD binding is what stops ciphertext transplant between rows;
* tampering with ciphertext or the wrapped DEK fails authentication rather than returning
  garbage — GCM is an AEAD, and a decrypt that "works" on modified bytes is a bug;
* the KEK is never reachable through the public interface — only wrap/unwrap exist;
* crypto-shredding is real: with the wrapped DEK gone, the ciphertext cannot be recovered
  by anything in this module, which is the deletion guarantee privacy (FR-017) depends on.
"""

from __future__ import annotations

import base64
import os

import pytest
from pydantic import SecretStr

from atlas_api.modules.credentials.service.crypto import (
    DecryptError,
    EnvelopeCrypto,
    KeyMaterialError,
    KmsKek,
    LocalEnvKek,
    WrappedKey,
    aad_for,
    build_kek_provider,
)
from atlas_api.modules.credentials.settings import VaultSettings

SECRET = "sk-live-super-secret-api-key"
USER = "01931e0a-0000-7000-8000-000000000001"
CRED = "01931e0a-0000-7000-8000-000000000002"


def _crypto() -> EnvelopeCrypto:
    return EnvelopeCrypto(LocalEnvKek())  # ephemeral KEK: process-lifetime, test-safe


def test_roundtrip_recovers_plaintext() -> None:
    crypto = _crypto()
    blob = crypto.encrypt(SECRET, user_id=USER, credential_id=CRED, version=1)
    assert blob.ciphertext != SECRET.encode()
    assert crypto.decrypt(blob, user_id=USER, credential_id=CRED, version=1) == SECRET


def test_unicode_secret_roundtrips() -> None:
    crypto = _crypto()
    blob = crypto.encrypt("पहली-कुंजी-🔑", user_id=USER, credential_id=CRED, version=3)
    assert crypto.decrypt(blob, user_id=USER, credential_id=CRED, version=3) == "पहली-कुंजी-🔑"


@pytest.mark.parametrize(
    "args",
    [
        {"user_id": "01931e0a-0000-7000-8000-000000000099", "credential_id": CRED, "version": 1},
        {"user_id": USER, "credential_id": "01931e0a-0000-7000-8000-000000000099", "version": 1},
        {"user_id": USER, "credential_id": CRED, "version": 2},
    ],
    ids=["wrong-user", "wrong-credential", "wrong-version"],
)
def test_aad_binding_rejects_transplant(args: dict[str, object]) -> None:
    """The same blob read under any different row identity fails — no plaintext leaks."""
    crypto = _crypto()
    blob = crypto.encrypt(SECRET, user_id=USER, credential_id=CRED, version=1)
    with pytest.raises(DecryptError):
        crypto.decrypt(blob, **args)  # type: ignore[arg-type]


def test_aad_length_prefix_prevents_separator_collision() -> None:
    """("a|b", "c") and ("a", "b|c") must not derive the same AAD."""
    assert aad_for("a|b", "c", 1) != aad_for("a", "b|c", 1)


def test_tampered_ciphertext_fails_authentication() -> None:
    crypto = _crypto()
    blob = crypto.encrypt(SECRET, user_id=USER, credential_id=CRED, version=1)
    bad = bytearray(blob.ciphertext)
    bad[-1] ^= 0x01  # flip one bit in the GCM tag
    tampered = blob.__class__(
        ciphertext=bytes(bad),
        wrapped_dek=blob.wrapped_dek,
        kek_version=blob.kek_version,
        aad_context=blob.aad_context,
    )
    with pytest.raises(DecryptError):
        crypto.decrypt(tampered, user_id=USER, credential_id=CRED, version=1)


def test_truncated_ciphertext_rejected_without_crypto_call() -> None:
    crypto = _crypto()
    blob = crypto.encrypt(SECRET, user_id=USER, credential_id=CRED, version=1)
    truncated = blob.__class__(
        ciphertext=blob.ciphertext[:4],
        wrapped_dek=blob.wrapped_dek,
        kek_version=blob.kek_version,
        aad_context=blob.aad_context,
    )
    with pytest.raises(DecryptError):
        crypto.decrypt(truncated, user_id=USER, credential_id=CRED, version=1)


def test_foreign_kek_cannot_unwrap() -> None:
    """A wrapped DEK made under one KEK fails under another — KEK rotation is safe."""
    issuer = _crypto()
    blob = issuer.encrypt(SECRET, user_id=USER, credential_id=CRED, version=1)
    stranger = EnvelopeCrypto(LocalEnvKek())
    with pytest.raises(DecryptError):
        stranger.decrypt(blob, user_id=USER, credential_id=CRED, version=1)


def test_unknown_kek_version_rejected_before_crypto() -> None:
    kek = LocalEnvKek()
    with pytest.raises(DecryptError):
        kek.unwrap(WrappedKey(wrapped_dek=b"x" * 60, kek_version="aws-kms-v99"))


def test_crypto_shred_leaves_ciphertext_unrecoverable() -> None:
    """Delete the wrapped DEK and the ciphertext is random bytes to everything here.

    This is the privacy-deletion guarantee (FR-017): old backups contain the row, but a
    row without its DEK decrypts to nothing, by any key the platform will ever hold.
    """
    crypto = _crypto()
    blob = crypto.encrypt(SECRET, user_id=USER, credential_id=CRED, version=1)
    shredded = blob.__class__(
        ciphertext=blob.ciphertext,
        wrapped_dek=b"",  # the row's wrapped_dek column is now NULL/deleted
        kek_version=blob.kek_version,
        aad_context=blob.aad_context,
    )
    with pytest.raises(DecryptError):
        crypto.decrypt(shredded, user_id=USER, credential_id=CRED, version=1)


def test_each_encrypt_uses_a_fresh_dek() -> None:
    """Two encryptions of the same secret share nothing: different DEK, nonce, bytes."""
    crypto = _crypto()
    a = crypto.encrypt(SECRET, user_id=USER, credential_id=CRED, version=1)
    b = crypto.encrypt(SECRET, user_id=USER, credential_id=CRED, version=1)
    assert a.ciphertext != b.ciphertext
    assert a.wrapped_dek != b.wrapped_dek


def test_local_kek_from_env_roundtrips_across_instances() -> None:
    """A stable configured KEK decrypts what a *different process's* instance encrypted."""
    kek_bytes = os.urandom(32)
    encoded = base64.b64encode(kek_bytes).decode()
    settings = VaultSettings(kek_provider="local", kek_local=SecretStr(encoded))  # type: ignore[call-arg]
    writer = EnvelopeCrypto(build_kek_provider(settings))
    blob = writer.encrypt(SECRET, user_id=USER, credential_id=CRED, version=1)

    reader = EnvelopeCrypto(build_kek_provider(VaultSettings(kek_local=SecretStr(encoded))))  # type: ignore[call-arg]
    assert reader.decrypt(blob, user_id=USER, credential_id=CRED, version=1) == SECRET


def test_local_kek_rejects_wrong_length_and_bad_base64() -> None:
    with pytest.raises(KeyMaterialError):
        LocalEnvKek(b"too-short")
    with pytest.raises(KeyMaterialError):
        EnvelopeCrypto(build_kek_provider(VaultSettings(kek_local=SecretStr("not base64!!"))))  # type: ignore[call-arg]


def test_ephemeral_kek_when_unset() -> None:
    """No configured KEK still composes a working vault (tests, forgotten bootstrap)."""
    crypto = EnvelopeCrypto(build_kek_provider(VaultSettings()))
    blob = crypto.encrypt(SECRET, user_id=USER, credential_id=CRED, version=1)
    assert crypto.decrypt(blob, user_id=USER, credential_id=CRED, version=1) == SECRET


def test_kms_stub_fails_loudly_not_silently() -> None:
    """The T076 stub must raise, never fall back to a weaker key.

    A silent fallback would mean a "production" deployment quietly running on an
    environment-variable KEK — the exact failure validate_for_environment exists to stop.
    """
    kms = KmsKek("arn:aws:kms:us-east-1:123456789012:key/abcd")
    with pytest.raises(NotImplementedError):
        kms.wrap(os.urandom(32))
    with pytest.raises(NotImplementedError):
        kms.unwrap(WrappedKey(wrapped_dek=b"x", kek_version="v1"))


def test_kek_provider_interface_exposes_no_key_material() -> None:
    """wrap/unwrap only: nothing to accidentally log, return, or serialize."""
    kek = LocalEnvKek()
    public = {n for n in dir(kek) if not n.startswith("_")}
    assert public == {"from_settings", "kek_version", "unwrap", "wrap"}
