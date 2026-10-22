from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

PricingStatus = Literal["illustrative", "verified"]

# Upper bound on any token count we accept, to keep arithmetic and abuse in check.
MAX_TOKENS = 1_000_000_000_000

MAX_REQUESTS_PER_DAY = 10_000_000
MAX_COMPARE_MODELS = 50
MAX_TEXT_CHARS = 1_000_000
DAYS_PER_MONTH = 30

TokenCount = Annotated[int, Field(ge=0, le=MAX_TOKENS)]
PricePerMillion = Annotated[Decimal, Field(ge=0)]
PriceTier = Literal["standard", "long_context"]


def _reject_float(value: Any) -> Any:
    if isinstance(value, float):
        raise ValueError(
            'write prices as quoted strings (e.g. "0.15") to avoid float rounding'
        )
    return value


class LongContextPrice(BaseModel):
    """Higher prices that apply to a request whose input exceeds a threshold."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    above_input_tokens: int = Field(gt=0)
    input_price_per_million: PricePerMillion
    output_price_per_million: PricePerMillion

    _no_floats = field_validator(
        "input_price_per_million", "output_price_per_million", mode="before"
    )(_reject_float)


class ModelPrice(BaseModel):
    """One model's published per-million-token prices, as stored in pricing.yaml."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]*$")
    provider: str
    name: str
    input_price_per_million: PricePerMillion
    output_price_per_million: PricePerMillion
    long_context: LongContextPrice | None = None
    pricing_status: PricingStatus
    effective_date: date
    # Last day these prices apply, for announced price changes.
    valid_until: date | None = None
    source_url: HttpUrl | None = None
    notes: str | None = None

    _no_floats = field_validator(
        "input_price_per_million", "output_price_per_million", mode="before"
    )(_reject_float)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.pricing_status == "verified" and self.source_url is None:
            raise ValueError("verified prices must include a source_url")
        if self.valid_until is not None and self.valid_until < self.effective_date:
            raise ValueError("valid_until must not be before effective_date")
        return self


class ModelInfo(ModelPrice):
    """A model's pricing plus whether that pricing is out of date."""

    stale: bool


class _Usage(BaseModel):
    """Token usage of one request, optionally repeated daily for a projection."""

    model_config = ConfigDict(extra="forbid")

    input_tokens: TokenCount
    output_tokens: TokenCount
    requests_per_day: int | None = Field(default=None, ge=1, le=MAX_REQUESTS_PER_DAY)


class EstimateRequest(_Usage):
    model_id: str


class CompareRequest(_Usage):
    # Omit to compare every available model.
    model_ids: list[str] | None = Field(
        default=None, min_length=1, max_length=MAX_COMPARE_MODELS
    )


class Projection(BaseModel):
    """Cost of repeating the same request every day."""

    requests_per_day: int
    days_per_month: int = DAYS_PER_MONTH
    daily_cost_usd: Decimal
    monthly_cost_usd: Decimal


class Estimate(BaseModel):
    """Cost of a single request. Money values are USD rounded to 6 decimal places."""

    model_id: str
    provider: str
    model_name: str
    input_tokens: int
    output_tokens: int
    price_tier: PriceTier
    input_cost_usd: Decimal
    output_cost_usd: Decimal
    total_cost_usd: Decimal
    currency: Literal["USD"] = "USD"
    projection: Projection | None = None
    pricing_status: PricingStatus
    effective_date: date
    valid_until: date | None
    stale: bool
    notes: str | None


class Comparison(BaseModel):
    """Estimates for several models, cheapest first."""

    estimates: list[Estimate]
    # Every model tied for the lowest per-request cost.
    cheapest_model_ids: list[str]


class TokenCountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(max_length=MAX_TEXT_CHARS)


class TokenCountResult(BaseModel):
    characters: int
    tokens: int
    method: Literal["approximate"]
    tokenizer: str
    note: str
