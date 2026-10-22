"""Pure cost arithmetic. No I/O, no framework imports."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from tokencost.core.schemas import (
    DAYS_PER_MONTH,
    Estimate,
    ModelPrice,
    PriceTier,
    Projection,
)

MILLION = Decimal(1_000_000)
COST_PRECISION = Decimal("0.000001")


def token_cost(tokens: int, price_per_million: Decimal) -> Decimal:
    """Cost in USD of `tokens` at `price_per_million`, rounded to 6 decimal places."""
    cost = Decimal(tokens) * price_per_million / MILLION
    return cost.quantize(COST_PRECISION, rounding=ROUND_HALF_UP)


def is_stale(model: ModelPrice, *, today: date, stale_after_days: int) -> bool:
    """True when the price is too old to trust or past its announced end date."""
    if model.valid_until is not None and today > model.valid_until:
        return True
    return (today - model.effective_date).days > stale_after_days


def prices_for(
    model: ModelPrice, input_tokens: int
) -> tuple[PriceTier, Decimal, Decimal]:
    """The (tier, input price, output price) that apply to a request of this size."""
    tier = model.long_context
    if tier is not None and input_tokens > tier.above_input_tokens:
        return (
            "long_context",
            tier.input_price_per_million,
            tier.output_price_per_million,
        )
    return (
        "standard",
        model.input_price_per_million,
        model.output_price_per_million,
    )


def project(
    input_tokens: int,
    output_tokens: int,
    input_price: Decimal,
    output_price: Decimal,
    requests_per_day: int,
) -> Projection:
    def cost_of(requests: int) -> Decimal:
        # Multiply tokens before rounding, so many tiny requests don't round to $0.
        return token_cost(input_tokens * requests, input_price) + token_cost(
            output_tokens * requests, output_price
        )

    return Projection(
        requests_per_day=requests_per_day,
        daily_cost_usd=cost_of(requests_per_day),
        monthly_cost_usd=cost_of(requests_per_day * DAYS_PER_MONTH),
    )


def estimate(
    model: ModelPrice,
    input_tokens: int,
    output_tokens: int,
    *,
    today: date,
    stale_after_days: int,
    requests_per_day: int | None = None,
) -> Estimate:
    # The price tier depends on the size of each individual request.
    price_tier, input_price, output_price = prices_for(model, input_tokens)
    input_cost = token_cost(input_tokens, input_price)
    output_cost = token_cost(output_tokens, output_price)
    projection = (
        None
        if requests_per_day is None
        else project(
            input_tokens, output_tokens, input_price, output_price, requests_per_day
        )
    )

    return Estimate(
        model_id=model.id,
        provider=model.provider,
        model_name=model.name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        price_tier=price_tier,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        # Sum the rounded parts so the line items always add up to the total.
        total_cost_usd=input_cost + output_cost,
        projection=projection,
        pricing_status=model.pricing_status,
        effective_date=model.effective_date,
        valid_until=model.valid_until,
        stale=is_stale(model, today=today, stale_after_days=stale_after_days),
        notes=model.notes,
    )
