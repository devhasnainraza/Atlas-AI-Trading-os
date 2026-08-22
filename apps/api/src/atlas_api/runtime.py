"""Platform runtime — the composed set of shared services the app factory injects.

Modules receive these via FastAPI dependencies (see deps.py); nothing here is a global
singleton, which keeps every layer swappable in tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from atlas_api.modules.public import ModuleRegistry
from atlas_core.audit import AuditLogRepository, InMemoryAuditLog
from atlas_core.config import AtlasSettings
from atlas_core.dependencies import DependencyRegistry
from atlas_core.feature_flags import FeatureFlags, StaticFlagProvider
from atlas_events import InMemoryEventBus, InMemoryOutbox, InMemoryProcessedLedger, catalog


@dataclass
class PlatformRuntime:
    settings: AtlasSettings
    bus: InMemoryEventBus = field(default_factory=lambda: InMemoryEventBus(catalog))
    outbox: InMemoryOutbox = field(default_factory=InMemoryOutbox)
    ledger: InMemoryProcessedLedger = field(default_factory=InMemoryProcessedLedger)
    modules: ModuleRegistry = field(default_factory=ModuleRegistry)
    dependencies: DependencyRegistry = field(default_factory=DependencyRegistry)
    audit_log: AuditLogRepository = field(default_factory=InMemoryAuditLog)
    flags: FeatureFlags = field(default_factory=lambda: FeatureFlags(StaticFlagProvider()))
