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

TokenCount = Annotated[int, Field(ge=0, le=MAX_TOKENS)]
PricePerMillion = Annotated[Decimal, Field(ge=0)]


class ModelPrice(BaseModel):
    """One model's published per-million-token prices, as stored in pricing.yaml."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]*$")
    provider: str
    name: str
    input_price_per_million: PricePerMillion
    output_price_per_million: PricePerMillion
    pricing_status: PricingStatus
    effective_date: date
    source_url: HttpUrl | None = None

    @field_validator(
        "input_price_per_million", "output_price_per_million", mode="before"
    )
    @classmethod
    def _reject_floats(cls, value: Any) -> Any:
        if isinstance(value, float):
            raise ValueError(
                'write prices as quoted strings (e.g. "0.15") to avoid float rounding'
            )
        return value

    @model_validator(mode="after")
    def _verified_needs_source(self) -> Self:
        if self.pricing_status == "verified" and self.source_url is None:
            raise ValueError("verified prices must include a source_url")
        return self


class ModelInfo(ModelPrice):
    """A model's pricing plus whether that pricing is out of date."""

    stale: bool


class EstimateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str
    input_tokens: TokenCount
    output_tokens: TokenCount


class Estimate(BaseModel):
    """Cost of a single request. Money values are USD rounded to 6 decimal places."""

    model_id: str
    provider: str
    model_name: str
    input_tokens: int
    output_tokens: int
    input_cost_usd: Decimal
    output_cost_usd: Decimal
    total_cost_usd: Decimal
    currency: Literal["USD"] = "USD"
    pricing_status: PricingStatus
    effective_date: date
    stale: bool
