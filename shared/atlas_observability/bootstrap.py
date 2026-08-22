"""Observability bootstrap (Spec 00 FR-033/034/037, US3).

One function every entrypoint calls. Provides:
- structlog JSON logging to stdout with timestamp, service, severity, correlation_id
- redaction of secret-shaped values (defense-in-depth; secrets should never reach logs)
- OpenTelemetry wiring is attempted only if the SDK is installed (optional at foundation
  stage; the call is a safe no-op without it)
"""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any, cast

import structlog

from atlas_core.correlation import get_correlation_id

_REDACT_KEY_MARKERS = ("secret", "password", "token", "api_key", "apikey", "credential")
_REDACTED = "[REDACTED]"


def _add_correlation_id(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    event_dict.setdefault("correlation_id", get_correlation_id())
    return event_dict


def _redact_sensitive(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    for key in list(event_dict):
        lowered = key.lower()
        if any(marker in lowered for marker in _REDACT_KEY_MARKERS):
            event_dict[key] = _REDACTED
    return event_dict


def configure_observability(service_name: str, log_level: str = "INFO") -> None:
    """Configure structured logging (and tracing/metrics when the OTel SDK is present)."""
    logging.basicConfig(stream=sys.stdout, level=log_level.upper(), format="%(message)s")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _add_correlation_id,
            _redact_sensitive,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )
    structlog.contextvars.bind_contextvars(service=service_name)

    try:  # OTel is optional at foundation stage — enabled by installing the SDK.
        from opentelemetry import trace  # noqa: F401  # pragma: no cover

        _configure_otel(service_name)  # pragma: no cover
    except ImportError:
        pass


def _configure_otel(service_name: str) -> None:  # pragma: no cover
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    trace.set_tracer_provider(provider)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    logger = structlog.get_logger(name) if name else structlog.get_logger()
    return cast(structlog.stdlib.BoundLogger, logger)
