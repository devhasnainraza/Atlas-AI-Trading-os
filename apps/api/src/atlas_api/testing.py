"""Test helpers — build a fully composed app with test-friendly settings."""

from __future__ import annotations

import httpx
from fastapi import FastAPI

from atlas_api.main import create_app
from atlas_core.config import AtlasSettings, Environment


def build_test_settings(**overrides: object) -> AtlasSettings:
    defaults: dict[str, object] = {
        "env": Environment.TEST,
        "service_name": "atlas-api-test",
        "log_level": "WARNING",
    }
    defaults.update(overrides)
    return AtlasSettings(**defaults)  # type: ignore[arg-type]


def build_test_app(**setting_overrides: object) -> FastAPI:
    return create_app(build_test_settings(**setting_overrides))


def make_client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")
