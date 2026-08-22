"""Atlas API application factory.

Composes middleware and modules per Spec 00 plan §4: modules declare themselves via
``ModuleDef`` and the factory wires routers (under /v1, or the version a router declares),
event subscriptions, and health probes. Adding a module never edits another module.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atlas_api.middleware.correlation import CorrelationMiddleware
from atlas_api.middleware.errors import register_error_handlers
from atlas_api.middleware.rate_limit import RateLimitMiddleware
from atlas_api.middleware.security_headers import SecurityHeadersMiddleware
from atlas_api.modules.platform.public import build_platform_module
from atlas_api.modules.public import ModuleDef
from atlas_api.modules.sample.public import build_sample_module
from atlas_api.runtime import PlatformRuntime
from atlas_core.config import AtlasSettings, load_settings
from atlas_observability import configure_observability, get_logger

logger = get_logger("atlas_api.main")


def create_app(settings: AtlasSettings | None = None) -> FastAPI:
    settings = settings or load_settings()
    configure_observability(settings.service_name, settings.log_level)

    app = FastAPI(
        title="Atlas AI Trading OS API",
        version="1.0.0",
        description="Unified API layer — platform foundation surface (Spec 00).",
    )
    runtime = PlatformRuntime(settings=settings)
    app.state.runtime = runtime

    # Middleware — outermost added last with BaseHTTPMiddleware ordering.
    app.add_middleware(
        RateLimitMiddleware, requests_per_minute=settings.rate_limit_default_per_minute
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CorrelationMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    # Compose modules — additive only (FR-003).
    for module in (build_platform_module(), build_sample_module()):
        _register_module(app, runtime, module)

    logger.info("app_composed", modules=[m.name for m in runtime.modules.all_modules()])
    return app


def _register_module(app: FastAPI, runtime: PlatformRuntime, module: ModuleDef) -> None:
    runtime.modules.register(module)

    routers = ([module.router] if module.router else []) + list(module.routers_extra)
    for router in routers:
        version = getattr(router, "version", "v1")
        app.include_router(router, prefix=f"/{version}")

    for sub in module.subscriptions:
        runtime.bus.subscribe(
            sub.consumer, sub.event_type, sub.handler, replay_capable=sub.replay_capable
        )

    for name, probe in module.health_probes.items():
        runtime.dependencies.register(name, probe)
