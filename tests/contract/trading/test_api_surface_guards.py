"""T027/T028 at the API boundary — the OpenAPI surface carries no bypass and no secret.

The library-level guards in ``shared/tests/venues/`` prove the adapter protocol and the
credential wrapper are safe. This file closes the remaining hole: the HTTP surface. A published
parameter is an invitation, so if ``skip_risk`` ever appears as a query parameter or a body
field, a client will eventually send it — and a response schema with an ``api_key`` property is
a leak whether or not today's handler happens to populate it.

Both checks read the composed document rather than the source, so they cover anything FastAPI
generates: path, query, header, and body parameters, and every nested schema.
"""

from __future__ import annotations

import re
from typing import Any

from atlas_api.testing import build_test_app

#: Names that would constitute a way around the gate or the confirmation step.
BYPASS_PATTERNS = (
    "skip_risk",
    "skiprisk",
    "bypass_risk",
    "bypassrisk",
    "ignore_risk",
    "disable_risk",
    "no_risk",
    "risk_override",
    "override_risk",
    "force_submit",
    "force_order",
    "skip_confirmation",
    "bypass_confirmation",
    "skip_kill_switch",
    "ignore_kill_switch",
    "unchecked",
)

#: Property names that would carry credential material. ``*_id`` references are fine — the
#: whole point of the vault is that an id is safe to publish and the material is not.
SECRET_PATTERNS = (
    "password",
    "passphrase",
    "api_key",
    "apikey",
    "secret",
    "private_key",
    "access_token",
    "refresh_token",
    "bearer",
    "signature",
    "authorization",
    "cookie",
    "session_token",
    "credential_payload",
    "credentials",
)

SECRET_ALLOWED = frozenset({"credential_id", "credential_ref"})

TRADING_PREFIXES = ("/v1/trading", "/v1/marketdata")


def _openapi() -> dict[str, Any]:
    return build_test_app().openapi()


def _matches(name: str, patterns: tuple[str, ...]) -> str | None:
    lowered = name.lower()
    normalized = re.sub(r"[^a-z0-9]", "", lowered)
    for pattern in patterns:
        flat = pattern.replace("_", "")
        if pattern in lowered or flat in normalized:
            return pattern
    return None


def _walk_schema(
    schema: Any, spec: dict[str, Any], seen: set[int], out: list[str], trail: str
) -> None:
    """Collect every property name reachable from a schema, following $refs once each."""
    if not isinstance(schema, dict) or id(schema) in seen:
        return
    seen.add(id(schema))

    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        name = ref.rsplit("/", 1)[-1]
        target = spec.get("components", {}).get("schemas", {}).get(name)
        _walk_schema(target, spec, seen, out, f"{trail}->{name}")
        return

    for prop_name, prop_schema in (schema.get("properties") or {}).items():
        out.append(f"{trail}.{prop_name}")
        _walk_schema(prop_schema, spec, seen, out, f"{trail}.{prop_name}")

    for key in ("items", "additionalProperties", "not"):
        _walk_schema(schema.get(key), spec, seen, out, trail)
    for key in ("anyOf", "oneOf", "allOf"):
        for member in schema.get(key) or []:
            _walk_schema(member, spec, seen, out, trail)


def _trading_operations(spec: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    found: list[tuple[str, str, dict[str, Any]]] = []
    for path, methods in spec["paths"].items():
        if not path.startswith(TRADING_PREFIXES):
            continue
        for method, operation in methods.items():
            if isinstance(operation, dict):
                found.append((path, method, operation))
    return found


def _trading_property_paths(spec: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for path, method, operation in _trading_operations(spec):
        trail = f"{method.upper()} {path}"
        body = operation.get("requestBody", {}).get("content", {})
        for media in body.values():
            _walk_schema(media.get("schema"), spec, set(), names, f"{trail} body")
        for status, response in (operation.get("responses") or {}).items():
            for media in (response.get("content") or {}).values():
                _walk_schema(media.get("schema"), spec, set(), names, f"{trail} {status}")
    return names


def test_the_trading_surface_is_actually_published():
    """Guard the guard: an empty surface would make both checks below vacuous."""
    operations = _trading_operations(_openapi())
    assert len(operations) >= 5, f"expected the trading/marketdata surface, found {operations}"


def test_no_endpoint_publishes_a_risk_bypass_parameter():
    spec = _openapi()
    offenders: list[str] = []

    for path, method, operation in _trading_operations(spec):
        for parameter in operation.get("parameters") or []:
            name = parameter.get("name", "")
            if hit := _matches(name, BYPASS_PATTERNS):
                offenders.append(f"{method.upper()} {path} parameter '{name}' matches '{hit}'")

    for property_path in _trading_property_paths(spec):
        leaf = property_path.rsplit(".", 1)[-1]
        if hit := _matches(leaf, BYPASS_PATTERNS):
            offenders.append(f"{property_path} matches '{hit}'")

    assert not offenders, (
        "the API publishes a risk-gate bypass — FR-038 permits no override path:\n  "
        + "\n  ".join(offenders)
    )


def test_no_response_schema_can_carry_credential_material():
    spec = _openapi()
    offenders: list[str] = []

    for property_path in _trading_property_paths(spec):
        leaf = property_path.rsplit(".", 1)[-1]
        if leaf.lower() in SECRET_ALLOWED:
            continue
        if hit := _matches(leaf, SECRET_PATTERNS):
            offenders.append(f"{property_path} matches '{hit}'")

    assert not offenders, (
        "a trading schema can carry credential material — FR-008 keeps it out of every "
        "response:\n  " + "\n  ".join(offenders)
    )


def test_the_matcher_catches_the_names_it_claims_to():
    """Both checks above pass trivially if the matcher is broken."""
    for name in ("skip_risk", "skipRisk", "force-submit", "riskOverride", "unchecked"):
        assert _matches(name, BYPASS_PATTERNS), name
    for name in ("api_key", "apiKey", "X-MBX-APIKEY", "secretKey", "refresh_token"):
        assert _matches(name, SECRET_PATTERNS), name
    for name in ("quantity", "venue_code", "reference_price", "reset_count"):
        assert not _matches(name, BYPASS_PATTERNS), name
        assert not _matches(name, SECRET_PATTERNS), name
