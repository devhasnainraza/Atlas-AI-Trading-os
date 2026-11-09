"""ES256 access-token minting and verification (T008; plan §7, §13).

Design decisions this file encodes:

* **Asymmetric signing.** The API holds the private key; other services verify with the
  public JWKS. A verifier cannot mint tokens, so a compromised read-only service cannot
  forge identity — which is the whole point of ES256 over an HMAC here.
* **kid-based rotation.** Tokens name the key that signed them; the ring keeps the current
  key plus the previous one (2 active) so a 90-day rotation never invalidates an in-flight
  15-minute token. Verification picks the key by ``kid`` from the unverified header.
* **Injected clock.** ``iat``/``exp`` come from a :class:`~atlas_core.timing.Clock`, so a test
  can mint a token and verify it one second before and one second after expiry.
* **Claims are a closed set.** ``sub``, ``sid``, ``roles_ver``, ``mfa`` plus the registered
  ``iss``/``aud``/``iat``/``exp``. ``roles_ver`` lets a role change invalidate cached
  authorization without waiting for the 15-minute token to die; ``sid`` ties the token to a
  revocable session row.

Nothing here touches the database: verifying a signature proves who minted the token, not
that the session still lives. The ``sid`` denylist check is the auth middleware's job (T012).
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import (
    EllipticCurvePrivateKey,
    EllipticCurvePublicKey,
)

from atlas_api.modules.auth.settings import AuthSettings
from atlas_core.timing import Clock, SystemClock

_P256_COORD_BYTES = 32


class TokenError(Exception):
    """Base for every token failure. Callers map these to ATLAS-AUTH-00x codes (T014)."""


class UnknownKeyId(TokenError):
    """The token names a kid not in the ring — a rotated-out key or a foreign issuer."""


class InvalidToken(TokenError):
    """Signature, expiry, audience, or issuer check failed."""


def key_id(public_key: EllipticCurvePublicKey) -> str:
    """Derive the JWKS ``kid`` from the key itself (SHA-256 thumbprint of the DER SPKI).

    A thumbprint rather than a random id or timestamp: the same key always has the same id,
    so a public key file moved between machines keeps matching the tokens it verifies, and a
    verifier that recomputes the id from the key cannot be pointed at the wrong entry.

    This is the single source of the derivation — ``scripts/gen_auth_keys.py`` imports it so
    the filename it writes and the ``kid`` this service emits can never drift apart.
    """
    der = public_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    digest = hashlib.sha256(der).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")[:16]


def _b64url_uint(value: int) -> str:
    return _b64url_raw(value.to_bytes(_P256_COORD_BYTES, "big"))


def _b64url_raw(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def public_jwk(public_key: EllipticCurvePublicKey, kid: str) -> dict[str, str]:
    """The JWKS entry for an ES256 public key."""
    numbers = public_key.public_numbers()
    return {
        "kty": "EC",
        "crv": "P-256",
        "x": _b64url_uint(numbers.x),
        "y": _b64url_uint(numbers.y),
        "kid": kid,
        "use": "sig",
        "alg": "ES256",
    }


@dataclass(frozen=True)
class SigningKey:
    kid: str
    private_key: EllipticCurvePrivateKey

    @property
    def public_key(self) -> EllipticCurvePublicKey:
        return self.private_key.public_key()


@dataclass(frozen=True)
class VerifiedToken:
    """A token whose signature and registered claims have been checked.

    Typed fields rather than a raw dict so a caller cannot silently read a claim that was
    never validated — ``sub`` and ``sid`` are non-optional here and PyJWT was told to require
    them, so their presence is proven, not assumed.
    """

    subject: str
    session_id: str
    roles_version: int
    mfa: bool
    issued_at: datetime
    expires_at: datetime
    kid: str


class KeyRing:
    """The signing key plus every public key still trusted for verification.

    Loaded from disk at construction, not lazily: a missing or malformed key is a startup
    failure, not the first login attempt of the day.
    """

    def __init__(
        self,
        *,
        signing_key: SigningKey | None,
        verifiers: dict[str, EllipticCurvePublicKey],
    ) -> None:
        self._signing_key = signing_key
        self._verifiers = dict(verifiers)
        if signing_key is not None:
            # The signing key's public half must be verifiable by this same ring, or a token
            # we mint could not be checked by us.
            self._verifiers.setdefault(signing_key.kid, signing_key.public_key)

    @classmethod
    def from_settings(cls, settings: AuthSettings, *, allow_ephemeral: bool = False) -> KeyRing:
        """Load the key ring from configured paths.

        ``allow_ephemeral`` mints a throwaway in-memory signing key when no key material is
        configured. It is set only for local/test composition (see ``build_auth_module``): a
        deployed environment has already failed ``validate_for_environment`` before reaching
        here, so an ephemeral key can never sign a production token. Without it, a missing
        key is a startup error rather than a silent downgrade to an unrotatable key.
        """
        verifiers: dict[str, EllipticCurvePublicKey] = {}
        if settings.jwt_public_keys_dir is not None:
            for path in sorted(Path(settings.jwt_public_keys_dir).glob("*.pem")):
                key = serialization.load_pem_public_key(path.read_bytes())
                if not isinstance(key, EllipticCurvePublicKey):
                    raise ValueError(f"{path} is not an EC public key")
                verifiers[key_id(key)] = key

        signing_key: SigningKey | None = None
        if settings.jwt_private_key_path is not None:
            private = serialization.load_pem_private_key(
                Path(settings.jwt_private_key_path).read_bytes(), password=None
            )
            if not isinstance(private, EllipticCurvePrivateKey):
                raise ValueError(f"{settings.jwt_private_key_path} is not an EC private key")
            signing_key = SigningKey(kid=key_id(private.public_key()), private_key=private)

        if signing_key is None and not verifiers:
            if not allow_ephemeral:
                raise ValueError(
                    "no auth key material: set AUTH_JWT_PRIVATE_KEY_PATH and/or "
                    "AUTH_JWT_PUBLIC_KEYS_DIR"
                )
            ephemeral = ec.generate_private_key(ec.SECP256R1())
            signing_key = SigningKey(kid=key_id(ephemeral.public_key()), private_key=ephemeral)
        return cls(signing_key=signing_key, verifiers=verifiers)

    @property
    def can_sign(self) -> bool:
        return self._signing_key is not None

    def jwks(self) -> dict[str, list[dict[str, str]]]:
        return {"keys": [public_jwk(pub, kid) for kid, pub in sorted(self._verifiers.items())]}


class TokenService:
    """Mints and verifies ES256 access tokens."""

    def __init__(
        self,
        *,
        ring: KeyRing,
        settings: AuthSettings,
        clock: Clock | None = None,
    ) -> None:
        self._ring = ring
        self._settings = settings
        self._clock = clock or SystemClock()

    @classmethod
    def from_settings(
        cls, settings: AuthSettings, *, clock: Clock | None = None, allow_ephemeral: bool = False
    ) -> TokenService:
        return cls(
            ring=KeyRing.from_settings(settings, allow_ephemeral=allow_ephemeral),
            settings=settings,
            clock=clock,
        )

    @property
    def ring(self) -> KeyRing:
        """The key ring, exposed read-only so the JWKS route can publish it."""
        return self._ring

    def mint_access_token(
        self,
        *,
        subject: str,
        session_id: str,
        roles_version: int,
        mfa: bool,
    ) -> str:
        if not self._ring.can_sign:
            raise TokenError("this instance has no signing key (verifier-only configuration)")
        assert self._ring._signing_key is not None  # narrowed by can_sign
        signing = self._ring._signing_key
        now = self._clock.now()
        issued_at = int(now.timestamp())
        payload: dict[str, Any] = {
            "sub": subject,
            "sid": session_id,
            "roles_ver": roles_version,
            "mfa": mfa,
            "iat": issued_at,
            "exp": issued_at + self._settings.access_token_ttl_seconds,
            "iss": self._settings.jwt_issuer,
            "aud": self._settings.jwt_audience,
        }
        return jwt.encode(
            payload,
            signing.private_key,
            algorithm="ES256",
            headers={"kid": signing.kid},
        )

    def verify_access_token(self, token: str) -> VerifiedToken:
        """Check signature and registered claims. Raises :class:`InvalidToken`/``UnknownKeyId``.

        Order matters: the ``kid`` is read from the *unverified* header to select a key, but
        nothing derived from the payload is trusted until ``jwt.decode`` has verified the
        signature against that key. An unknown kid fails before any claim is parsed.

        Expiry is checked against the injected clock, not PyJWT's wall clock. Leaving
        ``verify_exp`` on would make the service's time source a lie: a test that freezes the
        clock to mint an expired token would still see it accepted for 15 real minutes, and the
        one property the clock seam exists to prove would be unprovable.
        """
        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise InvalidToken("malformed token") from exc
        kid = header.get("kid")
        if not kid or kid not in self._ring._verifiers:
            raise UnknownKeyId(f"unrecognized signing key: {kid!r}")

        public_key = self._ring._verifiers[kid]
        try:
            claims = jwt.decode(
                token,
                public_key,
                algorithms=["ES256"],
                audience=self._settings.jwt_audience,
                issuer=self._settings.jwt_issuer,
                options={
                    "require": ["exp", "iat", "sub", "aud", "iss"],
                    # Both time checks are disabled here and done against the injected clock
                    # below. PyJWT compares iat/exp to wall time, which would make the clock
                    # seam a lie: a frozen-clock test could not prove expiry behaviour.
                    "verify_exp": False,
                    "verify_iat": False,
                },
            )
        except jwt.InvalidTokenError as exc:
            raise InvalidToken(str(exc)) from exc

        try:
            expires_at = datetime.fromtimestamp(claims["exp"], tz=UTC)
            verified = VerifiedToken(
                subject=str(claims["sub"]),
                session_id=str(claims["sid"]),
                roles_version=int(claims["roles_ver"]),
                mfa=bool(claims["mfa"]),
                issued_at=datetime.fromtimestamp(claims["iat"], tz=UTC),
                expires_at=expires_at,
                kid=kid,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidToken(f"malformed token claims: {exc}") from exc

        if self._clock.now() >= verified.expires_at:
            raise InvalidToken("token has expired")
        return verified


__all__ = [
    "InvalidToken",
    "KeyRing",
    "SigningKey",
    "TokenError",
    "TokenService",
    "UnknownKeyId",
    "VerifiedToken",
    "key_id",
    "public_jwk",
]
