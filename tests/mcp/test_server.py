from typing import Any

import pytest
from mcp import Client

from tests.conftest import FIXTURE_PRICING, TODAY
from tokencost.core import tokenizer
from tokencost.core.config import Settings
from tokencost.core.service import PricingService
from tokencost.mcp.server import build_server

pytestmark = pytest.mark.anyio

TOOL_NAMES = {"list_models", "estimate_cost", "compare_models", "count_tokens"}


@pytest.fixture
def client() -> Client:
    service = PricingService.from_settings(
        Settings(pricing_file=FIXTURE_PRICING), today=lambda: TODAY
    )
    return Client(build_server(service))


async def call(client: Client, tool: str, **arguments: Any) -> Any:
    async with client:
        return await client.call_tool(tool, arguments)


async def test_exposes_four_read_only_tools_with_schemas(client: Client) -> None:
    async with client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    assert set(tools) == TOOL_NAMES
    for tool in tools.values():
        assert tool.description
        assert tool.output_schema is not None
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
    estimate_inputs = tools["estimate_cost"].input_schema
    assert estimate_inputs["required"] == ["model_id", "input_tokens", "output_tokens"]
    assert estimate_inputs["properties"]["input_tokens"]["minimum"] == 0


async def test_server_instructions_mention_estimates(client: Client) -> None:
    async with client:
        instructions = client.instructions
        server_info = client.server_info

    assert server_info is not None
    assert server_info.name == "tokencost"
    assert instructions is not None
    assert "not invoices" in instructions


async def test_list_models(client: Client) -> None:
    result = await call(client, "list_models")

    assert result.is_error is False
    models = result.structured_content["models"]
    assert [m["id"] for m in models] == ["test-model", "test-old", "test-expired"]
    assert models[0]["input_price_per_million"] == "1.00"


async def test_estimate_cost_matches_rest_api_shape(client: Client) -> None:
    result = await call(
        client,
        "estimate_cost",
        model_id="test-model",
        input_tokens=1_000,
        output_tokens=500,
        requests_per_day=1_000,
    )

    body = result.structured_content
    assert body["total_cost_usd"] == "0.002000"
    assert body["projection"]["monthly_cost_usd"] == "60.000000"
    assert body["effective_date"] == "2026-01-01"
    assert body["stale"] is False


async def test_compare_models(client: Client) -> None:
    result = await call(client, "compare_models", input_tokens=0, output_tokens=0)

    body = result.structured_content
    assert len(body["estimates"]) == 3
    assert body["cheapest_model_ids"] == ["test-expired", "test-model", "test-old"]


async def test_compare_selected_models(client: Client) -> None:
    result = await call(
        client,
        "compare_models",
        model_ids=["test-old"],
        input_tokens=1,
        output_tokens=1,
    )

    assert result.structured_content["cheapest_model_ids"] == ["test-old"]


async def test_count_tokens(client: Client) -> None:
    result = await call(client, "count_tokens", text="Hello world")

    assert result.structured_content["tokens"] == 2
    assert result.structured_content["method"] == "approximate"


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("estimate_cost", {"model_id": "nope", "input_tokens": 1, "output_tokens": 1}),
        (
            "compare_models",
            {
                "model_ids": ["test-model", "nope"],
                "input_tokens": 1,
                "output_tokens": 1,
            },
        ),
    ],
)
async def test_unknown_model_points_agent_to_list_models(
    client: Client, tool: str, arguments: dict[str, Any]
) -> None:
    result = await call(client, tool, **arguments)

    assert result.is_error is True
    assert "Call list_models for valid ids" in result.content[0].text


async def test_invalid_arguments_are_reported_as_tool_errors(client: Client) -> None:
    result = await call(
        client, "estimate_cost", model_id="test-model", input_tokens=-1, output_tokens=1
    )

    assert result.is_error is True


async def test_tokenizer_failure_is_a_clean_tool_error(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    def offline(_: str) -> None:
        raise OSError("network unreachable")

    monkeypatch.setattr(tokenizer, "count_tokens", offline)

    result = await call(client, "count_tokens", text="Hello")

    assert result.is_error is True
    assert "temporarily unavailable" in result.content[0].text
    assert "network unreachable" not in result.content[0].text
