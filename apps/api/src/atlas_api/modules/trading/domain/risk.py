"""The pre-trade risk gate (Spec 03 plan §7, US5, FR-032..FR-043).

Constitution VI — Risk Before Profit — is enforced here, and the enforcement is structural:

* :func:`evaluate` is the **only** way to obtain a :class:`RiskVerdict`. The class refuses
  direct construction, so a caller cannot forge an approval (T100).
* There is no bypass parameter, and the guard test in
  ``shared/tests/venues/test_no_risk_bypass.py`` fails the build if one appears (FR-038, T027).
* Missing or stale inputs produce ``REJECT``, never a pass. An unmeasurable risk is not an
  absent risk (FR-039).
* Every verdict records the rules it evaluated and the state of its inputs, so an operator can
  see *why* — Constitution V, Explainability.

The verdict is hashed. The confirmation endpoint requires the hash back, which is what stops a
user from approving one order and transmitting a different one (FR-025).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from atlas_venues.enums import AssetClass, DataFreshness, OrderSide, OrderType, VenueEnvironment
from atlas_venues.precision import ZERO, notional

_CONSTRUCTION_TOKEN = object()


class RiskDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUIRE_CONFIRMATION = "require_confirmation"
    """Approved, but the user must confirm despite holding an automation mandate (FR-041)."""


class RiskRuleCode(StrEnum):
    """Every rule the gate can cite. The set is closed so a verdict is always explainable."""

    KILL_SWITCH_ENGAGED = "kill_switch_engaged"
    CONNECTION_UNHEALTHY = "connection_unhealthy"
    ENVIRONMENT_MISMATCH = "environment_mismatch"
    LIVE_TRADING_DISABLED = "live_trading_disabled"
    MARKET_DATA_STALE = "market_data_stale"
    ACCOUNT_STATE_UNKNOWN = "account_state_unknown"
    INSTRUMENT_NOT_TRADABLE = "instrument_not_tradable"
    ORDER_TYPE_UNSUPPORTED = "order_type_unsupported"
    QUANTITY_OUT_OF_BOUNDS = "quantity_out_of_bounds"
    NOTIONAL_LIMIT_EXCEEDED = "notional_limit_exceeded"
    MAX_POSITION_SIZE_EXCEEDED = "max_position_size_exceeded"
    MAX_OPEN_POSITIONS_EXCEEDED = "max_open_positions_exceeded"
    MAX_ORDERS_PER_WINDOW_EXCEEDED = "max_orders_per_window_exceeded"
    DAILY_LOSS_LIMIT_BREACHED = "daily_loss_limit_breached"
    DRAWDOWN_LIMIT_BREACHED = "drawdown_limit_breached"
    INSUFFICIENT_MARGIN = "insufficient_margin"
    MARGIN_LEVEL_TOO_LOW = "margin_level_too_low"
    SYMBOL_NOT_PERMITTED = "symbol_not_permitted"
    SHORT_SELLING_NOT_PERMITTED = "short_selling_not_permitted"
    PRICE_FAR_FROM_MARKET = "price_far_from_market"
    MANDATE_REQUIRED = "mandate_required"
    MANDATE_LIMIT_EXCEEDED = "mandate_limit_exceeded"


class InputState(StrEnum):
    PRESENT = "present"
    STALE = "stale"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    """The limits a user or operator set. ``None`` means "no limit configured for this rule".

    A ``None`` limit is not the same as a limit of zero: the former skips the rule, the latter
    rejects everything. Both are legitimate; conflating them is not.
    """

    policy_id: str
    max_order_notional: Decimal | None = None
    max_position_notional: Decimal | None = None
    max_open_positions: int | None = None
    max_orders_per_hour: int | None = None
    daily_loss_limit: Decimal | None = None
    max_drawdown_percent: Decimal | None = None
    min_margin_level_percent: Decimal | None = None
    allowed_symbols: frozenset[str] | None = None
    blocked_symbols: frozenset[str] = frozenset()
    allow_short_selling: bool = True
    max_price_deviation_percent: Decimal | None = None
    require_confirmation_always: bool = False

    def __post_init__(self) -> None:
        for name in (
            "max_order_notional",
            "max_position_notional",
            "daily_loss_limit",
            "max_drawdown_percent",
            "min_margin_level_percent",
            "max_price_deviation_percent",
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, Decimal):
                raise TypeError(f"RiskPolicy.{name} must be Decimal or None")
            if value is not None and value < ZERO:
                raise ValueError(f"RiskPolicy.{name} must not be negative")


@dataclass(frozen=True, slots=True)
class OrderIntentView:
    """The order being evaluated, as the gate sees it."""

    intent_id: str
    venue_code: str
    venue_account_ref: str
    venue_symbol: str
    canonical_symbol: str
    asset_class: AssetClass
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    environment: VenueEnvironment
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    reduce_only: bool = False


@dataclass(frozen=True, slots=True)
class RiskContext:
    """Everything the gate needs that is not part of the order itself.

    Optional fields are genuinely optional *inputs*, not optional *checks*: when a field the
    policy depends on is absent, the gate rejects rather than skipping the rule (FR-039). The
    ``*_state`` fields say which situation applies.
    """

    evaluated_at: datetime
    policy: RiskPolicy
    kill_switch_engaged: bool = False
    kill_switch_scope: str | None = None
    live_trading_enabled: bool = True
    connection_can_trade: bool = True
    connection_environment: VenueEnvironment | None = None
    instrument_is_tradable: bool = True
    supported_order_types: frozenset[OrderType] = frozenset()
    supports_short_selling: bool = True
    min_quantity: Decimal | None = None
    max_quantity: Decimal | None = None

    reference_price: Decimal | None = None
    quote_freshness: DataFreshness | None = None
    quote_age_seconds: float | None = None

    account_equity: Decimal | None = None
    available_margin: Decimal | None = None
    margin_level_percent: Decimal | None = None
    account_state_is_current: bool = True

    existing_position_notional: Decimal = ZERO
    open_position_count: int = 0
    orders_in_last_hour: int = 0
    realized_pnl_today: Decimal = ZERO
    peak_equity: Decimal | None = None

    contract_size: Decimal | None = None
    mandate_active: bool = False
    mandate_remaining_notional: Decimal | None = None


@dataclass(frozen=True, slots=True)
class RuleResult:
    """One rule's outcome, kept whether it passed or failed — the audit needs both."""

    code: RiskRuleCode
    passed: bool
    detail: str
    limit: str | None = None
    observed: str | None = None


