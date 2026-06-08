from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, InvalidOperation


ZERO = Decimal("0")


def dec(value: object, default: Decimal | None = None) -> Decimal:
    if value is None:
        if default is not None:
            return default
        raise ValueError("Decimal value cannot be None")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        if default is not None:
            return default
        raise ValueError(f"Invalid decimal value: {value!r}") from exc


def quantize_price(price: Decimal, digits: int) -> Decimal:
    unit = Decimal("1").scaleb(-digits)
    return price.quantize(unit, rounding=ROUND_HALF_UP)


def floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= ZERO:
        raise ValueError("step must be positive")
    units = (value / step).to_integral_value(rounding=ROUND_DOWN)
    return units * step


def safe_divide(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == ZERO:
        return None
    return numerator / denominator

