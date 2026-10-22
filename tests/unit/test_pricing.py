from datetime import date, timedelta
from decimal import Decimal

import pytest

from tokencost.core.pricing import estimate, is_stale, prices_for, token_cost
from tokencost.core.schemas import MAX_TOKENS, LongContextPrice, ModelPrice

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


def test_is_stale_after_valid_until_even_when_recent() -> None:
    model = MODEL.model_copy(update={"valid_until": date(2026, 1, 31)})

    assert is_stale(model, today=date(2026, 1, 31), stale_after_days=90) is False
    assert is_stale(model, today=date(2026, 2, 1), stale_after_days=90) is True


TIERED = MODEL.model_copy(
    update={
        "long_context": LongContextPrice(
            above_input_tokens=100_000,
            input_price_per_million=Decimal("1.60"),
            output_price_per_million=Decimal("8.00"),
        )
    }
)


@pytest.mark.parametrize(
    ("input_tokens", "tier", "input_price", "output_price"),
    [
        (100_000, "standard", "0.80", "4.00"),
        (100_001, "long_context", "1.60", "8.00"),
    ],
)
def test_prices_for_threshold_is_exclusive(
    input_tokens: int, tier: str, input_price: str, output_price: str
) -> None:
    assert prices_for(TIERED, input_tokens) == (
        tier,
        Decimal(input_price),
        Decimal(output_price),
    )


def test_prices_for_without_tier_is_always_standard() -> None:
    assert prices_for(MODEL, MAX_TOKENS)[0] == "standard"
