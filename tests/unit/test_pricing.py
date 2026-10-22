from datetime import date, timedelta
from decimal import Decimal

import pytest

from tokencost.core.pricing import estimate, is_stale, token_cost
from tokencost.core.schemas import MAX_TOKENS, ModelPrice

MODEL = ModelPrice(
    id="m",
    provider="P",
    name="M",
    input_price_per_million=Decimal("0.80"),
    output_price_per_million=Decimal("4.00"),
    pricing_status="illustrative",
    effective_date=date(2026, 1, 1),
)


@pytest.mark.parametrize(
    ("tokens", "price", "expected"),
    [
        (0, "4.00", "0.000000"),
        (1_000_000, "0.80", "0.800000"),
        (1, "1.00", "0.000001"),
        # 1 token at $0.50/M = 0.0000005 -> rounds half up to 0.000001
        (1, "0.50", "0.000001"),
        # 1 token at $0.40/M = 0.0000004 -> rounds down to 0
        (1, "0.40", "0.000000"),
        (MAX_TOKENS, "100.00", "100000000.000000"),
    ],
)
def test_token_cost(tokens: int, price: str, expected: str) -> None:
    result = token_cost(tokens, Decimal(price))

    assert result == Decimal(expected)
    assert result.as_tuple().exponent == -6


def test_estimate_parts_sum_to_total() -> None:
    result = estimate(
        MODEL, 1_234_567, 89_123, today=date(2026, 1, 2), stale_after_days=90
    )

    assert result.input_cost_usd == Decimal("0.987654")
    assert result.output_cost_usd == Decimal("0.356492")
    assert result.total_cost_usd == result.input_cost_usd + result.output_cost_usd
    assert result.model_name == "M"
    assert result.stale is False


@pytest.mark.parametrize(("age_days", "stale"), [(0, False), (90, False), (91, True)])
def test_is_stale_boundary(age_days: int, stale: bool) -> None:
    today = MODEL.effective_date + timedelta(days=age_days)

    assert is_stale(MODEL, today=today, stale_after_days=90) is stale
