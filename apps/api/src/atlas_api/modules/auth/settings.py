"""Auth module configuration (T004).

Fail-fast at startup: a missing or malformed security value aborts the process naming the
field, rather than degrading into a weaker security posture that nobody notices. Three
conventions matter here:

* **No silent defaults for key material.** ``jwt_private_key_path``, ``email_hash_key``, and
  ``device_cookie_key`` default to ``None``. ``validate_for_environment`` then *requires* them
  outside local/test, so a deployment cannot come up signing tokens with a throwaway key.
  Local development generates them via ``scripts/bootstrap``.
* **Defaults lean strict.** Cookie ``Secure`` on, breach checking on, step-up freshness short.
  A forgotten variable lands on the safe side.
* **Durations are explicit units in the field name** (``_seconds``, ``_minutes``, ``_days``).
  An unlabeled ``ttl`` is how a 15-minute token becomes a 15-hour one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from atlas_core.config import Environment


class AuthSettings(BaseSettings):
    """Tokens, sessions, passwords, MFA, lockout, and anomaly thresholds."""

    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- Token signing ---------------------------------------------------------------------
    #: ``iss`` claim. Verified on every access token, so it must match across services.
    jwt_issuer: str = "https://localhost:8000"

    #: ``aud`` claim. A token minted for another audience is rejected even if the signature is
    #: valid — that is what stops a token issued for a sibling service being replayed here.
    jwt_audience: str = "atlas-api"

    #: PEM-encoded EC P-256 private key. Absent locally until ``scripts/bootstrap`` runs.
    jwt_private_key_path: Path | None = None

    #: Directory of public keys published at ``/.well-known/jwks.json``. Holds the current key
    #: plus the previous one, so tokens minted before a rotation still verify.
    jwt_public_keys_dir: Path | None = None

    #: Access token lifetime. Short because access tokens are not revocable on their own; the
    #: ceiling here is the worst-case revocation lag on non-sensitive routes.
    access_token_ttl_seconds: int = Field(default=900, ge=60, le=3600)

    #: How old a signing key may get before rotation is due. Surfaced as an operational alert.
    signing_key_rotation_days: int = Field(default=90, ge=7, le=365)

    # -- Sessions --------------------------------------------------------------------------
    #: Inactivity window. A refresh token unused for this long is dead.
    refresh_idle_timeout_days: int = Field(default=14, ge=1, le=90)

    #: Hard ceiling regardless of activity — every session eventually requires re-authentication.
    refresh_absolute_lifetime_days: int = Field(default=90, ge=1, le=365)

    #: Concurrent sessions per user; the oldest is evicted past this. Bounds the blast radius
    #: of stolen-token spraying and keeps the session list reviewable by a human.
    max_sessions_per_user: int = Field(default=20, ge=1, le=200)

    #: ``Secure`` attribute on auth cookies. Never turn this off in a deployed environment —
    #: ``validate_for_environment`` refuses.
    cookie_secure: bool = True

    #: ``__Host-`` prefixed cookies must not carry a Domain attribute, so this stays ``None``
    #: for first-party use. Set only for a deliberate cross-subdomain deployment.
    cookie_domain: str | None = None

    # -- Passwords -------------------------------------------------------------------------
    #: Argon2id cost parameters. Stored per-hash so raising them rehashes on next login instead
    #: of invalidating every existing password.
    argon2_memory_kib: int = Field(default=65_536, ge=19_456)
    argon2_time_cost: int = Field(default=3, ge=2)
    argon2_parallelism: int = Field(default=4, ge=1, le=16)

    #: zxcvbn strength floor (0–4). 3 rejects the top password lists and keyboard walks.
    password_min_zxcvbn_score: int = Field(default=3, ge=0, le=4)

    #: How many previous passwords a new one may not match.
    password_history_depth: int = Field(default=5, ge=0, le=24)

    #: Check candidate passwords against the HIBP range API (k-anonymity: only a 5-character
    #: SHA-1 prefix leaves the process).
    breach_check_enabled: bool = True

    #: On HIBP outage, allow the password through on zxcvbn alone rather than blocking sign-up.
    #: Availability wins here because the local check still holds; every skip is logged.
    breach_check_fail_open: bool = True

    # -- Lockout and throttling ------------------------------------------------------------
    #: Failed attempts before backoff engages.
    lockout_free_attempts: int = Field(default=5, ge=1, le=20)

    #: Escalating delays applied after the free attempts are spent, in order. The final value
    #: repeats for further failures — an attacker never gets a shorter wait by trying again.
    lockout_backoff_seconds: tuple[int, ...] = (60, 300, 900, 3600)

    #: Per-IP attempt ceiling, applied before per-account state is touched so that an attacker
    #: cannot lock a victim out cheaply.
    ip_attempt_limit_per_minute: int = Field(default=20, ge=1, le=1000)

    #: Placeholder switch for a CAPTCHA challenge on suspicious attempts. Provider chosen later;
    #: the flag exists so the integration point is designed in, not bolted on.
    captcha_enabled: bool = False

    # -- MFA -------------------------------------------------------------------------------
    #: Label shown in the user's authenticator app.
    totp_issuer_name: str = "Atlas"

    #: Accepted clock skew in 30-second steps either side of now. 1 tolerates real-world drift;
    #: higher widens the replay window.
    totp_window_steps: int = Field(default=1, ge=0, le=2)

    #: Recovery codes issued per batch. Exactly this many, always — the count is asserted.
    recovery_code_count: int = Field(default=10, ge=5, le=20)

    #: How recently MFA must have been proven for a sensitive operation (vault write, role
    #: grant, account deletion, MFA disable) to proceed.
    step_up_freshness_seconds: int = Field(default=300, ge=60, le=1800)

    # -- One-time tokens -------------------------------------------------------------------
    email_verify_ttl_hours: int = Field(default=24, ge=1, le=168)
    password_reset_ttl_minutes: int = Field(default=30, ge=5, le=1440)
    magic_link_ttl_minutes: int = Field(default=15, ge=5, le=60)

    #: Minimum gap between resends of the same email. Stops the platform being used as a mailer.
    resend_cooldown_seconds: int = Field(default=60, ge=10, le=3600)

    # -- Anomaly signals -------------------------------------------------------------------
    #: Implied speed between consecutive logins that marks impossible travel. 900 km/h is
    #: airliner cruise: above it, the same account was in two places at once.
    impossible_travel_kmh: int = Field(default=900, ge=100, le=5000)

    #: MaxMind GeoLite2 City database. Absent means geo signals are skipped, not faked.
    geoip_database_path: Path | None = None

    # -- Keyed hashing ---------------------------------------------------------------------
    #: HMAC key for ``email_hash`` in ``login_failed`` events. Events must be able to correlate
    #: attempts against one address without ever carrying the address (contracts/auth-events.md).
    email_hash_key: SecretStr | None = None

    #: Signing key for the long-lived device-recognition cookie.
    device_cookie_key: SecretStr | None = None

    # -- Privacy ---------------------------------------------------------------------------
    #: Cancelable window between a deletion request and irreversible erasure.
    deletion_grace_days: int = Field(default=14, ge=1, le=90)

    #: Lifetime of the presigned URL for an export bundle.
    export_link_ttl_days: int = Field(default=7, ge=1, le=30)

    @model_validator(mode="after")
    def _coherent_lifetimes(self) -> AuthSettings:
        """Reject configurations whose windows contradict each other."""
        if self.refresh_absolute_lifetime_days < self.refresh_idle_timeout_days:
            raise ValueError(
                "AUTH_REFRESH_ABSOLUTE_LIFETIME_DAYS must be >= AUTH_REFRESH_IDLE_TIMEOUT_DAYS"
            )
        if not self.lockout_backoff_seconds:
            raise ValueError("AUTH_LOCKOUT_BACKOFF_SECONDS must contain at least one delay")
        if list(self.lockout_backoff_seconds) != sorted(self.lockout_backoff_seconds):
            raise ValueError("AUTH_LOCKOUT_BACKOFF_SECONDS must be non-decreasing")
        return self

    def validate_for_environment(self, env: Environment) -> None:
        """Require real key material outside local development.

        Called from the module's composition root. Raises ``ValueError`` naming every missing
        field at once, so an operator fixes one deployment rather than discovering the next
        gap on the following restart.
        """
        if env in (Environment.LOCAL, Environment.TEST):
            return

        missing: list[str] = []
        if self.jwt_private_key_path is None:
            missing.append("AUTH_JWT_PRIVATE_KEY_PATH")
        if self.jwt_public_keys_dir is None:
            missing.append("AUTH_JWT_PUBLIC_KEYS_DIR")
        if self.email_hash_key is None:
            missing.append("AUTH_EMAIL_HASH_KEY")
        if self.device_cookie_key is None:
            missing.append("AUTH_DEVICE_COOKIE_KEY")
        if not self.cookie_secure:
            missing.append("AUTH_COOKIE_SECURE (must be true)")
        if self.jwt_issuer.startswith("http://"):
            missing.append("AUTH_JWT_ISSUER (must be https)")

        if missing:
            raise ValueError(
                f"auth configuration incomplete for env={env.value}: {', '.join(missing)}"
            )


class OAuthSettings(BaseSettings):
    """Social sign-in provider credentials.

    All three providers are optional: with none configured, email/password and magic-link
    sign-in work unchanged and the provider list the UI renders is simply empty. A provider is
    considered configured only when its id *and* secret are both present — half-configured
    means "off", never "try it and fail at the redirect".
    """

    model_config = SettingsConfigDict(
        env_prefix="OAUTH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None

    github_client_id: str | None = None
    github_client_secret: SecretStr | None = None

    #: Apple signs its client secret as a JWT, so it needs the team/key identity, not a static
    #: secret string.
    apple_client_id: str | None = None
    apple_team_id: str | None = None
    apple_key_id: str | None = None
    apple_private_key_path: Path | None = None

    #: Where providers redirect back to. Must exactly match the value registered with each
    #: provider console, including scheme and trailing path.
    redirect_base_url: str = "http://localhost:8000/v1/auth/oauth"

    @property
    def google_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def github_configured(self) -> bool:
        return bool(self.github_client_id and self.github_client_secret)

    @property
    def apple_configured(self) -> bool:
        return bool(
            self.apple_client_id
            and self.apple_team_id
            and self.apple_key_id
            and self.apple_private_key_path
        )

    def configured_providers(self) -> tuple[Literal["google", "github", "apple"], ...]:
        """Providers the sign-in page may offer. Order is stable for predictable UI."""
        providers: list[Literal["google", "github", "apple"]] = []
        if self.google_configured:
            providers.append("google")
        if self.github_configured:
            providers.append("github")
        if self.apple_configured:
            providers.append("apple")
        return tuple(providers)


__all__ = ["AuthSettings", "OAuthSettings"]
