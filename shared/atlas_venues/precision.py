"""Money, price, and quantity arithmetic for trading code (Spec 03 research §13).

Every price and quantity in Atlas is a ``Decimal``. Floats are banned in trading domain code
because a rounding error here changes the order that is actually sent to a venue. The helpers
below apply venue-declared precision at the adapter boundary and refuse — rather than round
silently — when a value cannot be represented at the venue.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation

ZERO = Decimal("0")


class PrecisionError(ValueError):
    """A value cannot be represented at the venue's declared precision."""


def to_decimal(value: object, *, field: str = "value") -> Decimal:
    """Coerce API/venue input to ``Decimal``, rejecting floats outright.

    Floats are rejected rather than converted: accepting them would let an upstream
    ``0.1 + 0.2`` reach a venue as ``0.30000000000000004``.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool) or isinstance(value, float):
        raise PrecisionError(f"{field} must be a decimal string or int, not float/bool")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        try:
            return Decimal(value.strip())
        except InvalidOperation as exc:
            raise PrecisionError(f"{field} is not a valid decimal: {value!r}") from exc
    raise PrecisionError(f"{field} has unsupported type {type(value).__name__}")


def quantize_price(price: Decimal, tick_size: Decimal) -> Decimal:
    """Snap a price to the venue's tick grid (nearest tick, half-up)."""
    if tick_size <= ZERO:
        raise PrecisionError("tick_size must be positive")
    steps = (price / tick_size).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return (steps * tick_size).normalize() + ZERO


def quantize_quantity(quantity: Decimal, step: Decimal) -> Decimal:
    """Snap a quantity down to the venue's step grid.

    Rounding *down* is deliberate: rounding up would send more risk than the user reviewed.
    """
    if step <= ZERO:
        raise PrecisionError("quantity_step must be positive")
    steps = (quantity / step).quantize(Decimal("1"), rounding=ROUND_DOWN)
    return (steps * step).normalize() + ZERO


def is_on_grid(value: Decimal, increment: Decimal) -> bool:
    if increment <= ZERO:
        return False
    return (value % increment) == ZERO


def validate_price(price: Decimal, *, tick_size: Decimal, precision: int, field: str) -> None:
    if price <= ZERO:
        raise PrecisionError(f"{field} must be positive")
    if -price.as_tuple().exponent > precision:  # type: ignore[operator]
        raise PrecisionError(f"{field} exceeds venue price precision of {precision} decimals")
    if not is_on_grid(price, tick_size):
        raise PrecisionError(f"{field} must be a multiple of the tick size {tick_size}")


def validate_quantity(
    quantity: Decimal,
    *,
    minimum: Decimal,
    maximum: Decimal | None,
    step: Decimal,
) -> None:
    if quantity <= ZERO:
        raise PrecisionError("quantity must be positive")
    if quantity < minimum:
        raise PrecisionError(f"quantity {quantity} is below the venue minimum {minimum}")
    if maximum is not None and quantity > maximum:
        raise PrecisionError(f"quantity {quantity} exceeds the venue maximum {maximum}")
    if not is_on_grid(quantity, step):
        raise PrecisionError(f"quantity must be a multiple of the step size {step}")


def notional(quantity: Decimal, price: Decimal, *, contract_size: Decimal | None = None) -> Decimal:
    """Position value in quote currency, honoring contract size where the venue uses one."""
    value = quantity * price
    if contract_size is not None:
        value *= contract_size
    return value


def money(value: Decimal, *, places: int = 2) -> Decimal:
    """Round a monetary display value; never used for order terms."""
    return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


__all__ = [
    "ZERO",
    "PrecisionError",
    "is_on_grid",
    "money",
    "notional",
    "quantize_price",
    "quantize_quantity",
    "to_decimal",
    "validate_price",
    "validate_quantity",
]
