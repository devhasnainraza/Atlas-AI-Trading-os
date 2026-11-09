"""Credential vault configuration (T004).

The one rule worth stating twice: ``VAULT_KEK_LOCAL`` is a development affordance and
``validate_for_environment`` **rejects** it outside local/test. A root key sitting in an
environment variable is a root key in every crash dump, process listing, and container
inspect output — which defeats the point of envelope encryption, whose whole purpose is to
keep the KEK in an HSM and out of application memory.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from atlas_core.config import Environment

#: How the key-encryption key is obtained. ``local`` reads a base64 32-byte value from the
#: environment (dev only); the KMS providers wrap and unwrap DEKs without the KEK ever
#: entering this process.
KekProviderName = Literal["local", "aws_kms", "gcp_kms"]


class VaultSettings(BaseSettings):
    """Envelope-encryption parameters and vault operational limits."""

    model_config = SettingsConfigDict(
        env_prefix="VAULT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- Key management --------------------------------------------------------------------
    kek_provider: KekProviderName = "local"

    #: Base64-encoded 32-byte KEK. Local development only.
    kek_local: SecretStr | None = None

    #: KMS key ARN/resource name used to wrap per-credential DEKs.
    kms_key_id: str | None = None

    #: Age at which the KEK is due for rotation. Rotation rewraps wrapped DEKs in the
    #: background; ciphertext is never rewritten, so rotation is cheap and interruptible.
    kek_rotation_days: int = Field(default=180, ge=30, le=730)

    # -- Vault limits ----------------------------------------------------------------------
    #: Credentials one user may hold. A ceiling exists so a compromised account cannot be used
    #: to turn the vault into bulk storage.
    max_credentials_per_user: int = Field(default=50, ge=1, le=500)

    #: Versions retained per credential. Older versions are crypto-shredded, keeping the audit
    #: row and dropping the wrapped DEK.
    max_versions_per_credential: int = Field(default=10, ge=2, le=100)

    #: Require fresh step-up MFA for create/rotate/revoke/delete.
    require_step_up_for_writes: bool = True

    #: Timeout for a provider validation probe ("does this key actually work?").
    validation_timeout_seconds: float = Field(default=10.0, gt=0, le=60)

    #: Trailing characters kept in ``masked_hint`` so a user can tell two keys apart. Four is
    #: the industry norm and carries no useful entropy for an attacker.
    masked_hint_length: int = Field(default=4, ge=0, le=6)

    @model_validator(mode="after")
    def _provider_configured(self) -> VaultSettings:
        """A KMS provider must have the key it wraps with, checked at startup rather than at
        the first credential write — which would be during a user's onboarding.

        Deliberately does *not* require ``kek_local``: an absent local KEK is legitimate in
        tests, where the crypto layer mints an ephemeral one. Making it mandatory here would
        force every test that builds the app to carry vault key material.
        """
        if self.kek_provider != "local" and not self.kms_key_id:
            raise ValueError(
                f"VAULT_KMS_KEY_ID is required when VAULT_KEK_PROVIDER={self.kek_provider}"
            )
        return self

    def validate_for_environment(self, env: Environment) -> None:
        """Refuse the local KEK outside local/test, and require a KMS key there instead.

        In local/test an absent ``kek_local`` is tolerated — the crypto layer generates an
        ephemeral process-lifetime KEK, so stored ciphertext dies with the process. That is the
        right outcome for a test and a visible one for a developer (credentials stored before a
        restart stop decrypting), which is why ``scripts/bootstrap`` writes a stable value.
        """
        if env in (Environment.LOCAL, Environment.TEST):
            return

        if self.kek_provider == "local":
            raise ValueError(
                f"VAULT_KEK_PROVIDER=local is not permitted when ENV={env.value} — "
                "configure aws_kms or gcp_kms; the vault root key must not live in an "
                "environment variable"
            )
        if self.kek_local is not None:
            raise ValueError(
                f"VAULT_KEK_LOCAL must not be set when ENV={env.value} — remove it from the "
                "deployment configuration"
            )
        if not self.kms_key_id:
            raise ValueError(f"VAULT_KMS_KEY_ID is required when ENV={env.value}")


__all__ = ["KekProviderName", "VaultSettings"]
