"""One-time token machinery for email verification, password reset, magic links (T011).

The shape, and why:

* **Only a SHA-256 hash is stored.** The raw token exists in the email link and in the
  request that consumes it, never in the database. A leaked table therefore leaks no
  usable links — the hash is not a secret and needs no KEK, unlike the vault's DEKs,
  because the token itself is high-entropy random and the hash is one-way.
* **Single-use, enforced by state transition.** Consume flips ``used_at`` atomically with
  the check (the repository's job; the in-memory one here holds a lock). A replayed link
  fails exactly like an expired one — same error, same timing — because telling an
  attacker "that token was already used" is an oracle for valid-but-spent links.
* **Newer issuance invalidates prior same-purpose tokens.** Requesting a second password
  reset kills the first link. Without this, N issued links are N live attack surfaces
  and the user's own newest email is not special.
* **Purpose-bound TTL.** 24 h for email verification (people check mail slowly), 30 min
  for password reset (an attacker with mailbox access gets a short window), 15 min for
  magic links (the link *is* the authentication). The purpose is part of the stored row
  and checked at consume: a password-reset token can never verify an email.

The repository is a Protocol so this service is testable without Postgres; the SQLAlchemy
implementation arrives with the ``verification_token`` table (T022/T024) and the same
contract.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from threading import Lock
from typing import Protocol

from atlas_api.modules.auth.settings import AuthSettings
from atlas_core.timing import Clock, SystemClock


class TokenPurpose(StrEnum):
    """What a one-time token is for. Stored and checked; never inferred from context."""

    EMAIL_VERIFY = "email_verify"
    PASSWORD_RESET = "password_reset"
    MAGIC_LINK = "magic_link"


class OneTimeTokenError(Exception):
    """Consume failed for any reason. Deliberately one error type: expired, used,
    unknown, and wrong-purpose must be indistinguishable to the caller (and through it,
    to the client) so no oracle about token state leaks. Mapping to ATLAS-AUTH-00x
    codes (T014) happens at the route layer, uniformly."""


@dataclass(frozen=True)
class IssuedToken:
    """What the caller gets at issue time: the raw token for the link, plus its id."""

    token_id: str
    raw_token: str
    expires_at: datetime


@dataclass(frozen=True)
class ConsumedToken:
    """What a successful consume proves: who issued it and for what."""

    user_id: str
    purpose: TokenPurpose


@dataclass
class TokenRecord:
    """The stored row. ``token_hash`` is the only token-derived value persisted."""

    token_id: str
    user_id: str
    purpose: TokenPurpose
    token_hash: bytes
    expires_at: datetime
    used_at: datetime | None = None
    invalidated_at: datetime | None = None
    context: dict[str, str] = field(default_factory=dict)


class OneTimeTokenRepository(Protocol):
    """Persistence contract. The Postgres implementation (T024) must make
    ``consume``'s check-and-flip atomic per token row."""

    def insert(self, record: TokenRecord) -> None: ...

    def invalidate_active(self, *, user_id: str, purpose: TokenPurpose, now: datetime) -> int:
        """Flip ``invalidated_at`` on every live token of this purpose for this user.
        Returns the count — the caller logs it, never the client."""
        ...

    def find_by_hash(self, token_hash: bytes) -> TokenRecord | None: ...

    def mark_used(self, *, token_id: str, now: datetime) -> bool:
        """Atomically set ``used_at`` if still live. ``False`` if it wasn't — the
        race-loser path for two simultaneous consumes of one link."""
        ...


class InMemoryTokenRepository:
    """Test/dev repository with the same atomicity rules the Postgres one must honor."""

    def __init__(self) -> None:
        self._by_hash: dict[bytes, TokenRecord] = {}
        self._lock = Lock()

    def insert(self, record: TokenRecord) -> None:
        with self._lock:
            self._by_hash[record.token_hash] = record

    def invalidate_active(self, *, user_id: str, purpose: TokenPurpose, now: datetime) -> int:
        count = 0
        with self._lock:
            for record in self._by_hash.values():
                if (
                    record.user_id == user_id
                    and record.purpose == purpose
                    and record.used_at is None
                    and record.invalidated_at is None
                ):
                    record.invalidated_at = now
                    count += 1
        return count

    def find_by_hash(self, token_hash: bytes) -> TokenRecord | None:
        with self._lock:
            return self._by_hash.get(token_hash)

    def mark_used(self, *, token_id: str, now: datetime) -> bool:
        with self._lock:
            for record in self._by_hash.values():
                if record.token_id == token_id:
                    if record.used_at is not None or record.invalidated_at is not None:
                        return False
                    record.used_at = now
                    return True
            return False


