"""Argon2id password hashing (T009).

The properties these tests pin down are the ones the login flow depends on: a correct
password verifies and a wrong one does not; the encoded hash carries its own parameters
so an outdated hash is *detected* and transparently upgraded on the next successful
login; and a corrupt or foreign hash fails like a wrong password rather than raising —
the login path must not be able to distinguish "broken data" from "bad credentials",
or it leaks an enumeration signal.

Tests run with cheap parameters (1 MiB, t=1) so the suite stays fast; production
composition uses the module defaults.
"""

from __future__ import annotations

from argon2 import Type as Argon2Type

from atlas_api.modules.auth.service.hashing import (
    CURRENT_MEMORY_KIB,
    CURRENT_TIME_COST,
    Argon2PasswordHasher,
    default_hasher,
)

# Cheap-but-valid policy for tests only.
FAST: dict[str, object] = {"memory_kib": 1024, "time_cost": 1, "parallelism": 1}


def _fast_hasher(**overrides: object) -> Argon2PasswordHasher:
    return Argon2PasswordHasher(**{**FAST, **overrides})  # type: ignore[arg-type]


def test_correct_password_verifies_wrong_one_does_not() -> None:
    hasher = _fast_hasher()
    encoded = hasher.hash("correc7-horse-battery")
    assert hasher.verify("correc7-horse-battery", encoded) is True
    assert hasher.verify("wrong-password", encoded) is False


def test_hash_encodes_argon2id_and_current_policy() -> None:
    hasher = default_hasher()
    # One real hash at production cost proves the defaults are wired through; the
    # encoded string is self-describing, so this is the contract the rehash check reads.
    encoded = hasher.hash("x")
    assert encoded.startswith("$argon2id$")
    assert f"m={CURRENT_MEMORY_KIB},t={CURRENT_TIME_COST}" in encoded


def test_same_password_hashes_differ() -> None:
    """A random salt per hash: two users with the same password store different hashes."""
    hasher = _fast_hasher()
    assert hasher.hash("same") != hasher.hash("same")


def test_outdated_hash_is_flagged_and_upgraded_on_verify() -> None:
    old = _fast_hasher(memory_kib=2048)  # a hash made under yesterday's policy
    encoded = old.hash("passw0rd!")

    current = _fast_hasher()
    assert current.needs_rehash(encoded) is True

    assert current.verify("passw0rd!", encoded) is True
    upgraded = current.pop_rehash()
    assert upgraded is not None
    assert upgraded != encoded
    assert current.needs_rehash(upgraded) is False
    # The upgraded hash verifies the same password — the user never notices.
    assert current.verify("passw0rd!", upgraded) is True


def test_verify_of_current_hash_records_no_rehash() -> None:
    hasher = _fast_hasher()
    encoded = hasher.hash("passw0rd!")
    assert hasher.verify("passw0rd!", encoded) is True
    assert hasher.pop_rehash() is None


def test_failed_verify_clears_pending_rehash() -> None:
    """State hygiene: a rehash from an earlier verify must not leak into a later call.

    If it did, the login service could persist a hash computed for a *different*
    user's password — a silent credential-corruption bug.
    """
    old = _fast_hasher(memory_kib=2048)
    encoded = old.hash("passw0rd!")

    current = _fast_hasher()
    assert current.verify("passw0rd!", encoded) is True  # queues a rehash
    assert current.verify("wrong", encoded) is False  # must clear it
    assert current.pop_rehash() is None


def test_pop_rehash_is_single_use() -> None:
    old = _fast_hasher(memory_kib=2048)
    encoded = old.hash("passw0rd!")
    current = _fast_hasher()
    current.verify("passw0rd!", encoded)
    assert current.pop_rehash() is not None
    assert current.pop_rehash() is None


def test_corrupt_and_foreign_hashes_fail_like_wrong_password() -> None:
    """Never raise on bad hash data — the caller cannot distinguish it from a mismatch."""
    hasher = _fast_hasher()
    for junk in ("", "not-a-hash", "$argon2i$m=65536,t=3,p=4$broken", "$2b$12$bcrypt"):
        assert hasher.verify("anything", junk) is False
        assert hasher.pop_rehash() is None


def test_variant_change_triggers_rehash() -> None:
    """A future move from Argon2id to another variant is detected the same way."""
    id_hasher = _fast_hasher()
    encoded = id_hasher.hash("passw0rd!")

    other = _fast_hasher(variant=Argon2Type.I)
    assert other.needs_rehash(encoded) is True
    assert other.verify("passw0rd!", encoded) is True
    assert other.pop_rehash() is not None
