"""Configuration loading with fail-fast validation (Spec 00 FR-005/006/007).

Every service composes ``AtlasSettings`` (or a subclass) and calls ``load_settings()`` at
startup. Missing or invalid required values abort the process with an error naming the
offending field — services never run half-configured. Secrets come from the environment;
no defaults exist for security-relevant fields.
"""

from __future__ import annotations

import sys
from enum import StrEnum

from pydantic import ValidationError as PydanticValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class AtlasSettings(BaseSettings):
    """Base settings shared by every Atlas service."""

    model_config = SettingsConfigDict(
        env_prefix="ATLAS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Environment = Environment.LOCAL
    service_name: str = "atlas-api"
    log_level: str = "INFO"

    # Dependency endpoints — required in deployed environments, optional locally so the
    # API can boot for pure in-memory development/tests.
    database_url: str | None = None
    redis_url: str | None = None
    kafka_bootstrap_servers: str | None = None

    # HTTP surface
    cors_allowed_origins: list[str] = ["http://localhost:3000"]
    rate_limit_default_per_minute: int = 120

    @property
    def is_production(self) -> bool:
        return self.env == Environment.PRODUCTION

    def validate_for_environment(self) -> None:
        """Environment-specific invariants beyond field types (fail-fast)."""
        if self.env in (Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION):
            missing = [
                name
                for name, value in (
                    ("ATLAS_DATABASE_URL", self.database_url),
                    ("ATLAS_REDIS_URL", self.redis_url),
                    ("ATLAS_KAFKA_BOOTSTRAP_SERVERS", self.kafka_bootstrap_servers),
                )
                if not value
            ]
            if missing:
                raise ValueError(f"Environment '{self.env}' requires: {', '.join(missing)}")
        if self.env == Environment.TEST and self.database_url and "prod" in self.database_url:
            raise ValueError("Refusing ENV=test with a production-looking ATLAS_DATABASE_URL")


def load_settings(cls: type[AtlasSettings] = AtlasSettings, **overrides: object) -> AtlasSettings:
    """Load and validate settings; exit non-zero naming the bad field on failure."""
    try:
        settings = cls(**overrides)  # type: ignore[arg-type]
        settings.validate_for_environment()
        return settings
    except PydanticValidationError as exc:
        fields = ", ".join(str(e["loc"][0]) for e in exc.errors())
        print(f"FATAL: invalid configuration — field(s): {fields}", file=sys.stderr)
        raise SystemExit(1) from exc
    except ValueError as exc:
        print(f"FATAL: invalid configuration — {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
