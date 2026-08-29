"""Pre-trade risk gate (US5, T094–T107).

The gate is the last thing between a mistake and real money, so these tests are written to
prove *refusals*: that a missing input rejects rather than skips, that a stale quote cannot be
valued, that a mandate cannot widen a limit, and that a verdict cannot be forged.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from atlas_api.modules.trading.domain.risk import (
    InputState,
    OrderIntentView,
    RiskContext,
    RiskDecision,
    RiskPolicy,
    RiskRuleCode,
    RiskVerdict,
    RuleResult,
    evaluate,
)
from atlas_venues.enums import AssetClass, DataFreshness, OrderSide, OrderType, VenueEnvironment

T0 = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)


def make_intent(**overrides: object) -> OrderIntentView:
    defaults: dict[str, object] = {
        "intent_id": "int-1",
        "venue_code": "paper",
        "venue_account_ref": "acct-1",
        "venue_symbol": "BTCUSDT",
        "canonical_symbol": "BTC/USDT",
        "asset_class": AssetClass.CRYPTO,
        "side": OrderSide.BUY,
        "order_type": OrderType.MARKET,
        "quantity": Decimal("1"),
        "environment": VenueEnvironment.PAPER,
    }
    return OrderIntentView(**{**defaults, **overrides})  # type: ignore[arg-type]


def make_context(policy: RiskPolicy | None = None, **overrides: object) -> RiskContext:
    defaults: dict[str, object] = {
        "evaluated_at": T0,
        "policy": policy or RiskPolicy(policy_id="pol-1"),
        "reference_price": Decimal("60000"),
        "quote_freshness": DataFreshness.FRESH,
        "quote_age_seconds": 0.4,
        "account_equity": Decimal("100000"),
        "available_margin": Decimal("100000"),
        "connection_environment": VenueEnvironment.PAPER,
    }
    return RiskContext(**{**defaults, **overrides})  # type: ignore[arg-type]


def failed_codes(verdict: RiskVerdict) -> set[RiskRuleCode]:
    return {r.code for r in verdict.failed_rules}


class TestVerdictCannotBeForged:
    """T100 — the gate is the only source of an approval."""

    def test_direct_construction_is_refused(self) -> None:
        with pytest.raises(TypeError, match="cannot be constructed directly"):
            RiskVerdict(
                intent_id="int-1",
                decision=RiskDecision.APPROVE,
                evaluated_at=T0,
                rules_evaluated=(),
                inputs_state={},
                policy_id="pol-1",
            )

    def test_construction_with_a_guessed_token_is_refused(self) -> None:
        with pytest.raises(TypeError, match="cannot be constructed directly"):
            RiskVerdict(
                intent_id="int-1",
                decision=RiskDecision.APPROVE,
                evaluated_at=T0,
                rules_evaluated=(),
                inputs_state={},
                policy_id="pol-1",
                _token=object(),
            )

    def test_a_verdict_from_the_gate_is_immutable(self) -> None:
        verdict = evaluate(make_intent(), make_context())
        with pytest.raises((AttributeError, TypeError)):
            verdict.decision = RiskDecision.APPROVE  # type: ignore[misc]

    def test_no_module_level_bypass_exists(self) -> None:
        """FR-038 at the module surface: nothing here hands back an unchecked approval."""
        from atlas_api.modules.trading.domain import risk

        for name in dir(risk):
            assert "bypass" not in name.lower()
            assert "skip_risk" not in name.lower()
            assert "force" not in name.lower()


class TestVerdictHash:
    def test_hash_is_stable_for_the_same_decision(self) -> None:
        first = evaluate(make_intent(), make_context())
        second = evaluate(make_intent(), make_context())
        assert first.hash() == second.hash()

    def test_hash_changes_when_the_terms_change(self) -> None:
        """FR-025: approving one order must not authorize a different one."""
        base = evaluate(make_intent(), make_context())
        bigger = evaluate(make_intent(quantity=Decimal("2")), make_context())
        assert base.hash() != bigger.hash()

    def test_hash_changes_when_the_decision_changes(self) -> None:
        approved = evaluate(make_intent(), make_context())
        rejected = evaluate(make_intent(), make_context(kill_switch_engaged=True))
        assert approved.hash() != rejected.hash()

    def test_hash_is_a_sha256_hex_digest(self) -> None:
        assert len(evaluate(make_intent(), make_context()).hash()) == 64


class TestKillSwitchOutranksEverything:
    def test_engaged_kill_switch_rejects(self) -> None:
        verdict = evaluate(make_intent(), make_context(kill_switch_engaged=True))
        assert verdict.decision is RiskDecision.REJECT
        assert RiskRuleCode.KILL_SWITCH_ENGAGED in failed_codes(verdict)

    def test_a_mandate_does_not_override_the_kill_switch(self) -> None:
        """FR-043: the stop is absolute. A mandate is permission to skip a click, not a limit."""
        verdict = evaluate(
            make_intent(),
            make_context(
                kill_switch_engaged=True,
                mandate_active=True,
                mandate_remaining_notional=Decimal("1000000"),
            ),
        )
        assert verdict.decision is RiskDecision.REJECT
        assert RiskRuleCode.KILL_SWITCH_ENGAGED in failed_codes(verdict)

    def test_the_scope_is_reported(self) -> None:
        verdict = evaluate(
            make_intent(), make_context(kill_switch_engaged=True, kill_switch_scope="operator")
        )
        assert "operator" in verdict.explain()


class TestLiveTradingFlag:
    def test_live_intent_is_rejected_when_the_flag_is_off(self) -> None:
        verdict = evaluate(
            make_intent(environment=VenueEnvironment.LIVE),
            make_context(live_trading_enabled=False, connection_environment=VenueEnvironment.LIVE),
        )
        assert RiskRuleCode.LIVE_TRADING_DISABLED in failed_codes(verdict)

    def test_paper_intent_is_unaffected_by_the_live_flag(self) -> None:
        """Paper must stay usable when live transmission is switched off."""
        verdict = evaluate(make_intent(), make_context(live_trading_enabled=False))
        assert RiskRuleCode.LIVE_TRADING_DISABLED not in failed_codes(verdict)


class TestEnvironmentMismatch:
    def test_paper_intent_on_a_live_connection_is_rejected(self) -> None:
        """FR-050: the two worlds never mix, in either direction."""
        verdict = evaluate(
            make_intent(environment=VenueEnvironment.PAPER),
            make_context(connection_environment=VenueEnvironment.LIVE),
        )
        assert RiskRuleCode.ENVIRONMENT_MISMATCH in failed_codes(verdict)

    def test_live_intent_on_a_demo_connection_is_rejected(self) -> None:
        verdict = evaluate(
            make_intent(environment=VenueEnvironment.LIVE),
            make_context(connection_environment=VenueEnvironment.DEMO),
        )
        assert RiskRuleCode.ENVIRONMENT_MISMATCH in failed_codes(verdict)


class TestStaleAndMissingInputsAreRefused:
    """FR-039 — the gate refuses rather than approximates."""

    def test_stale_quote_rejects_a_market_order(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(quote_freshness=DataFreshness.STALE, quote_age_seconds=12.0),
        )
        assert verdict.decision is RiskDecision.REJECT
        assert RiskRuleCode.MARKET_DATA_STALE in failed_codes(verdict)
        assert verdict.inputs_state["quote"] is InputState.STALE

    def test_missing_quote_rejects_a_market_order(self) -> None:
        verdict = evaluate(make_intent(), make_context(quote_freshness=None, reference_price=None))
        assert RiskRuleCode.MARKET_DATA_STALE in failed_codes(verdict)
        assert verdict.inputs_state["quote"] is InputState.MISSING

    def test_a_stale_quote_cannot_be_used_to_value_an_order(self) -> None:
        """The subtle one: a stale price must not quietly satisfy the notional check."""
        verdict = evaluate(
            make_intent(),
            make_context(
                RiskPolicy(policy_id="pol-1", max_order_notional=Decimal("1000000")),
                quote_freshness=DataFreshness.STALE,
            ),
        )
        assert RiskRuleCode.NOTIONAL_LIMIT_EXCEEDED in failed_codes(verdict)
        observed = next(
            r.observed
            for r in verdict.failed_rules
            if r.code is RiskRuleCode.NOTIONAL_LIMIT_EXCEEDED
        )
        assert observed == "unmeasurable"

    def test_unmeasurable_drawdown_rejects(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(
                RiskPolicy(policy_id="pol-1", max_drawdown_percent=Decimal("20")),
                peak_equity=None,
            ),
        )
        assert RiskRuleCode.DRAWDOWN_LIMIT_BREACHED in failed_codes(verdict)

    def test_unknown_margin_level_rejects_when_a_floor_is_configured(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(
                RiskPolicy(policy_id="pol-1", min_margin_level_percent=Decimal("150")),
                margin_level_percent=None,
            ),
        )
        assert RiskRuleCode.MARGIN_LEVEL_TOO_LOW in failed_codes(verdict)

    def test_stale_account_state_rejects_when_a_balance_limit_applies(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(
                RiskPolicy(policy_id="pol-1", daily_loss_limit=Decimal("500")),
                account_state_is_current=False,
            ),
        )
        assert RiskRuleCode.ACCOUNT_STATE_UNKNOWN in failed_codes(verdict)

    def test_stale_account_state_is_tolerated_when_no_balance_limit_applies(self) -> None:
        """Don't refuse for an input no configured rule actually needs."""
        verdict = evaluate(make_intent(), make_context(account_state_is_current=False))
        assert RiskRuleCode.ACCOUNT_STATE_UNKNOWN not in failed_codes(verdict)


