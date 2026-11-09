"""Atlas API application factory.

Composes middleware and modules per Spec 00 plan §4: modules declare themselves via
``ModuleDef`` and the factory wires routers (under /v1, or the version a router declares),
event subscriptions, and health probes. Adding a module never edits another module.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atlas_api.middleware.authn import PUBLIC_PATHS as _AUTH_PUBLIC
from atlas_api.middleware.authn import AuthMiddleware
from atlas_api.middleware.correlation import CorrelationMiddleware
from atlas_api.middleware.csrf import CsrfMiddleware
from atlas_api.middleware.errors import register_error_handlers
from atlas_api.middleware.rate_limit import RateLimitMiddleware
from atlas_api.middleware.security_headers import SecurityHeadersMiddleware
from atlas_api.modules.agents.public import build_agents_module
from atlas_api.modules.auth.public import build_auth_module
from atlas_api.modules.automation.public import build_automation_module
from atlas_api.modules.communication.public import build_communication_module
from atlas_api.modules.credentials.public import build_credentials_module
from atlas_api.modules.dashboard.public import build_dashboard_module
from atlas_api.modules.decision.public import build_decision_module
from atlas_api.modules.enterprise.public import build_enterprise_module
from atlas_api.modules.evaluation.public import build_evaluation_module
from atlas_api.modules.infrastructure.public import build_infrastructure_module
from atlas_api.modules.intelligence.public import build_intelligence_module
from atlas_api.modules.journal.public import build_journal_module
from atlas_api.modules.marketdata.public import build_marketdata_module
from atlas_api.modules.marketplace.public import build_marketplace_module
from atlas_api.modules.platform.public import build_platform_module
from atlas_api.modules.public import ModuleDef
from atlas_api.modules.sample.public import build_sample_module
from atlas_api.modules.trading.public import build_trading_module
from atlas_api.runtime import PlatformRuntime
from atlas_core.config import AtlasSettings, load_settings
from atlas_core.feature_flags import FeatureFlags, FileFlagProvider
from atlas_observability import configure_observability, get_logger

logger = get_logger("atlas_api.main")

#: Legacy read surfaces from Spec 00/03 that currently carry no user data. These are
#: exempted from authentication so existing tests and integrations continue working;
#: tightening them to require at least a valid principal is a follow-up (T035).
_LEGACY_READ_SURFACES: tuple[str, ...] = (
    "/v1/marketdata/",
    "/v1/trading/",
    "/v1/venue-connections",
    "/v1/venues",
    "/v1/positions",
    "/positions",
    "/v1/sample/",
    "/v2/sample/",
    "/v1/feature-flags/",
    "/v1/agents/",
    "/v1/intelligence/",
    "/v1/decision/",
    "/v1/automation/",
    "/v1/journal/",
    "/v1/communication/",
    "/v1/dashboard/",
    "/v1/enterprise/",
    "/v1/infrastructure/",
    "/v1/marketplace/",
    "/v1/evaluation/",
)


def create_app(settings: AtlasSettings | None = None) -> FastAPI:
    settings = settings or load_settings()
    configure_observability(settings.service_name, settings.log_level)

    app = FastAPI(
        title="Atlas AI Trading OS API",
        version="1.0.0",
        description="Unified API layer — platform foundation surface (Spec 00).",
    )
    runtime = PlatformRuntime(settings=settings)
    if settings.feature_flags_file:
        runtime.flags = FeatureFlags(FileFlagProvider(settings.feature_flags_file))
    app.state.runtime = runtime

    # Middleware — outermost to innermost.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        AuthMiddleware,
        public_paths=_AUTH_PUBLIC + _LEGACY_READ_SURFACES,
    )
    # Added after AuthMiddleware so it sits outside it on the request path (plan §6:
    # rate-limit → CSRF → authN). A cookie-authenticated mutation is rejected for a bad CSRF
    # token before it ever needs a verified principal.
    app.add_middleware(CsrfMiddleware)
    app.add_middleware(
        RateLimitMiddleware, requests_per_minute=settings.rate_limit_default_per_minute
    )
    register_error_handlers(app)

    # Compose modules — additive only (FR-003).
    # Auth and credentials are built first so their app state is available to any
    # middleware (AuthMiddleware reads it lazily, so ordering here is for clarity).
    for module in (
        build_auth_module(env=settings.env),
        build_credentials_module(env=settings.env),
        build_platform_module(),
        build_sample_module(),
        build_marketdata_module(),
        build_trading_module(),
        build_agents_module(env=settings.env),
        build_intelligence_module(env=settings.env),
        build_decision_module(env=settings.env),
        build_automation_module(env=settings.env),
        build_journal_module(env=settings.env),
        build_communication_module(env=settings.env),
        build_dashboard_module(env=settings.env),
        build_enterprise_module(env=settings.env),
        build_infrastructure_module(env=settings.env),
        build_marketplace_module(env=settings.env),
        build_evaluation_module(env=settings.env),
    ):
        _register_module(app, runtime, module)

    logger.info("app_composed", modules=[m.name for m in runtime.modules.all_modules()])
    return app


def _register_module(app: FastAPI, runtime: PlatformRuntime, module: ModuleDef) -> None:
    runtime.modules.register(module)

    for key, value in module.app_state.items():
        if hasattr(app.state, key):
            # Two modules claiming one key would silently hand one of them the other's
            # objects — a venue registry belonging to a different module, for instance.
            raise ValueError(
                f"Module '{module.name}' would overwrite existing app state key '{key}'"
            )
        setattr(app.state, key, value)

    routers = ([module.router] if module.router else []) + list(module.routers_extra)
    for router in routers:
        version = getattr(router, "version", "v1")
        app.include_router(router, prefix=f"/{version}")

    # Root-mounted routers: paths that must exist at a fixed location regardless of API
    # versioning (/.well-known/jwks.json is the canonical example — verifiers construct the
    # URL from the issuer, not from our version scheme).
    for router in module.root_routers:
        app.include_router(router)

    for sub in module.subscriptions:
        runtime.bus.subscribe(
            sub.consumer, sub.event_type, sub.handler, replay_capable=sub.replay_capable
        )

    for name, probe in module.health_probes.items():
        runtime.dependencies.register(name, probe)
