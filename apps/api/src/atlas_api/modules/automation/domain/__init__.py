"""Domain layer exports for Trading Automation."""

from atlas_api.modules.automation.domain.circuit_breaker import CircuitBreakerEvaluator
from atlas_api.modules.automation.domain.models import (
    AutomationMandate,
    AutomationStatus,
    CircuitBreakerEvent,
    PositionGuardState,
)
from atlas_api.modules.automation.domain.smart_stops import (
    calculate_smart_stops,
    evaluate_position_tick,
)

__all__ = [
    "AutomationMandate",
    "AutomationStatus",
    "CircuitBreakerEvent",
    "PositionGuardState",
    "CircuitBreakerEvaluator",
    "calculate_smart_stops",
    "evaluate_position_tick",
]
