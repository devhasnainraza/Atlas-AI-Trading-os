"""Venue adapter registry (Spec 03 plan §2, T012).

Adapters are constructed per connection, not per venue: each carries its own credential id,
environment, and rate-limit budget. So the registry stores *factories* keyed by venue code and
builds an adapter when a connection needs one.

Registration is explicit — no import-time scanning of a plugin directory. A venue that is not
registered cannot be traded, which is the behaviour we want when a deployment intentionally
omits an adapter.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from atlas_venues.enums import VenueEnvironment
from atlas_venues.errors import UnsupportedCapabilityError
from atlas_venues.models import Capabilities
from atlas_venues.protocol import VenueAdapter


@dataclass(frozen=True, slots=True)
class AdapterContext:
    """Everything an adapter needs to serve one connection.

    ``credential_id`` is a *reference*, never material: the adapter resolves it per operation
    through :mod:`atlas_venues.credentials` (FR-008).
    """

    connection_id: str
    venue_code: str
    environment: VenueEnvironment
    credential_id: str | None = None
    venue_account_ref: str | None = None
    options: Mapping[str, str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.options is None:
            object.__setattr__(self, "options", {})


AdapterFactory = Callable[[AdapterContext], VenueAdapter]


class VenueNotRegisteredError(UnsupportedCapabilityError):
    """No adapter is registered for the requested venue code."""


class VenueRegistry:
    """Maps venue codes to adapter factories and their static capabilities."""

    def __init__(self) -> None:
        self._factories: dict[str, AdapterFactory] = {}
        self._capabilities: dict[str, Capabilities] = {}

    def register(
        self, venue_code: str, factory: AdapterFactory, capabilities: Capabilities
    ) -> None:
        code = venue_code.lower()
        if code in self._factories:
            raise ValueError(f"venue {code} is already registered")
        if capabilities.venue_code.lower() != code:
            raise ValueError(
                f"capabilities declare venue {capabilities.venue_code!r}, registered as {code!r}"
            )
        self._factories[code] = factory
        self._capabilities[code] = capabilities

    def create(self, context: AdapterContext) -> VenueAdapter:
        code = context.venue_code.lower()
        try:
            factory = self._factories[code]
        except KeyError as exc:
            raise VenueNotRegisteredError(
                f"no adapter registered for venue {code!r}", venue_code=code
            ) from exc
        capabilities = self._capabilities[code]
        if context.environment not in capabilities.environments:
            raise UnsupportedCapabilityError(
                f"venue {code} does not support the {context.environment} environment",
                venue_code=code,
            )
        return factory(context)

    build_adapter = create

    def capabilities(self, venue_code: str) -> Capabilities:
        code = venue_code.lower()
        try:
            return self._capabilities[code]
        except KeyError as exc:
            raise VenueNotRegisteredError(
                f"no adapter registered for venue {code!r}", venue_code=code
            ) from exc

    def all_capabilities(self) -> tuple[Capabilities, ...]:
        return tuple(self._capabilities[code] for code in sorted(self._capabilities))

    def is_registered(self, venue_code: str) -> bool:
        return venue_code.lower() in self._factories

    def venue_codes(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))


registry = VenueRegistry()
"""Process-wide registry. Adapter modules register into this at import time of their package."""


__all__ = [
    "AdapterContext",
    "AdapterFactory",
    "VenueNotRegisteredError",
    "VenueRegistry",
    "registry",
]
