"""ES256 access-token service (T008).

These tests prove the properties the token format exists to guarantee: a token names its
signing key and verifies only against that key; expiry is enforced against the *injected*
clock (so it is testable, not left to wall time); and every failure mode — tamper, wrong
audience, wrong issuer, unknown kid, expired — is rejected rather than tolerated. A verifier
that accepts a token it should reject is worse than one that crashes.
"""

from __future__ import annotations

from datetime import UTC, datetime

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from atlas_api.modules.auth.service.tokens import (
    InvalidToken,
    KeyRing,
    SigningKey,
    TokenError,
    TokenService,
    UnknownKeyId,
    key_id,
)
from atlas_api.modules.auth.settings import AuthSettings
from atlas_core.timing import FrozenClock

T0 = datetime(2026, 9, 7, 12, 0, 0, tzinfo=UTC)


def _service(**overrides: object) -> TokenService:
    settings = AuthSettings(**overrides)  # type: ignore[arg-type]
    return TokenService.from_settings(settings, clock=FrozenClock(T0), allow_ephemeral=True)


def test_roundtrip_preserves_claims() -> None:
    svc = _service()
    token = svc.mint_access_token(subject="user-1", session_id="sess-1", roles_version=4, mfa=True)
    verified = svc.verify_access_token(token)
    assert verified.subject == "user-1"
    assert verified.session_id == "sess-1"
    assert verified.roles_version == 4
    assert verified.mfa is True


def test_ttl_is_configured_access_token_ttl() -> None:
    svc = _service()
    token = svc.mint_access_token(subject="u", session_id="s", roles_version=1, mfa=False)
    verified = svc.verify_access_token(token)
    assert (verified.expires_at - verified.issued_at).total_seconds() == pytest.approx(
        AuthSettings().access_token_ttl_seconds
    )


def test_token_header_names_the_signing_kid() -> None:
    svc = _service()
    token = svc.mint_access_token(subject="u", session_id="s", roles_version=1, mfa=False)
    header = jwt.get_unverified_header(token)
    assert header["kid"] == svc.ring._signing_key.kid  # type: ignore[union-attr]
    assert header["alg"] == "ES256"


def test_expires_at_injected_clock_boundary() -> None:
    clock = FrozenClock(T0)
    svc = TokenService.from_settings(AuthSettings(), clock=clock, allow_ephemeral=True)
    token = svc.mint_access_token(subject="u", session_id="s", roles_version=1, mfa=False)
    ttl = AuthSettings().access_token_ttl_seconds

    clock.set(T0)
    svc.verify_access_token(token)  # at issue time: valid
    clock.advance(ttl - 1)
    svc.verify_access_token(token)  # one second before expiry: still valid
    clock.advance(2)  # one second past expiry
    with pytest.raises(InvalidToken):
        svc.verify_access_token(token)


def test_tampered_payload_rejected() -> None:
    svc = _service()
    token = svc.mint_access_token(subject="u", session_id="s", roles_version=1, mfa=False)
    with pytest.raises(InvalidToken):
        svc.verify_access_token(token[:-3] + "abc")


def test_unknown_kid_rejected() -> None:
    svc = _service()
    foreign = ec.generate_private_key(ec.SECP256R1())
    settings = AuthSettings()
    forged = jwt.encode(
        {
            "sub": "u",
            "sid": "s",
            "roles_ver": 1,
            "mfa": False,
            "iat": int(T0.timestamp()),
            "exp": int(T0.timestamp()) + 900,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        foreign,
        algorithm="ES256",
        headers={"kid": "not-a-real-kid"},
    )
    with pytest.raises(UnknownKeyId):
        svc.verify_access_token(forged)


def test_wrong_audience_rejected() -> None:
    settings = AuthSettings()
    signing = ec.generate_private_key(ec.SECP256R1())
    ring = KeyRing(
        signing_key=SigningKey(kid=key_id(signing.public_key()), private_key=signing),
        verifiers={},
    )
    svc = TokenService(ring=ring, settings=settings, clock=FrozenClock(T0))
    token = svc.mint_access_token(subject="u", session_id="s", roles_version=1, mfa=False)
    # A service configured for a different audience must reject it.
    other = TokenService(
        ring=ring,
        settings=AuthSettings(jwt_audience="someone-else"),  # type: ignore[arg-type]
        clock=FrozenClock(T0),
    )
    with pytest.raises(InvalidToken):
        other.verify_access_token(token)


def test_key_rotation_verifies_old_token_with_previous_key() -> None:
    """A token minted under key A still verifies after the ring rotates to key B.

    This is the entire reason for kid-based rotation with two active keys: a 90-day rotation
    must not invalidate the 15-minute tokens already in flight.
    """
    settings = AuthSettings()
    key_a = ec.generate_private_key(ec.SECP256R1())
    key_b = ec.generate_private_key(ec.SECP256R1())

    # Mint under A while A is the signing key.
    ring_a = KeyRing(
        signing_key=SigningKey(kid=key_id(key_a.public_key()), private_key=key_a),
        verifiers={},
    )
    token = TokenService(ring=ring_a, settings=settings, clock=FrozenClock(T0)).mint_access_token(
        subject="u", session_id="s", roles_version=1, mfa=False
    )

    # Rotate: B signs, but A's public key stays in the verifier set.
    ring_b = KeyRing(
        signing_key=SigningKey(kid=key_id(key_b.public_key()), private_key=key_b),
        verifiers={key_id(key_a.public_key()): key_a.public_key()},
    )
    svc_b = TokenService(ring=ring_b, settings=settings, clock=FrozenClock(T0))
    verified = svc_b.verify_access_token(token)
    assert verified.subject == "u"
    assert verified.kid == key_id(key_a.public_key())


def test_verifier_only_instance_cannot_mint() -> None:
    settings = AuthSettings()
    key = ec.generate_private_key(ec.SECP256R1())
    ring = KeyRing(signing_key=None, verifiers={key_id(key.public_key()): key.public_key()})
    svc = TokenService(ring=ring, settings=settings, clock=FrozenClock(T0))
    assert not svc.ring.can_sign
    with pytest.raises(TokenError):
        svc.mint_access_token(subject="u", session_id="s", roles_version=1, mfa=False)
