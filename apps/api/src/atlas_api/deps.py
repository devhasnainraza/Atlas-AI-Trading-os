"""FastAPI dependency providers for the platform runtime."""

from __future__ import annotations

from fastapi import Request

from atlas_api.runtime import PlatformRuntime


def get_runtime(request: Request) -> PlatformRuntime:
    return request.app.state.runtime