@dataclass(frozen=True)
class RiskVerdict:
    """An immutable, hashed decision produced only by :func:`evaluate`.

    Direct construction raises. This is the mechanism behind FR-038: code that wants an
    approval must actually run the gate, because there is no other way to get one of these.
    """

    intent_id: str
    decision: RiskDecision
    evaluated_at: datetime
    rules_evaluated: tuple[RuleResult, ...]
    inputs_state: Mapping[str, InputState]
    policy_id: str
    reasons: tuple[str, ...] = ()
    _token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _CONSTRUCTION_TOKEN:
            raise TypeError(
                "RiskVerdict cannot be constructed directly; call "
                "atlas_api.modules.trading.domain.risk.evaluate()"
            )

    @property
    def approved(self) -> bool:
        return self.decision is not RiskDecision.REJECT

    @property
    def requires_confirmation(self) -> bool:
        return self.decision is RiskDecision.REQUIRE_CONFIRMATION

    @property
    def failed_rules(self) -> tuple[RuleResult, ...]:
        return tuple(r for r in self.rules_evaluated if not r.passed)

    def hash(self) -> str:
        """A stable fingerprint of this decision and the terms it approved.

        The confirm endpoint requires this value back. If anything about the intent or the
        verdict changed in between, the hash will not match and the confirmation is refused
        with 409 rather than transmitting terms the user never saw (FR-025).
        """
        payload = {
            "intent_id": self.intent_id,
            "decision": str(self.decision),
            "policy_id": self.policy_id,
            "evaluated_at": self.evaluated_at.isoformat(),
            "rules": [
                {"code": str(r.code), "passed": r.passed, "limit": r.limit, "observed": r.observed}
                for r in self.rules_evaluated
            ],
            "inputs": {k: str(v) for k, v in sorted(self.inputs_state.items())},
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def explain(self) -> str:
        """A human-readable account of the decision (Constitution V)."""
        if self.decision is RiskDecision.REJECT:
            head = "Rejected by the pre-trade risk gate."
        elif self.decision is RiskDecision.REQUIRE_CONFIRMATION:
            head = "Approved, but requires your explicit confirmation."
        else:
            head = "Approved by the pre-trade risk gate."
        lines = [head]
        for rule in self.failed_rules:
            suffix = ""
            if rule.limit is not None and rule.observed is not None:
                suffix = f" (limit {rule.limit}, observed {rule.observed})"
            lines.append(f"  - {rule.code}: {rule.detail}{suffix}")
        checked = len(self.rules_evaluated)
        lines.append(f"  {checked} rule(s) evaluated against policy {self.policy_id}.")
        return "\n".join(lines)


def evaluate(intent: OrderIntentView, context: RiskContext) -> RiskVerdict:
    """Run every applicable rule and return a verdict. The only path to a ``RiskVerdict``.

    Rules are evaluated in escalating order of cost, but *all* of them run: the verdict records
    every rule so an operator sees the full picture, not just the first failure.
    """
    rules: list[RuleResult] = []
    inputs: dict[str, InputState] = {}

    _check_stops(intent, context, rules)
    _check_venue_and_instrument(intent, context, rules)
    _check_data_freshness(intent, context, rules, inputs)
    _check_account_state(context, rules, inputs)
    _check_quantity_bounds(intent, context, rules)
    reference = _reference_price(intent, context)
    _check_notional_limits(intent, context, rules, inputs, reference)
    _check_position_limits(intent, context, rules, inputs, reference)
    _check_activity_limits(context, rules)
    _check_loss_limits(context, rules, inputs)
    _check_margin(context, rules, inputs, reference, intent)
    _check_symbol_permissions(intent, context, rules)
    _check_price_sanity(intent, context, rules, reference)
    _check_mandate(intent, context, rules, reference)

    failed = [r for r in rules if not r.passed]
    if failed:
        decision = RiskDecision.REJECT
        reasons = tuple(f"{r.code}: {r.detail}" for r in failed)
    elif context.policy.require_confirmation_always or not context.mandate_active:
        decision = RiskDecision.REQUIRE_CONFIRMATION
        reasons = ("explicit human confirmation required before transmission",)
    else:
        decision = RiskDecision.APPROVE
        reasons = ()

    return RiskVerdict(
        intent_id=intent.intent_id,
        decision=decision,
        evaluated_at=context.evaluated_at,
        rules_evaluated=tuple(rules),
        inputs_state=dict(inputs),
        policy_id=context.policy.policy_id,
        reasons=reasons,
        _token=_CONSTRUCTION_TOKEN,
    )


# --------------------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------------------


def _check_stops(intent: OrderIntentView, ctx: RiskContext, rules: list[RuleResult]) -> None:
    """The kill switch outranks everything, including a valid mandate (FR-043)."""
    rules.append(
        RuleResult(
            code=RiskRuleCode.KILL_SWITCH_ENGAGED,
            passed=not ctx.kill_switch_engaged,
            detail=(
                f"a kill switch is engaged ({ctx.kill_switch_scope or 'global'}); "
                "no new orders may be transmitted"
                if ctx.kill_switch_engaged
                else "no kill switch is engaged"
            ),
        )
    )
    live_ok = intent.environment is not VenueEnvironment.LIVE or ctx.live_trading_enabled
    rules.append(
        RuleResult(
            code=RiskRuleCode.LIVE_TRADING_DISABLED,
            passed=live_ok,
            detail=(
                "live order transmission is disabled by feature flag"
                if not live_ok
                else "live transmission is permitted for this environment"
            ),
        )
    )


def _check_venue_and_instrument(
    intent: OrderIntentView, ctx: RiskContext, rules: list[RuleResult]
) -> None:
    rules.append(
        RuleResult(
            code=RiskRuleCode.CONNECTION_UNHEALTHY,
            passed=ctx.connection_can_trade,
            detail=(
                "the venue connection is not healthy"
                if not ctx.connection_can_trade
                else "the venue connection is healthy"
            ),
        )
    )
    env_ok = ctx.connection_environment is None or ctx.connection_environment is intent.environment
    rules.append(
        RuleResult(
            code=RiskRuleCode.ENVIRONMENT_MISMATCH,
            passed=env_ok,
            detail=(
                f"intent is {intent.environment} but the connection is {ctx.connection_environment}"
                if not env_ok
                else f"intent and connection agree on {intent.environment}"
            ),
        )
    )
    rules.append(
        RuleResult(
            code=RiskRuleCode.INSTRUMENT_NOT_TRADABLE,
            passed=ctx.instrument_is_tradable,
            detail=(
                f"{intent.canonical_symbol} is not currently tradable at this venue"
                if not ctx.instrument_is_tradable
                else f"{intent.canonical_symbol} is tradable"
            ),
        )
    )
    if ctx.supported_order_types:
        supported = intent.order_type in ctx.supported_order_types
        rules.append(
            RuleResult(
                code=RiskRuleCode.ORDER_TYPE_UNSUPPORTED,
                passed=supported,
                detail=(
                    f"the venue does not support {intent.order_type} orders"
                    if not supported
                    else f"{intent.order_type} is supported"
                ),
            )
        )


def _check_data_freshness(
    intent: OrderIntentView,
    ctx: RiskContext,
    rules: list[RuleResult],
    inputs: dict[str, InputState],
) -> None:
    """A market order without a fresh price is refused — FR-039, not a warning."""
    needs_price = intent.order_type is OrderType.MARKET or _needs_reference_price(ctx)
    if ctx.quote_freshness is None:
        inputs["quote"] = InputState.MISSING
        if needs_price:
            rules.append(
                RuleResult(
                    code=RiskRuleCode.MARKET_DATA_STALE,
                    passed=False,
                    detail="no market data is available for this instrument",
                    observed="missing",
                )
            )
        return
    fresh = ctx.quote_freshness is DataFreshness.FRESH
    inputs["quote"] = InputState.PRESENT if fresh else InputState.STALE
    if needs_price:
        rules.append(
            RuleResult(
                code=RiskRuleCode.MARKET_DATA_STALE,
                passed=fresh,
                detail=(
                    "market data is stale; risk cannot be measured against a price we do not trust"
                    if not fresh
                    else "market data is fresh"
                ),
                observed=(
                    f"{ctx.quote_age_seconds:.1f}s old"
                    if ctx.quote_age_seconds is not None
                    else None
                ),
            )
        )


def _check_account_state(
    ctx: RiskContext, rules: list[RuleResult], inputs: dict[str, InputState]
) -> None:
    inputs["account"] = InputState.PRESENT if ctx.account_state_is_current else InputState.STALE
    if _needs_account_state(ctx):
        rules.append(
            RuleResult(
                code=RiskRuleCode.ACCOUNT_STATE_UNKNOWN,
                passed=ctx.account_state_is_current,
                detail=(
                    "account state is stale; balance-dependent limits cannot be evaluated"
                    if not ctx.account_state_is_current
                    else "account state is current"
                ),
            )
        )


def _check_quantity_bounds(
    intent: OrderIntentView, ctx: RiskContext, rules: list[RuleResult]
) -> None:
    if ctx.min_quantity is None and ctx.max_quantity is None:
        return
    below = ctx.min_quantity is not None and intent.quantity < ctx.min_quantity
    above = ctx.max_quantity is not None and intent.quantity > ctx.max_quantity
    rules.append(
        RuleResult(
            code=RiskRuleCode.QUANTITY_OUT_OF_BOUNDS,
            passed=not (below or above),
            detail=(
                "quantity is outside the venue's permitted range"
                if below or above
                else "quantity is within the venue's permitted range"
            ),
            limit=f"{ctx.min_quantity}..{ctx.max_quantity}",
            observed=str(intent.quantity),
        )
    )


def _check_notional_limits(
    intent: OrderIntentView,
    ctx: RiskContext,
    rules: list[RuleResult],
    inputs: dict[str, InputState],
    reference: Decimal | None,
) -> None:
    limit = ctx.policy.max_order_notional
    if limit is None:
        return
    if reference is None:
        inputs["reference_price"] = InputState.MISSING
        rules.append(
            RuleResult(
                code=RiskRuleCode.NOTIONAL_LIMIT_EXCEEDED,
                passed=False,
                detail="cannot value this order — no reference price, so the notional limit "
                "cannot be checked",
                limit=str(limit),
                observed="unmeasurable",
            )
        )
        return
    inputs["reference_price"] = InputState.PRESENT
    value = notional(intent.quantity, reference, contract_size=ctx.contract_size)
    rules.append(
        RuleResult(
            code=RiskRuleCode.NOTIONAL_LIMIT_EXCEEDED,
            passed=value <= limit,
            detail=(
                "order value exceeds the configured per-order limit"
                if value > limit
                else "order value is within the per-order limit"
            ),
            limit=str(limit),
            observed=str(value),
        )
    )


def _check_position_limits(
    intent: OrderIntentView,
    ctx: RiskContext,
    rules: list[RuleResult],
    inputs: dict[str, InputState],
    reference: Decimal | None,
) -> None:
    policy = ctx.policy
    if policy.max_position_notional is not None and not intent.reduce_only:
        if reference is None:
            rules.append(
                RuleResult(
                    code=RiskRuleCode.MAX_POSITION_SIZE_EXCEEDED,
                    passed=False,
                    detail="cannot value the resulting position — no reference price",
                    limit=str(policy.max_position_notional),
                    observed="unmeasurable",
                )
            )
        else:
            projected = ctx.existing_position_notional + notional(
                intent.quantity, reference, contract_size=ctx.contract_size
            )
            rules.append(
                RuleResult(
                    code=RiskRuleCode.MAX_POSITION_SIZE_EXCEEDED,
                    passed=projected <= policy.max_position_notional,
                    detail=(
                        "the resulting position would exceed the configured size limit"
                        if projected > policy.max_position_notional
                        else "the resulting position is within the size limit"
                    ),
                    limit=str(policy.max_position_notional),
                    observed=str(projected),
                )
            )

    if policy.max_open_positions is not None and not intent.reduce_only:
        # A new position only counts if this instrument is not already held.
        projected_count = ctx.open_position_count + (
            0 if ctx.existing_position_notional > ZERO else 1
        )
        rules.append(
            RuleResult(
                code=RiskRuleCode.MAX_OPEN_POSITIONS_EXCEEDED,
                passed=projected_count <= policy.max_open_positions,
                detail=(
                    "this order would open more concurrent positions than permitted"
                    if projected_count > policy.max_open_positions
                    else "concurrent position count is within the limit"
                ),
                limit=str(policy.max_open_positions),
                observed=str(projected_count),
            )
        )


def _check_activity_limits(ctx: RiskContext, rules: list[RuleResult]) -> None:
    limit = ctx.policy.max_orders_per_hour
    if limit is None:
        return
    rules.append(
        RuleResult(
            code=RiskRuleCode.MAX_ORDERS_PER_WINDOW_EXCEEDED,
            passed=ctx.orders_in_last_hour < limit,
            detail=(
                "the hourly order limit has been reached"
                if ctx.orders_in_last_hour >= limit
                else "the hourly order count is within the limit"
            ),
            limit=str(limit),
            observed=str(ctx.orders_in_last_hour),
        )
    )


def _check_loss_limits(
    ctx: RiskContext, rules: list[RuleResult], inputs: dict[str, InputState]
) -> None:
    policy = ctx.policy
    if policy.daily_loss_limit is not None:
        loss = -ctx.realized_pnl_today if ctx.realized_pnl_today < ZERO else ZERO
        rules.append(
            RuleResult(
                code=RiskRuleCode.DAILY_LOSS_LIMIT_BREACHED,
                passed=loss < policy.daily_loss_limit,
                detail=(
                    "today's realized loss has reached the configured limit; "
                    "no new risk may be taken"
                    if loss >= policy.daily_loss_limit
                    else "today's realized loss is within the limit"
                ),
                limit=str(policy.daily_loss_limit),
                observed=str(loss),
            )
        )

    if policy.max_drawdown_percent is not None:
        if ctx.account_equity is None or ctx.peak_equity is None or ctx.peak_equity <= ZERO:
            inputs["equity"] = InputState.MISSING
            rules.append(
                RuleResult(
                    code=RiskRuleCode.DRAWDOWN_LIMIT_BREACHED,
                    passed=False,
                    detail="drawdown cannot be measured — equity or peak equity is unknown",
                    limit=f"{policy.max_drawdown_percent}%",
                    observed="unmeasurable",
                )
            )
        else:
            inputs["equity"] = InputState.PRESENT
            drawdown = (ctx.peak_equity - ctx.account_equity) / ctx.peak_equity * Decimal(100)
            rules.append(
                RuleResult(
                    code=RiskRuleCode.DRAWDOWN_LIMIT_BREACHED,
                    passed=drawdown < policy.max_drawdown_percent,
                    detail=(
                        "account drawdown has reached the configured limit"
                        if drawdown >= policy.max_drawdown_percent
                        else "account drawdown is within the limit"
                    ),
                    limit=f"{policy.max_drawdown_percent}%",
                    observed=f"{drawdown:.2f}%",
                )
            )


def _check_margin(
    ctx: RiskContext,
    rules: list[RuleResult],
    inputs: dict[str, InputState],
    reference: Decimal | None,
    intent: OrderIntentView,
) -> None:
    if ctx.policy.min_margin_level_percent is not None:
        if ctx.margin_level_percent is None:
            inputs["margin"] = InputState.MISSING
            rules.append(
                RuleResult(
                    code=RiskRuleCode.MARGIN_LEVEL_TOO_LOW,
                    passed=False,
                    detail="margin level is unknown; the margin floor cannot be checked",
                    limit=f"{ctx.policy.min_margin_level_percent}%",
                    observed="unmeasurable",
                )
            )
        else:
            inputs["margin"] = InputState.PRESENT
            ok = ctx.margin_level_percent >= ctx.policy.min_margin_level_percent
            rules.append(
                RuleResult(
                    code=RiskRuleCode.MARGIN_LEVEL_TOO_LOW,
                    passed=ok,
                    detail=(
                        "margin level is below the configured floor"
                        if not ok
                        else "margin level is above the configured floor"
                    ),
                    limit=f"{ctx.policy.min_margin_level_percent}%",
                    observed=f"{ctx.margin_level_percent}%",
                )
            )

    if ctx.available_margin is not None and reference is not None and not intent.reduce_only:
        required = notional(intent.quantity, reference, contract_size=ctx.contract_size)
        # Without declared leverage we compare against full notional, which is the
        # conservative reading: it can refuse a fundable order but never permit an unfundable one.
        rules.append(
            RuleResult(
                code=RiskRuleCode.INSUFFICIENT_MARGIN,
                passed=ctx.available_margin >= required,
                detail=(
                    "available margin does not cover this order's notional value"
                    if ctx.available_margin < required
                    else "available margin covers this order"
                ),
                limit=str(ctx.available_margin),
                observed=str(required),
            )
        )


def _check_symbol_permissions(
    intent: OrderIntentView, ctx: RiskContext, rules: list[RuleResult]
) -> None:
    policy = ctx.policy
    symbols = {intent.canonical_symbol, intent.venue_symbol}
    if policy.allowed_symbols is not None:
        allowed = bool(symbols & set(policy.allowed_symbols))
        rules.append(
            RuleResult(
                code=RiskRuleCode.SYMBOL_NOT_PERMITTED,
                passed=allowed,
                detail=(
                    f"{intent.canonical_symbol} is not on the permitted symbol list"
                    if not allowed
                    else f"{intent.canonical_symbol} is permitted"
                ),
            )
        )
    if policy.blocked_symbols:
        blocked = bool(symbols & set(policy.blocked_symbols))
        rules.append(
            RuleResult(
                code=RiskRuleCode.SYMBOL_NOT_PERMITTED,
                passed=not blocked,
                detail=(
                    f"{intent.canonical_symbol} is on the blocked symbol list"
                    if blocked
                    else f"{intent.canonical_symbol} is not blocked"
                ),
            )
        )

    opening_short = intent.side is OrderSide.SELL and not intent.reduce_only
    if opening_short and (not policy.allow_short_selling or not ctx.supports_short_selling):
        rules.append(
            RuleResult(
                code=RiskRuleCode.SHORT_SELLING_NOT_PERMITTED,
                passed=False,
                detail=(
                    "short selling is disabled by policy"
                    if not policy.allow_short_selling
                    else "the venue does not permit short selling for this instrument"
                ),
            )
        )


def _check_price_sanity(
    intent: OrderIntentView,
    ctx: RiskContext,
    rules: list[RuleResult],
    reference: Decimal | None,
) -> None:
    """Catch fat fingers: a limit far from the market is usually a typo, not a strategy."""
    limit_pct = ctx.policy.max_price_deviation_percent
    stated = intent.limit_price or intent.stop_price
    if limit_pct is None or stated is None or reference is None or reference <= ZERO:
        return
    deviation = abs(stated - reference) / reference * Decimal(100)
    rules.append(
        RuleResult(
            code=RiskRuleCode.PRICE_FAR_FROM_MARKET,
            passed=deviation <= limit_pct,
            detail=(
                "the stated price is far from the current market; check for a typo"
                if deviation > limit_pct
                else "the stated price is close to the current market"
            ),
            limit=f"{limit_pct}%",
            observed=f"{deviation:.2f}%",
        )
    )


def _check_mandate(
    intent: OrderIntentView,
    ctx: RiskContext,
    rules: list[RuleResult],
    reference: Decimal | None,
) -> None:
    """A mandate can only *reduce* friction; it can never widen a policy limit (FR-041)."""
    if not ctx.mandate_active or ctx.mandate_remaining_notional is None:
        return
    if reference is None:
        rules.append(
            RuleResult(
                code=RiskRuleCode.MANDATE_LIMIT_EXCEEDED,
                passed=False,
                detail="cannot value this order against the mandate's remaining allowance",
                limit=str(ctx.mandate_remaining_notional),
                observed="unmeasurable",
            )
        )
        return
    value = notional(intent.quantity, reference, contract_size=ctx.contract_size)
    rules.append(
        RuleResult(
            code=RiskRuleCode.MANDATE_LIMIT_EXCEEDED,
            passed=value <= ctx.mandate_remaining_notional,
            detail=(
                "this order exceeds the automation mandate's remaining allowance; "
                "explicit confirmation is required"
                if value > ctx.mandate_remaining_notional
                else "the order is within the mandate's remaining allowance"
            ),
            limit=str(ctx.mandate_remaining_notional),
            observed=str(value),
        )
    )


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------


def _reference_price(intent: OrderIntentView, ctx: RiskContext) -> Decimal | None:
    """The price used to value the order.

    A *stale* quote yields no reference price at all: valuing an order against a price we have
    already declared untrustworthy would defeat the freshness check (FR-039).
    """
    if ctx.quote_freshness is DataFreshness.STALE:
        return None
    if ctx.reference_price is not None:
        return ctx.reference_price
    if intent.order_type is OrderType.LIMIT:
        return intent.limit_price
    return None


def _needs_reference_price(ctx: RiskContext) -> bool:
    policy = ctx.policy
    return any(
        limit is not None
        for limit in (
            policy.max_order_notional,
            policy.max_position_notional,
            policy.max_price_deviation_percent,
        )
    )


def _needs_account_state(ctx: RiskContext) -> bool:
    policy = ctx.policy
    return any(
        limit is not None
        for limit in (
            policy.daily_loss_limit,
            policy.max_drawdown_percent,
            policy.min_margin_level_percent,
        )
    )


def rule_codes() -> Sequence[str]:
    return tuple(str(code) for code in RiskRuleCode)


#: Plain-language meaning of every rule, in evaluation order.
#:
#: These are user-facing. They exist so the API can tell someone *what the gate will check*
#: before they submit, not only what failed afterwards — a refusal a user could have
#: anticipated is a refusal they will not try to route around (Constitution V).
RULE_DESCRIPTIONS: dict[RiskRuleCode, str] = {
    RiskRuleCode.KILL_SWITCH_ENGAGED: (
        "Trading is stopped for your account, this venue, or the whole platform. Nothing "
        "overrides an engaged kill switch."
    ),
    RiskRuleCode.CONNECTION_UNHEALTHY: (
        "The venue connection is not healthy enough to trade — degraded, quarantined, or "
        "on reconciliation hold."
    ),
    RiskRuleCode.ENVIRONMENT_MISMATCH: (
        "The order's environment does not match the connection's. Paper, demo, and live never mix."
    ),
    RiskRuleCode.LIVE_TRADING_DISABLED: (
        "Live order transmission is switched off for this deployment. Paper and demo "
        "trading still work."
    ),
    RiskRuleCode.MARKET_DATA_STALE: (
        "No quote fresh enough to price or size this order. The gate declines rather than "
        "valuing your order against a price we already distrust."
    ),
    RiskRuleCode.ACCOUNT_STATE_UNKNOWN: (
        "Account balance or equity could not be refreshed, so a limit that depends on it "
        "cannot be checked."
    ),
    RiskRuleCode.INSTRUMENT_NOT_TRADABLE: (
        "The instrument is halted, delisted, or outside its trading session."
    ),
    RiskRuleCode.ORDER_TYPE_UNSUPPORTED: (
        "This venue does not accept the requested order type or time-in-force."
    ),
    RiskRuleCode.QUANTITY_OUT_OF_BOUNDS: (
        "Quantity is below the venue minimum, above its maximum, or off its step grid."
    ),
    RiskRuleCode.NOTIONAL_LIMIT_EXCEEDED: (
        "The order's value exceeds your per-order notional limit."
    ),
    RiskRuleCode.MAX_POSITION_SIZE_EXCEEDED: (
        "Filling this order would push the position past your maximum size. Orders that "
        "reduce a position are exempt."
    ),
    RiskRuleCode.MAX_OPEN_POSITIONS_EXCEEDED: (
        "You already hold the maximum number of open positions. Adding to an existing "
        "position does not count as a new one."
    ),
    RiskRuleCode.MAX_ORDERS_PER_WINDOW_EXCEEDED: (
        "You have placed more orders in the last hour than your policy allows."
    ),
    RiskRuleCode.DAILY_LOSS_LIMIT_BREACHED: (
        "Today's realized loss has reached your daily limit, so no new risk may be taken."
    ),
    RiskRuleCode.DRAWDOWN_LIMIT_BREACHED: (
        "Equity has fallen further from its peak than your drawdown limit permits."
    ),
    RiskRuleCode.INSUFFICIENT_MARGIN: (
        "Available margin does not cover this order. Orders that reduce a position are exempt."
    ),
    RiskRuleCode.MARGIN_LEVEL_TOO_LOW: ("Your margin level is below the floor your policy sets."),
    RiskRuleCode.SYMBOL_NOT_PERMITTED: (
        "This instrument is not on your allowed list, or is explicitly blocked."
    ),
    RiskRuleCode.SHORT_SELLING_NOT_PERMITTED: (
        "Your policy forbids opening a short position. Closing a long is not shorting."
    ),
    RiskRuleCode.PRICE_FAR_FROM_MARKET: (
        "The limit or stop price is further from the market than your policy allows — the "
        "guard against a fat-fingered price."
    ),
    RiskRuleCode.MANDATE_REQUIRED: (
        "Automated submission needs an active mandate. Without one, a human must confirm."
    ),
    RiskRuleCode.MANDATE_LIMIT_EXCEEDED: (
        "The order is larger than the mandate's remaining allowance. You can still confirm "
        "it manually — a mandate removes a click, never a limit."
    ),
}


def rule_descriptors() -> Sequence[tuple[str, str]]:
    """``(code, description)`` for every rule, in evaluation order.

    Raises if a rule has no description, so adding a rule without explaining it fails here
    rather than shipping an unexplainable refusal.
    """
    missing = [code for code in RiskRuleCode if code not in RULE_DESCRIPTIONS]
    if missing:  # pragma: no cover - guarded by test_every_rule_has_a_description
        raise AssertionError(f"risk rules without a user-facing description: {missing}")
    return tuple((str(code), RULE_DESCRIPTIONS[code]) for code in RiskRuleCode)


__all__ = [
    "RULE_DESCRIPTIONS",
    "InputState",
    "OrderIntentView",
    "RiskContext",
    "RiskDecision",
    "RiskPolicy",
    "RiskRuleCode",
    "RiskVerdict",
    "RuleResult",
    "evaluate",
    "rule_codes",
    "rule_descriptors",
]