class TestNotionalAndPositionLimits:
    def test_order_over_the_notional_limit_is_rejected(self) -> None:
        verdict = evaluate(
            make_intent(quantity=Decimal("1")),
            make_context(RiskPolicy(policy_id="pol-1", max_order_notional=Decimal("50000"))),
        )
        assert RiskRuleCode.NOTIONAL_LIMIT_EXCEEDED in failed_codes(verdict)

    def test_order_at_exactly_the_limit_is_allowed(self) -> None:
        verdict = evaluate(
            make_intent(quantity=Decimal("1")),
            make_context(RiskPolicy(policy_id="pol-1", max_order_notional=Decimal("60000"))),
        )
        assert RiskRuleCode.NOTIONAL_LIMIT_EXCEEDED not in failed_codes(verdict)

    def test_contract_size_is_applied_to_the_valuation(self) -> None:
        """A 1-lot FX order is 100,000 units; ignoring that understates risk enormously."""
        verdict = evaluate(
            make_intent(quantity=Decimal("1"), asset_class=AssetClass.FOREX),
            make_context(
                RiskPolicy(policy_id="pol-1", max_order_notional=Decimal("50000")),
                reference_price=Decimal("1.10"),
                contract_size=Decimal("100000"),
            ),
        )
        assert RiskRuleCode.NOTIONAL_LIMIT_EXCEEDED in failed_codes(verdict)

    def test_projected_position_includes_what_is_already_held(self) -> None:
        verdict = evaluate(
            make_intent(quantity=Decimal("1")),
            make_context(
                RiskPolicy(policy_id="pol-1", max_position_notional=Decimal("100000")),
                existing_position_notional=Decimal("60000"),
            ),
        )
        assert RiskRuleCode.MAX_POSITION_SIZE_EXCEEDED in failed_codes(verdict)

    def test_reduce_only_orders_skip_position_growth_limits(self) -> None:
        """Closing risk must never be blocked by a limit on taking risk."""
        verdict = evaluate(
            make_intent(quantity=Decimal("1"), reduce_only=True),
            make_context(
                RiskPolicy(policy_id="pol-1", max_position_notional=Decimal("1")),
                existing_position_notional=Decimal("60000"),
            ),
        )
        assert RiskRuleCode.MAX_POSITION_SIZE_EXCEEDED not in failed_codes(verdict)

    def test_open_position_count_limit(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(
                RiskPolicy(policy_id="pol-1", max_open_positions=3), open_position_count=3
            ),
        )
        assert RiskRuleCode.MAX_OPEN_POSITIONS_EXCEEDED in failed_codes(verdict)

    def test_adding_to_an_existing_position_does_not_count_as_a_new_one(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(
                RiskPolicy(policy_id="pol-1", max_open_positions=3),
                open_position_count=3,
                existing_position_notional=Decimal("1000"),
            ),
        )
        assert RiskRuleCode.MAX_OPEN_POSITIONS_EXCEEDED not in failed_codes(verdict)


