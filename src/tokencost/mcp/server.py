"""MCP server: the pricing service exposed as tools for AI agents.

Served over stdio by the `tokencost-mcp` command, and over Streamable HTTP at
/mcp by the web app.
"""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field

from tokencost import __version__
from tokencost.core import tokenizer
from tokencost.core.config import Settings
from tokencost.core.schemas import (
    MAX_COMPARE_MODELS,
    MAX_REQUESTS_PER_DAY,
    MAX_TEXT_CHARS,
    MAX_TOKENS,
    CompareRequest,
    Comparison,
    Estimate,
    EstimateRequest,
    ModelInfo,
    TokenCountResult,
)
from tokencost.core.service import ModelNotFoundError, PricingService

INSTRUCTIONS = (
    "Estimates what AI model API calls cost, using each provider's published "
    "standard prices in USD. Call list_models for valid model ids. "
    "estimate_cost and compare_models take token counts for ONE request; add "
    "requests_per_day for daily and 30-day totals. Prices that depend on prompt "
    "size are applied automatically (see price_tier). Results are estimates, not "
    "invoices: check `stale` and `notes` before relying on a figure. count_tokens "
    "gives an approximate count for text when exact token counts are unknown."
)

# Every tool only reads bundled data: safe to call repeatedly, no side effects.
READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)

ModelId = Annotated[str, Field(description="Model id from list_models.")]
InputTokens = Annotated[
    int, Field(ge=0, le=MAX_TOKENS, description="Input (prompt) tokens per request.")
]
OutputTokens = Annotated[
    int, Field(ge=0, le=MAX_TOKENS, description="Output tokens per request.")
]
RequestsPerDay = Annotated[
    int | None,
    Field(
        ge=1,
        le=MAX_REQUESTS_PER_DAY,
        description="Requests per day. Adds daily and 30-day projected totals.",
    ),
]


class ModelCatalog(BaseModel):
    models: list[ModelInfo]


def build_server(service: PricingService) -> MCPServer:
    server = MCPServer(
        name="tokencost",
        title="Token Cost Estimator",
        version=__version__,
        instructions=INSTRUCTIONS,
    )

    @server.tool(annotations=READ_ONLY)
    def list_models() -> ModelCatalog:
        """List supported models with prices in USD per million tokens.

        Includes long-prompt price tiers, the date each price was checked,
        and whether it may be out of date (`stale`).
        """
        return ModelCatalog(models=service.list_models())

    @server.tool(annotations=READ_ONLY)
    def estimate_cost(
        model_id: ModelId,
        input_tokens: InputTokens,
        output_tokens: OutputTokens,
        requests_per_day: RequestsPerDay = None,
    ) -> Estimate:
        """Estimate the USD cost of one request on one model.

        Money values are strings with 6 decimal places.
        """
        try:
            return service.estimate(
                EstimateRequest(
                    model_id=model_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    requests_per_day=requests_per_day,
                )
            )
        except ModelNotFoundError as exc:
            raise _unknown_model(exc) from None

    @server.tool(annotations=READ_ONLY)
    def compare_models(
        input_tokens: InputTokens,
        output_tokens: OutputTokens,
        model_ids: Annotated[
            list[str] | None,
            Field(
                min_length=1,
                max_length=MAX_COMPARE_MODELS,
                description="Models to compare. Omit to compare every model.",
            ),
        ] = None,
        requests_per_day: RequestsPerDay = None,
    ) -> Comparison:
        """Estimate the same usage across models, sorted cheapest first.

        `cheapest_model_ids` lists every model tied for the lowest cost.
        """
        try:
            return service.compare(
                CompareRequest(
                    model_ids=model_ids,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    requests_per_day=requests_per_day,
                )
            )
        except ModelNotFoundError as exc:
            raise _unknown_model(exc) from None

    @server.tool(annotations=READ_ONLY)
    def count_tokens(
        text: Annotated[
            str,
            Field(max_length=MAX_TEXT_CHARS, description="Text to count."),
        ],
    ) -> TokenCountResult:
        """Approximate the number of tokens in text.

        The count comes from a public tokenizer; each model's real count
        differs somewhat. The text is not stored.
        """
        try:
            return tokenizer.count_tokens(text)
        except OSError:
            raise ToolError(
                "The tokenizer is temporarily unavailable. Try again later."
            ) from None

    return server


def _unknown_model(exc: ModelNotFoundError) -> ToolError:
    return ToolError(
        f"Unknown model_id {exc.model_id!r}. Call list_models for valid ids."
    )


# Exercised by tests/mcp/test_stdio.py in a subprocess, which coverage can't see.
def main() -> None:  # pragma: no cover
    """Entry point for `tokencost-mcp`: serve over stdio for local MCP clients."""
    build_server(PricingService.from_settings(Settings())).run("stdio")


if __name__ == "__main__":  # pragma: no cover
    main()