def hash_token(raw: str) -> bytes:
    """SHA-256 of the raw token, as stored and looked up.

    Plain SHA-256 (not Argon2, not HMAC): the input is 256 bits of CSPRNG output, so
    there is no low-entropy guessing to slow down and no secret to key with. The hash
    exists so a table leak is not a link leak; anything stronger buys nothing.
    """
    return hashlib.sha256(raw.encode()).digest()


class OneTimeTokenService:
    """Issue and consume single-use, purpose-scoped, hashed tokens."""

    #: 32 bytes of CSPRNG output, urlsafe-encoded: ~43 characters, 256 bits of entropy.
    _TOKEN_BYTES = 32

    def __init__(
        self,
        *,
        repo: OneTimeTokenRepository,
        settings: AuthSettings,
        clock: Clock | None = None,
    ) -> None:
        self._repo = repo
        self._settings = settings
        self._clock = clock or SystemClock()

    def ttl_for(self, purpose: TokenPurpose) -> timedelta:
        if purpose is TokenPurpose.EMAIL_VERIFY:
            return timedelta(hours=self._settings.email_verify_ttl_hours)
        if purpose is TokenPurpose.PASSWORD_RESET:
            return timedelta(minutes=self._settings.password_reset_ttl_minutes)
        return timedelta(minutes=self._settings.magic_link_ttl_minutes)

    def issue(
        self,
        *,
        user_id: str,
        purpose: TokenPurpose,
        context: dict[str, str] | None = None,
    ) -> IssuedToken:
        """Create a token, invalidating any live token of the same purpose for the user.

        The invalidation happens *before* the insert so the new token is never among the
        rows it invalidates — a same-purpose reissue is "replace", not "add".
        """
        now = self._clock.now()
        self._repo.invalidate_active(user_id=user_id, purpose=purpose, now=now)
        raw = secrets.token_urlsafe(self._TOKEN_BYTES)
        token_id = secrets.token_hex(8)
        record = TokenRecord(
            token_id=token_id,
            user_id=user_id,
            purpose=purpose,
            token_hash=hash_token(raw),
            expires_at=now + self.ttl_for(purpose),
            context=dict(context or {}),
        )
        self._repo.insert(record)
        return IssuedToken(token_id=token_id, raw_token=raw, expires_at=record.expires_at)

    def consume(self, raw: str, *, purpose: TokenPurpose) -> ConsumedToken:
        """Validate and spend a token. Raises :class:`OneTimeTokenError` on any failure.

        The caller supplies the expected purpose — routes know what they are consuming —
        and a token of a different purpose fails identically to an unknown one. Every
        rejection path raises the same exception with the same message, so response
        construction cannot accidentally differentiate them.
        """
        record = self._repo.find_by_hash(hash_token(raw))
        if record is None:
            raise OneTimeTokenError("invalid or expired token")
        now = self._clock.now()
        if record.purpose is not purpose:
            raise OneTimeTokenError("invalid or expired token")
        if record.used_at is not None or record.invalidated_at is not None:
            raise OneTimeTokenError("invalid or expired token")
        if now >= record.expires_at:
            raise OneTimeTokenError("invalid or expired token")
        if not self._repo.mark_used(token_id=record.token_id, now=now):
            # Lost the race against a concurrent consume of the same link.
            raise OneTimeTokenError("invalid or expired token")
        return ConsumedToken(user_id=record.user_id, purpose=record.purpose)


__all__ = [
    "ConsumedToken",
    "InMemoryTokenRepository",
    "IssuedToken",
    "OneTimeTokenError",
    "OneTimeTokenRepository",
    "OneTimeTokenService",
    "TokenPurpose",
    "TokenRecord",
    "hash_token",
]