class TestLossLimits:
    def test_daily_loss_limit_blocks_new_risk(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(
                RiskPolicy(policy_id="pol-1", daily_loss_limit=Decimal("500")),
                realized_pnl_today=Decimal("-500"),
            ),
        )
        assert RiskRuleCode.DAILY_LOSS_LIMIT_BREACHED in failed_codes(verdict)

    def test_a_profitable_day_does_not_trip_the_loss_limit(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(
                RiskPolicy(policy_id="pol-1", daily_loss_limit=Decimal("500")),
                realized_pnl_today=Decimal("1200"),
            ),
        )
        assert RiskRuleCode.DAILY_LOSS_LIMIT_BREACHED not in failed_codes(verdict)

    def test_drawdown_limit(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(
                RiskPolicy(policy_id="pol-1", max_drawdown_percent=Decimal("20")),
                account_equity=Decimal("75000"),
                peak_equity=Decimal("100000"),
            ),
        )
        assert RiskRuleCode.DRAWDOWN_LIMIT_BREACHED in failed_codes(verdict)


class TestMarginChecks:
    def test_insufficient_margin_is_rejected(self) -> None:
        verdict = evaluate(
            make_intent(quantity=Decimal("1")),
            make_context(available_margin=Decimal("100")),
        )
        assert RiskRuleCode.INSUFFICIENT_MARGIN in failed_codes(verdict)

    def test_margin_floor_is_enforced(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(
                RiskPolicy(policy_id="pol-1", min_margin_level_percent=Decimal("150")),
                margin_level_percent=Decimal("120"),
            ),
        )
        assert RiskRuleCode.MARGIN_LEVEL_TOO_LOW in failed_codes(verdict)

    def test_closing_orders_are_not_blocked_by_margin(self) -> None:
        verdict = evaluate(
            make_intent(reduce_only=True),
            make_context(available_margin=Decimal("0")),
        )
        assert RiskRuleCode.INSUFFICIENT_MARGIN not in failed_codes(verdict)


