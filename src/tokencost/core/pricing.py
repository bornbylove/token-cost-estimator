"""Pure cost arithmetic. No I/O, no framework imports."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from tokencost.core.schemas import Estimate, ModelPrice

MILLION = Decimal(1_000_000)
COST_PRECISION = Decimal("0.000001")


def token_cost(tokens: int, price_per_million: Decimal) -> Decimal:
    """Cost in USD of `tokens` at `price_per_million`, rounded to 6 decimal places."""
    cost = Decimal(tokens) * price_per_million / MILLION
    return cost.quantize(COST_PRECISION, rounding=ROUND_HALF_UP)


def is_stale(model: ModelPrice, *, today: date, stale_after_days: int) -> bool:
    return (today - model.effective_date).days > stale_after_days


def estimate(
    model: ModelPrice,
    input_tokens: int,
    output_tokens: int,
    *,
    today: date,
    stale_after_days: int,
) -> Estimate:
    input_cost = token_cost(input_tokens, model.input_price_per_million)
    output_cost = token_cost(output_tokens, model.output_price_per_million)

    return Estimate(
        model_id=model.id,
        provider=model.provider,
        model_name=model.name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        # Sum the rounded parts so the line items always add up to the total.
        total_cost_usd=input_cost + output_cost,
        pricing_status=model.pricing_status,
        effective_date=model.effective_date,
        stale=is_stale(model, today=today, stale_after_days=stale_after_days),
    )
