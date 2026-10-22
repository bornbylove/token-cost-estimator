from decimal import Decimal
from typing import Annotated, TypedDict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="Token Cost Estimator API",
    description="Estimate token costs across AI providers.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# These are illustrative starter rates, not verified live prices.
# Verify and update them against each provider's official pricing
# before using estimates for billing or financial decisions.
class ModelPricing(TypedDict):
    id: str
    provider: str
    name: str
    input_price_per_million: Decimal
    output_price_per_million: Decimal
    pricing_status: str


MODEL_PRICING: list[ModelPricing] = [
    {
        "id": "openai-example",
        "provider": "OpenAI",
        "name": "OpenAI example model",
        "input_price_per_million": Decimal("0.15"),
        "output_price_per_million": Decimal("0.60"),
        "pricing_status": "illustrative",
    },
    {
        "id": "anthropic-example",
        "provider": "Anthropic",
        "name": "Anthropic example model",
        "input_price_per_million": Decimal("0.80"),
        "output_price_per_million": Decimal("4.00"),
        "pricing_status": "illustrative",
    },
    {
        "id": "google-example",
        "provider": "Google",
        "name": "Google example model",
        "input_price_per_million": Decimal("0.30"),
        "output_price_per_million": Decimal("2.50"),
        "pricing_status": "illustrative",
    },
]


class EstimateRequest(BaseModel):
    model_id: str
    input_tokens: Annotated[int, Field(ge=0)]
    output_tokens: Annotated[int, Field(ge=0)]


class EstimateResponse(BaseModel):
    model_id: str
    provider: str
    input_tokens: int
    output_tokens: int
    input_cost_usd: Decimal
    output_cost_usd: Decimal
    total_cost_usd: Decimal
    currency: str = "USD"
    pricing_status: str


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Token Cost Estimator",
        "status": "running",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/api/models")
def list_models() -> list[dict[str, object]]:
    return [
        {
            **model,
            "input_price_per_million": str(model["input_price_per_million"]),
            "output_price_per_million": str(model["output_price_per_million"]),
        }
        for model in MODEL_PRICING
    ]


@app.post("/api/estimate", response_model=EstimateResponse)
def estimate_cost(request: EstimateRequest) -> EstimateResponse:
    model = next(
        (item for item in MODEL_PRICING if item["id"] == request.model_id),
        None,
    )

    if model is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown model_id. Fetch available models from /api/models.",
        )

    million = Decimal("1000000")

    input_cost = (
        Decimal(request.input_tokens) * model["input_price_per_million"] / million
    )
    output_cost = (
        Decimal(request.output_tokens) * model["output_price_per_million"] / million
    )

    return EstimateResponse(
        model_id=model["id"],
        provider=model["provider"],
        input_tokens=request.input_tokens,
        output_tokens=request.output_tokens,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        total_cost_usd=input_cost + output_cost,
        pricing_status=model["pricing_status"],
    )
