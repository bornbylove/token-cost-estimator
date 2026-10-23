"""Parsing and display helpers for the CLI."""

from decimal import Decimal, InvalidOperation

_SUFFIXES = {"k": 1_000, "m": 1_000_000}


def parse_count(value: str) -> int:
    """Parse a human-friendly count: 3000, 3,000, 3_000, 3k, 1.5M."""
    text = value.strip().replace(",", "").replace("_", "").lower()
    multiplier = 1
    if text and text[-1] in _SUFFIXES:
        multiplier = _SUFFIXES[text[-1]]
        text = text[:-1]
    try:
        number = Decimal(text) * multiplier
    except InvalidOperation:
        raise ValueError(f"{value!r} is not a number") from None
    if not number.is_finite() or number < 0 or number != number.to_integral_value():
        raise ValueError(f"{value!r} is not a whole, non-negative number")
    return int(number)


def format_usd(amount: Decimal) -> str:
    """$10,500.00 or $0.0029: at least 2 decimals, up to 6, no trailing zeros."""
    whole, _, fraction = f"{amount:,.6f}".partition(".")
    return f"${whole}.{fraction.rstrip('0').ljust(2, '0')}"


def format_int(value: int) -> str:
    return f"{value:,}"


def format_compact(value: int) -> str:
    """272K, 1.5M; falls back to 1,234 when the value isn't a round K or M."""
    for divisor, suffix in ((1_000_000, "M"), (1_000, "K")):
        if value >= divisor and (value * 10) % divisor == 0:
            return f"{value / divisor:g}{suffix}"
    return format_int(value)