class TestSymbolPermissions:
    def test_symbol_not_on_the_allow_list_is_rejected(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(RiskPolicy(policy_id="pol-1", allowed_symbols=frozenset({"ETH/USDT"}))),
        )
        assert RiskRuleCode.SYMBOL_NOT_PERMITTED in failed_codes(verdict)

    def test_allow_list_matches_canonical_or_venue_symbol(self) -> None:
        for symbol in ("BTC/USDT", "BTCUSDT"):
            verdict = evaluate(
                make_intent(),
                make_context(RiskPolicy(policy_id="pol-1", allowed_symbols=frozenset({symbol}))),
            )
            assert RiskRuleCode.SYMBOL_NOT_PERMITTED not in failed_codes(verdict)

    def test_blocked_symbol_is_rejected(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(RiskPolicy(policy_id="pol-1", blocked_symbols=frozenset({"BTC/USDT"}))),
        )
        assert RiskRuleCode.SYMBOL_NOT_PERMITTED in failed_codes(verdict)

    def test_short_selling_can_be_disabled_by_policy(self) -> None:
        verdict = evaluate(
            make_intent(side=OrderSide.SELL),
            make_context(RiskPolicy(policy_id="pol-1", allow_short_selling=False)),
        )
        assert RiskRuleCode.SHORT_SELLING_NOT_PERMITTED in failed_codes(verdict)

    def test_closing_a_long_is_not_treated_as_shorting(self) -> None:
        verdict = evaluate(
            make_intent(side=OrderSide.SELL, reduce_only=True),
            make_context(RiskPolicy(policy_id="pol-1", allow_short_selling=False)),
        )
        assert RiskRuleCode.SHORT_SELLING_NOT_PERMITTED not in failed_codes(verdict)


class TestPriceSanity:
    def test_limit_far_from_market_is_rejected(self) -> None:
        verdict = evaluate(
            make_intent(order_type=OrderType.LIMIT, limit_price=Decimal("6000")),
            make_context(
                RiskPolicy(policy_id="pol-1", max_price_deviation_percent=Decimal("10")),
                reference_price=Decimal("60000"),
            ),
        )
        assert RiskRuleCode.PRICE_FAR_FROM_MARKET in failed_codes(verdict)

    def test_limit_near_market_passes(self) -> None:
        verdict = evaluate(
            make_intent(order_type=OrderType.LIMIT, limit_price=Decimal("59500")),
            make_context(
                RiskPolicy(policy_id="pol-1", max_price_deviation_percent=Decimal("10")),
                reference_price=Decimal("60000"),
            ),
        )
        assert RiskRuleCode.PRICE_FAR_FROM_MARKET not in failed_codes(verdict)


class TestVenueAndInstrumentChecks:
    def test_unhealthy_connection_is_rejected(self) -> None:
        verdict = evaluate(make_intent(), make_context(connection_can_trade=False))
        assert RiskRuleCode.CONNECTION_UNHEALTHY in failed_codes(verdict)

    def test_untradable_instrument_is_rejected(self) -> None:
        verdict = evaluate(make_intent(), make_context(instrument_is_tradable=False))
        assert RiskRuleCode.INSTRUMENT_NOT_TRADABLE in failed_codes(verdict)

    def test_unsupported_order_type_is_rejected(self) -> None:
        verdict = evaluate(
            make_intent(
                order_type=OrderType.STOP_LIMIT,
                limit_price=Decimal("1"),
                stop_price=Decimal("1"),
            ),
            make_context(supported_order_types=frozenset({OrderType.MARKET, OrderType.LIMIT})),
        )
        assert RiskRuleCode.ORDER_TYPE_UNSUPPORTED in failed_codes(verdict)

    def test_quantity_below_venue_minimum_is_rejected(self) -> None:
        verdict = evaluate(
            make_intent(quantity=Decimal("0.0000001")),
            make_context(min_quantity=Decimal("0.001")),
        )
        assert RiskRuleCode.QUANTITY_OUT_OF_BOUNDS in failed_codes(verdict)


