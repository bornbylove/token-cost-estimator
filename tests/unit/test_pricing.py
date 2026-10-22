from datetime import date, timedelta
from decimal import Decimal

import pytest

from tokencost.core.pricing import estimate, is_stale, prices_for, token_cost
from tokencost.core.schemas import (
    MAX_REQUESTS_PER_DAY,
    MAX_TOKENS,
    LongContextPrice,
    ModelPrice,
)

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


def test_projection_does_not_round_tiny_requests_to_zero() -> None:
    cheap = MODEL.model_copy(update={"input_price_per_million": Decimal("0.10")})

    result = estimate(
        cheap,
        1,
        0,
        today=date(2026, 1, 2),
        stale_after_days=90,
        requests_per_day=1_000_000,
    )

    assert result.total_cost_usd == Decimal("0.000000")
    assert result.projection is not None
    assert result.projection.daily_cost_usd == Decimal("0.100000")
    assert result.projection.monthly_cost_usd == Decimal("3.000000")


def test_projection_uses_the_per_request_price_tier() -> None:
    result = estimate(
        TIERED,
        100_001,
        0,
        today=date(2026, 1, 2),
        stale_after_days=90,
        requests_per_day=10,
    )

    assert result.price_tier == "long_context"
    assert result.projection is not None
    # 100,001 tokens x 10 requests at $1.60/M
    assert result.projection.daily_cost_usd == Decimal("1.600016")


def test_projection_handles_maximum_inputs_exactly() -> None:
    result = estimate(
        MODEL,
        MAX_TOKENS,
        MAX_TOKENS,
        today=date(2026, 1, 2),
        stale_after_days=90,
        requests_per_day=MAX_REQUESTS_PER_DAY,
    )

    assert result.projection is not None
    # (1e12 x $0.80 + 1e12 x $4.00) / 1e6 x 1e7 requests x 30 days
    assert result.projection.monthly_cost_usd == Decimal("1440000000000000.000000")


def test_no_projection_without_requests_per_day() -> None:
    result = estimate(MODEL, 1, 1, today=date(2026, 1, 2), stale_after_days=90)

    assert result.projection is None
