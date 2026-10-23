"""End to end: launch the stdio server as a subprocess, as Claude Code would."""

import os
import sys

import pytest
from mcp import Client, StdioServerParameters

from tests.conftest import FIXTURE_PRICING

pytestmark = pytest.mark.anyio


async def test_stdio_server_round_trip() -> None:
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "tokencost.mcp.server"],
        env={**os.environ, "TOKENCOST_PRICING_FILE": str(FIXTURE_PRICING)},
    )

    async with Client(server) as client:
        tools = await client.list_tools()
        result = await client.call_tool(
            "estimate_cost",
            {"model_id": "test-model", "input_tokens": 1_000, "output_tokens": 500},
        )

    assert len(tools.tools) == 4
    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["total_cost_usd"] == "0.002000"
