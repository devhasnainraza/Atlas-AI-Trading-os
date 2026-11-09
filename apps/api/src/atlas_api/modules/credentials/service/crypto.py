"""Envelope encryption for the credential vault (T010; plan §9, research §8).

The pattern, in one paragraph: every secret is encrypted with its own random 256-bit
data-encryption key (DEK) using AES-256-GCM; the DEK is itself encrypted ("wrapped") by a
key-encryption key (KEK) that lives in a KMS in deployed environments. A row is therefore
``(wrapped_dek, ciphertext)`` — useless without the KEK, and the KEK never leaves the HSM.

Why each piece is the way it is:

* **Per-credential DEK.** Breach blast radius is one secret, not the vault. An attacker
  with the database and one unwrapped DEK reads one credential.
* **AAD binding.** The additional-authenticated-data is ``(user_id, credential_id,
  version)``. GCM verifies it on decrypt, so a ciphertext copied onto another row — an
  attacker's "swap my credential for the victim's" — fails authentication. Encryption is
  not just confidentiality; here the binding *is* the integrity property that matters.
* **KEK version on the row.** Rotation rewraps DEKs in the background (the ciphertext is
  never rewritten); the stored ``kek_version`` says which key generation unwraps this row,
  so a half-finished rewrap is safe to resume and an old backup still decrypts while the
  old KEK generation is kept alive.
* **Crypto-shredding.** Deleting a secret means deleting its wrapped DEK. The ciphertext
  in a six-month-old backup is then indistinguishable from random bytes — deletion is
  real even where row-deletion is not. There is no code here to write: the shred is
  ``DELETE FROM credential_version``, which is exactly why the design chose this shape.

The KEK interface is a :class:`KekProvider` protocol so the local dev implementation
(a 32-byte key from the environment, refused outside local/test by
:meth:`VaultSettings.validate_for_environment`) and the cloud-KMS implementation are
interchangeable without touching this module's callers.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from atlas_api.modules.credentials.settings import VaultSettings

#: Nonce size for AES-GCM. 96 bits is the size GCM is designed for: other lengths force
#: an extra GHASH pass and, more importantly, 12 bytes is what every interoperating
#: implementation (KMS ``Encrypt``, libsodium, WebCrypto) uses by default.
_NONCE_LEN = 12

#: DEK and KEK size: 256 bits, the AES-256 in "AES-256-GCM".
_KEY_LEN = 32

#: Domain-separation prefix for the AAD. Without it, a future second use of AES-GCM in
#: this codebase could produce an AAD that a vault ciphertext also matches.
_AAD_PREFIX = b"atlas-vault:v1"


class VaultCryptoError(Exception):
    """Base for vault crypto failures. Mapped to ATLAS-CRED-* codes (T014)."""


class KeyMaterialError(VaultCryptoError):
    """The KEK is missing, malformed, or of the wrong length — a configuration fault."""


class DecryptError(VaultCryptoError):
    """Authentication failed: tampered ciphertext, wrong KEK, or AAD mismatch.

    One error for all three deliberately: the differences are not actionable by callers
    and must not be distinguishable in any response or log line that leaves the process.
    """


@dataclass(frozen=True)
class WrappedKey:
    """A DEK encrypted by a KEK, plus the KEK generation that produced it.

    ``kek_version`` travels with the wrapped key because a KMS returns it and the local
    provider must behave the same way: the row stores both, and unwrap needs both.
    """

    wrapped_dek: bytes
    kek_version: str


@dataclass(frozen=True)
class EncryptedBlob:
    """Everything that goes into a ``credential_version`` row.

    ``aad_context`` is stored alongside for audit and debugging only — decrypt re-derives
    the AAD from the caller's identity arguments and never trusts the stored copy. If it
    did, an attacker who could rewrite the row could rewrite its own binding too.
    """

    ciphertext: bytes
    wrapped_dek: bytes
    kek_version: str
    aad_context: tuple[str, str, int]


class KekProvider(Protocol):
    """Wrap and unwrap DEKs. Implementations: :class:`LocalEnvKek`, :class:`KmsKek`.

    A provider must never expose the KEK itself — the interface is deliberately
    wrap/unwrap-only so no caller can accidentally log or return it. A KMS-backed
    provider keeps the key in an HSM; the local one keeps it in process memory, which is
    why its use outside local/test is a startup error rather than a runtime warning.
    """

    def wrap(self, dek: bytes) -> WrappedKey: ...

    def unwrap(self, wrapped: WrappedKey) -> bytes: ...


class LocalEnvKek:
    """KEK held in process memory, from ``VAULT_KEK_LOCAL`` (base64, 32 bytes).

    Local development only — enforced by :meth:`VaultSettings.validate_for_environment`,
    not by this class, because the class cannot know what environment it is running in
    and a check here would be a check that a motivated deployment could delete.

    When no KEK is configured, an ephemeral one is minted at construction: credentials
    stored under it stop decrypting when the process exits. That is the correct outcome
    for tests and a visible, self-explaining outcome for a developer who forgot to run
    ``scripts/bootstrap``.
    """

    kek_version = "local-v1"

    def __init__(self, kek: bytes | None = None) -> None:
        if kek is None:
            kek = os.urandom(_KEY_LEN)
        if len(kek) != _KEY_LEN:
            raise KeyMaterialError(f"local KEK must be {_KEY_LEN} bytes, got {len(kek)}")
        self._aesgcm = AESGCM(kek)

    @classmethod
    def from_settings(cls, settings: VaultSettings) -> LocalEnvKek:
        kek: bytes | None = None
        if settings.kek_local is not None:
            raw = settings.kek_local.get_secret_value()
            try:
                kek = base64.b64decode(raw, validate=True)
            except Exception as exc:  # binascii.Error and friends
                raise KeyMaterialError("VAULT_KEK_LOCAL is not valid base64") from exc
        return cls(kek)

    def wrap(self, dek: bytes) -> WrappedKey:
        if len(dek) != _KEY_LEN:
            raise KeyMaterialError(f"DEK must be {_KEY_LEN} bytes, got {len(dek)}")
        nonce = os.urandom(_NONCE_LEN)
        wrapped_dek = nonce + self._aesgcm.encrypt(nonce, dek, None)
        return WrappedKey(wrapped_dek=wrapped_dek, kek_version=self.kek_version)

    def unwrap(self, wrapped: WrappedKey) -> bytes:
        if wrapped.kek_version != self.kek_version:
            raise DecryptError(f"unknown kek_version: {wrapped.kek_version!r}")
        raw = wrapped.wrapped_dek
        if len(raw) <= _NONCE_LEN:
            raise DecryptError("wrapped DEK is truncated")
        try:
            return self._aesgcm.decrypt(raw[:_NONCE_LEN], raw[_NONCE_LEN:], None)
        except InvalidTag as exc:
            raise DecryptError("wrapped DEK failed authentication") from exc


class KmsKek:
    """Cloud-KMS KEK provider — interface stub (T076 wires the real client).

    The shape is fixed now because the row format depends on it: ``kek_version`` is
    whatever the KMS says generated the wrapper (a key version id), and ``wrapped_dek``
    is the KMS ciphertext blob verbatim. Implementing ``aws_kms``/``gcp_kms`` later is
    filling in two method bodies, not a schema change.

    Construction succeeds so an app can boot and serve non-vault routes; the first vault
    write fails loudly with this message rather than every write silently falling back to
    something weaker.
    """

    def __init__(self, key_id: str) -> None:
        self._key_id = key_id

    @property
    def key_id(self) -> str:
        return self._key_id

    def wrap(self, dek: bytes) -> WrappedKey:
        raise NotImplementedError(
            "KMS KEK provider is not wired yet (T076); the vault requires a real KMS "
            "client before it can store credentials in a deployed environment"
        )

    def unwrap(self, wrapped: WrappedKey) -> bytes:
        raise NotImplementedError("KMS KEK provider is not wired yet (T076)")


def build_kek_provider(settings: VaultSettings) -> KekProvider:
    """Resolve the configured provider. Called once per app composition."""
    if settings.kek_provider == "local":
        return LocalEnvKek.from_settings(settings)
    # validate_for_environment guarantees kms_key_id is set for a KMS provider in any
    # environment that reaches composition; the assert documents the invariant.
    assert settings.kms_key_id is not None
    return KmsKek(settings.kms_key_id)


def aad_for(user_id: str, credential_id: str, version: int) -> bytes:
    """The canonical AAD binding a ciphertext to its row.

    A length-prefixed encoding rather than ``f"{user_id}|{credential_id}|{version}"``:
    with a bare separator, the pairs ``("a|b", "c")`` and ``("a", "b|c")`` produce the
    same string, and IDs are opaque text. Length prefixes make that collision impossible.
    """
    parts = (_AAD_PREFIX, user_id.encode(), credential_id.encode(), str(version).encode())
    out = bytearray()
    for part in parts:
        out += len(part).to_bytes(2, "big")
        out += part
    return bytes(out)


class EnvelopeCrypto:
    """Encrypt/decrypt vault payloads with per-call DEKs bound to their row.

    Stateless apart from the KEK provider: safe to share across requests, and nothing
    here caches plaintext or DEKs — a decrypt result lives only in the caller's scope.
    """

    def __init__(self, kek: KekProvider) -> None:
        self._kek = kek

    def encrypt(
        self, plaintext: str, *, user_id: str, credential_id: str, version: int
    ) -> EncryptedBlob:
        dek = os.urandom(_KEY_LEN)
        wrapped = self._kek.wrap(dek)
        nonce = os.urandom(_NONCE_LEN)
        aad = aad_for(user_id, credential_id, version)
        ciphertext = nonce + AESGCM(dek).encrypt(nonce, plaintext.encode(), aad)
        # Zero the DEK reference; CPython refcounting frees the bytes object promptly.
        # Not a guarantee (the buffer may have been copied), but it is free hygiene.
        del dek
        return EncryptedBlob(
            ciphertext=ciphertext,
            wrapped_dek=wrapped.wrapped_dek,
            kek_version=wrapped.kek_version,
            aad_context=(user_id, credential_id, version),
        )

    def decrypt(
        self, blob: EncryptedBlob, *, user_id: str, credential_id: str, version: int
    ) -> str:
        """Recover the plaintext, verifying the row binding. Raises :class:`DecryptError`.

        The identity arguments come from the *caller's* context (the authenticated user,
        the row being read), never from ``blob.aad_context`` — that field is stored data
        an attacker with write access to the table could change. Re-deriving the AAD from
        arguments the caller already had to be authorized to pass is what makes the
        binding real.
        """
        raw = blob.ciphertext
        if len(raw) <= _NONCE_LEN:
            raise DecryptError("ciphertext is truncated")
        dek = self._kek.unwrap(
            WrappedKey(wrapped_dek=blob.wrapped_dek, kek_version=blob.kek_version)
        )
        aad = aad_for(user_id, credential_id, version)
        try:
            plaintext = AESGCM(dek).decrypt(raw[:_NONCE_LEN], raw[_NONCE_LEN:], aad)
        except InvalidTag as exc:
            raise DecryptError("ciphertext failed authentication") from exc
        finally:
            del dek
        try:
            return plaintext.decode()
        except UnicodeDecodeError as exc:  # pragma: no cover - would require a non-UTF-8 encrypt
            raise DecryptError("plaintext is not valid UTF-8") from exc


__all__ = [
    "DecryptError",
    "EncryptedBlob",
    "EnvelopeCrypto",
    "KekProvider",
    "KeyMaterialError",
    "KmsKek",
    "LocalEnvKek",
    "VaultCryptoError",
    "WrappedKey",
    "aad_for",
    "build_kek_provider",
]
