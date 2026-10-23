from decimal import Decimal

import pytest

from tokencost.cli.format import format_compact, format_usd, parse_count


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("3000", 3_000),
        ("3,000", 3_000),
        ("3_000", 3_000),
        ("3k", 3_000),
        ("3K", 3_000),
        ("1.5M", 1_500_000),
        (" 0 ", 0),
        ("1e3", 1_000),
    ],
)
def test_parse_count(text: str, expected: int) -> None:
    assert parse_count(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "1.5", "-1", "1.0001k", "inf", "nan"])
def test_parse_count_rejects(text: str) -> None:
    with pytest.raises(ValueError):
        parse_count(text)


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("0", "$0.00"),
        ("0.000700", "$0.0007"),
        ("0.014000", "$0.014"),
        ("105.000000", "$105.00"),
        ("10500", "$10,500.00"),
        ("1.600016", "$1.600016"),
    ],
)
def test_format_usd(amount: str, expected: str) -> None:
    assert format_usd(Decimal(amount)) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(100_000, "100K"), (272_000, "272K"), (1_500_000, "1.5M"), (1_234, "1,234")],
)
def test_format_compact(value: int, expected: str) -> None:
    assert format_compact(value) == expected
