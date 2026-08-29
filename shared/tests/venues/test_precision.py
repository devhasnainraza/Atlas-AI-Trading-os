"""Decimal arithmetic and venue precision (T019).

These tests exist because the failure mode is silent: a float that survives to the wire sends
a different order than the one the user approved.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from atlas_venues.precision import (
    PrecisionError,
    is_on_grid,
    money,
    notional,
    quantize_price,
    quantize_quantity,
    to_decimal,
    validate_price,
    validate_quantity,
)


class TestToDecimal:
    def test_accepts_decimal_and_int_and_string(self) -> None:
        assert to_decimal(Decimal("1.5")) == Decimal("1.5")
        assert to_decimal(3) == Decimal("3")
        assert to_decimal(" 2.25 ") == Decimal("2.25")

    @pytest.mark.parametrize("bad", [0.1, 1.0, True, False])
    def test_rejects_floats_and_bools(self, bad: object) -> None:
        """A float is never coerced — accepting one is how 0.1+0.2 reaches a venue."""
        with pytest.raises(PrecisionError, match="not float/bool"):
            to_decimal(bad, field="price")

    def test_rejects_garbage_strings(self) -> None:
        with pytest.raises(PrecisionError, match="not a valid decimal"):
            to_decimal("about three", field="quantity")

    def test_rejects_unsupported_types(self) -> None:
        with pytest.raises(PrecisionError, match="unsupported type"):
            to_decimal(object())


class TestQuantize:
    def test_price_snaps_to_nearest_tick(self) -> None:
        assert quantize_price(Decimal("1.23456"), Decimal("0.0001")) == Decimal("1.2346")
        assert quantize_price(Decimal("1.23444"), Decimal("0.0001")) == Decimal("1.2344")

    def test_quantity_always_rounds_down(self) -> None:
        """Rounding up would send more risk than the user reviewed."""
        assert quantize_quantity(Decimal("0.123999"), Decimal("0.001")) == Decimal("0.123")
        assert quantize_quantity(Decimal("0.9999"), Decimal("0.5")) == Decimal("0.5")

    @pytest.mark.parametrize("bad_increment", [Decimal("0"), Decimal("-0.1")])
    def test_non_positive_increments_are_rejected(self, bad_increment: Decimal) -> None:
        with pytest.raises(PrecisionError):
            quantize_price(Decimal("1"), bad_increment)
        with pytest.raises(PrecisionError):
            quantize_quantity(Decimal("1"), bad_increment)

    def test_is_on_grid(self) -> None:
        assert is_on_grid(Decimal("1.20"), Decimal("0.01"))
        assert not is_on_grid(Decimal("1.205"), Decimal("0.01"))
        assert not is_on_grid(Decimal("1"), Decimal("0"))


class TestValidatePrice:
    def test_accepts_a_grid_aligned_price(self) -> None:
        validate_price(Decimal("1.2345"), tick_size=Decimal("0.0001"), precision=4, field="limit")

    def test_rejects_off_grid(self) -> None:
        with pytest.raises(PrecisionError, match="multiple of the tick size"):
            validate_price(
                Decimal("1.23455"), tick_size=Decimal("0.0001"), precision=5, field="limit"
            )

    def test_rejects_excess_precision(self) -> None:
        with pytest.raises(PrecisionError, match="price precision"):
            validate_price(
                Decimal("1.234567"), tick_size=Decimal("0.000001"), precision=4, field="limit"
            )

    @pytest.mark.parametrize("bad", [Decimal("0"), Decimal("-1")])
    def test_rejects_non_positive(self, bad: Decimal) -> None:
        with pytest.raises(PrecisionError, match="must be positive"):
            validate_price(bad, tick_size=Decimal("0.01"), precision=2, field="limit")


class TestValidateQuantity:
    def test_accepts_within_bounds(self) -> None:
        validate_quantity(
            Decimal("0.5"), minimum=Decimal("0.1"), maximum=Decimal("1"), step=Decimal("0.1")
        )

    def test_rejects_below_minimum(self) -> None:
        with pytest.raises(PrecisionError, match="below the venue minimum"):
            validate_quantity(
                Decimal("0.05"), minimum=Decimal("0.1"), maximum=None, step=Decimal("0.01")
            )

    def test_rejects_above_maximum(self) -> None:
        with pytest.raises(PrecisionError, match="exceeds the venue maximum"):
            validate_quantity(
                Decimal("5"), minimum=Decimal("0.1"), maximum=Decimal("1"), step=Decimal("0.1")
            )

    def test_rejects_off_step(self) -> None:
        with pytest.raises(PrecisionError, match="multiple of the step size"):
            validate_quantity(
                Decimal("0.15"), minimum=Decimal("0.1"), maximum=None, step=Decimal("0.1")
            )

    def test_unbounded_maximum_is_allowed(self) -> None:
        validate_quantity(
            Decimal("1000000"), minimum=Decimal("0.1"), maximum=None, step=Decimal("0.1")
        )


class TestNotionalAndMoney:
    def test_notional_without_contract_size(self) -> None:
        assert notional(Decimal("2"), Decimal("100")) == Decimal("200")

    def test_notional_honours_contract_size(self) -> None:
        """A 1-lot FX position is 100,000 units, not 1 — omitting this understates risk 100,000x."""
        assert notional(Decimal("1"), Decimal("1.10"), contract_size=Decimal("100000")) == Decimal(
            "110000.00"
        )

    def test_money_rounds_half_up_for_display(self) -> None:
        assert money(Decimal("1.005")) == Decimal("1.01")
        assert money(Decimal("1.004")) == Decimal("1.00")
