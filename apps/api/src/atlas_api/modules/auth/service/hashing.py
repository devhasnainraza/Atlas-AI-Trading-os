"""Password hashing via Argon2id with versioned parameters (T009; plan §8).

Design decisions:

* **Argon2id** over Argon2i (side-channel resistant) or Argon2d (GPU-resistant). The
  password database is a bulk offline target once breached, so GPU resistance dominates;
  time-domain attacks on the hash itself are not a credible threat model here.
* **Versioned params.** The stored hash encodes its own parameters (:math:`m`, :math:`t`,
  :math:`p`), so next year's migration to a higher memory cost works without a forced
  rehash of every account — a login with the old hash triggers a transparent rehash.
* **Rehash-on-verify.** Every successful verification against a non-current hash silently
  re-hashes the password. A user who logs in once every 90 days gets their hash upgraded
  without noticing. The caller fetches the new hash via ``pop_rehash()`` and persists it;
  the service never touches the database itself.
* **Configurable cost.** The constructor accepts the Argon2 parameters so tests can run
  with cheap costs; production composition uses the module defaults, which are the
  current policy. A hash produced under old parameters is detected by ``needs_rehash``
  regardless of which instance checks it, because the parameters live in the encoded
  string.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from argon2 import PasswordHasher as _Argon2Hasher
from argon2 import Type as Argon2Type
from argon2.exceptions import InvalidHashError as _Argon2InvalidHashError
from argon2.exceptions import VerificationError as _Argon2VerificationError
from argon2.exceptions import VerifyMismatchError as _Argon2MismatchError

#: Current memory cost (64 MiB). Chosen for GPU resistance on a CPU-bound server: this
#: makes a single hash take ~200 ms, which is invisible to the user at login and expensive
#: at bulk-crack scale.
CURRENT_MEMORY_KIB: int = 65536

#: Time cost (iterations). RFC 9106 recommends 3.
CURRENT_TIME_COST: int = 3

#: Parallelism. Past 4 the marginal cost per lane drops below the scheduling overhead.
CURRENT_PARALLELISM: int = 4

#: The Argon2 variant used.
CURRENT_TYPE: Argon2Type = Argon2Type.ID

#: Salt length. 128 bits is enough to make rainbow tables infeasible; longer is wasted.
CURRENT_SALT_LEN: int = 16

#: Hash output length. 256 bits — the output is stored, not truncated.
CURRENT_HASH_LEN: int = 32


class PasswordStrengthError(Exception):
    """Password too weak — rejected by zxcvbn or HIBP (T032)."""


class PasswordHasher(Protocol):
    """Protocol so a test can stub hashing without paying the Argon2 cost."""

    def hash(self, password: str) -> str:
        """Return the encoded hash string."""
        ...

    def verify(self, password: str, encoded: str) -> bool:
        """``True`` if ``password`` matches ``encoded``.

        May mutate internal state: a successful verification against a non-current hash
        records the rehash, which the caller must fetch via ``pop_rehash()``.
        """
        ...

    def needs_rehash(self, encoded: str) -> bool:
        """``True`` if the encoded hash uses outdated parameters."""
        ...

    def pop_rehash(self) -> str | None:
        """A new hash for the last verified password, if it needed rehashing, or ``None``."""
        ...


@dataclass
class Argon2PasswordHasher:
    """Production :class:`PasswordHasher` backed by ``argon2-cffi``.

    Thread-safe for the shared-instance pattern used by module composition:
    ``argon2-cffi`` releases the GIL during hashing and the underlying hasher is
    immutable. The ``_rehash`` slot is per-request state, so routes must not share one
    instance across concurrent requests — composition builds one per app and the login
    service holds it under a request-scoped lock (T026).
    """

    memory_kib: int = CURRENT_MEMORY_KIB
    time_cost: int = CURRENT_TIME_COST
    parallelism: int = CURRENT_PARALLELISM
    hash_len: int = CURRENT_HASH_LEN
    salt_len: int = CURRENT_SALT_LEN
    variant: Argon2Type = CURRENT_TYPE

    _rehash: str | None = field(default=None, init=False, repr=False)
    _impl: _Argon2Hasher = field(default=None, init=False, repr=False)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self._impl = _Argon2Hasher(
            time_cost=self.time_cost,
            memory_cost=self.memory_kib,
            parallelism=self.parallelism,
            hash_len=self.hash_len,
            salt_len=self.salt_len,
            type=self.variant,
        )

    def hash(self, password: str) -> str:
        self._rehash = None
        return self._impl.hash(password)

    def verify(self, password: str, encoded: str) -> bool:
        """Check a password. Malformed or foreign hashes return ``False``, never raise.

        A corrupt hash is a data-integrity problem, not an authentication signal; the
        login flow treats it exactly like a wrong password (enumeration-safe, uniform).
        """
        self._rehash = None
        try:
            self._impl.verify(encoded, password)
        except (_Argon2MismatchError, _Argon2VerificationError, _Argon2InvalidHashError):
            return False
        if self.needs_rehash(encoded):
            self._rehash = self._impl.hash(password)
        return True

    def needs_rehash(self, encoded: str) -> bool:
        try:
            return self._impl.check_needs_rehash(encoded)
        except _Argon2InvalidHashError:
            # Not an Argon2 hash at all: it cannot be upgraded by re-verifying, so it
            # does not "need" a rehash — the caller's verify() already returned False.
            return False

    def pop_rehash(self) -> str | None:
        value = self._rehash
        self._rehash = None
        return value


#: The production instance policy: current parameters, no overrides.
def default_hasher() -> Argon2PasswordHasher:
    return Argon2PasswordHasher()


__all__ = [
    "Argon2PasswordHasher",
    "PasswordHasher",
    "PasswordStrengthError",
    "default_hasher",
]