class TestMandates:
    def test_without_a_mandate_confirmation_is_required(self) -> None:
        """FR-024 — the default is always a human click."""
        verdict = evaluate(make_intent(), make_context())
        assert verdict.decision is RiskDecision.REQUIRE_CONFIRMATION
        assert verdict.approved

    def test_an_active_mandate_within_its_allowance_approves_outright(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(mandate_active=True, mandate_remaining_notional=Decimal("100000")),
        )
        assert verdict.decision is RiskDecision.APPROVE

    def test_an_order_beyond_the_mandate_allowance_is_rejected(self) -> None:
        verdict = evaluate(
            make_intent(quantity=Decimal("1")),
            make_context(mandate_active=True, mandate_remaining_notional=Decimal("100")),
        )
        assert RiskRuleCode.MANDATE_LIMIT_EXCEEDED in failed_codes(verdict)

    def test_a_mandate_cannot_widen_a_policy_limit(self) -> None:
        """FR-041: a mandate removes a click, never a limit."""
        verdict = evaluate(
            make_intent(quantity=Decimal("1")),
            make_context(
                RiskPolicy(policy_id="pol-1", max_order_notional=Decimal("100")),
                mandate_active=True,
                mandate_remaining_notional=Decimal("999999999"),
            ),
        )
        assert verdict.decision is RiskDecision.REJECT
        assert RiskRuleCode.NOTIONAL_LIMIT_EXCEEDED in failed_codes(verdict)

    def test_policy_can_force_confirmation_despite_a_mandate(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(
                RiskPolicy(policy_id="pol-1", require_confirmation_always=True),
                mandate_active=True,
                mandate_remaining_notional=Decimal("100000"),
            ),
        )
        assert verdict.decision is RiskDecision.REQUIRE_CONFIRMATION


class TestExplainability:
    """Constitution V — a verdict a user cannot understand is not a usable safety control."""

    def test_every_rule_is_recorded_pass_or_fail(self) -> None:
        verdict = evaluate(make_intent(), make_context())
        assert verdict.rules_evaluated
        assert all(isinstance(r, RuleResult) for r in verdict.rules_evaluated)

    def test_all_failures_are_reported_not_just_the_first(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(
                RiskPolicy(policy_id="pol-1", max_order_notional=Decimal("1")),
                kill_switch_engaged=True,
                connection_can_trade=False,
            ),
        )
        assert len(verdict.failed_rules) >= 3

    def test_explain_names_the_failing_rules_and_the_numbers(self) -> None:
        verdict = evaluate(
            make_intent(),
            make_context(RiskPolicy(policy_id="pol-1", max_order_notional=Decimal("100"))),
        )
        text = verdict.explain()
        assert "notional_limit_exceeded" in text
        assert "limit 100" in text
        assert "observed 60000" in text
        assert "pol-1" in text

    def test_reasons_are_populated_on_rejection(self) -> None:
        verdict = evaluate(make_intent(), make_context(kill_switch_engaged=True))
        assert verdict.reasons
        assert any("kill_switch" in r for r in verdict.reasons)

    def test_an_empty_policy_still_produces_a_reviewable_verdict(self) -> None:
        """A user with no limits configured must still get an explainable decision."""
        verdict = evaluate(make_intent(), make_context())
        assert verdict.rules_evaluated
        assert verdict.explain()


class TestPolicyValidation:
    def test_float_limits_are_refused(self) -> None:
        with pytest.raises(TypeError, match="must be Decimal"):
            RiskPolicy(policy_id="pol-1", max_order_notional=1000.0)  # type: ignore[arg-type]

    def test_negative_limits_are_refused(self) -> None:
        with pytest.raises(ValueError, match="must not be negative"):
            RiskPolicy(policy_id="pol-1", max_order_notional=Decimal("-1"))

    def test_a_zero_limit_is_legal_and_rejects_everything(self) -> None:
        """Zero is a real limit — distinct from None, which means 'no rule configured'."""
        verdict = evaluate(
            make_intent(),
            make_context(RiskPolicy(policy_id="pol-1", max_order_notional=Decimal("0"))),
        )
        assert RiskRuleCode.NOTIONAL_LIMIT_EXCEEDED in failed_codes(verdict)
