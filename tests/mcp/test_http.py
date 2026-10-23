"""The MCP endpoint served by the web app at /mcp (Streamable HTTP)."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import TODAY
from tokencost.api.app import create_app
from tokencost.core.config import Settings

HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


@pytest.fixture
def http(settings: Settings) -> Iterator[TestClient]:
    app = create_app(
        settings.model_copy(update={"allowed_hosts": ["testserver"]}),
        today=lambda: TODAY,
    )
    # Entering the client runs the app lifespan, which starts the MCP manager.
    with TestClient(app) as client:
        yield client


def rpc(http: TestClient, method: str, params: dict[str, Any] | None = None) -> Any:
    response = http.post(
        "/mcp",
        headers=HEADERS,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    return response.json()["result"]


def test_initialize(http: TestClient) -> None:
    result = rpc(
        http,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    )

    assert result["serverInfo"]["name"] == "tokencost"
    assert "tools" in result["capabilities"]


def test_tools_list(http: TestClient) -> None:
    tools = rpc(http, "tools/list")["tools"]

    assert {tool["name"] for tool in tools} == {
        "list_models",
        "estimate_cost",
        "compare_models",
        "count_tokens",
    }


def test_tools_call_without_a_session(http: TestClient) -> None:
    result = rpc(
        http,
        "tools/call",
        {
            "name": "estimate_cost",
            "arguments": {
                "model_id": "test-model",
                "input_tokens": 1_000_000,
                "output_tokens": 0,
            },
        },
    )

    assert result["isError"] is False
    assert result["structuredContent"]["total_cost_usd"] == "1.000000"


def test_rejects_unexpected_host_header(http: TestClient) -> None:
    response = http.post(
        "/mcp",
        headers={**HEADERS, "Host": "attacker.example"},
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )

    assert response.status_code == 421


def test_rest_api_still_served_alongside_mcp(http: TestClient) -> None:
    assert http.get("/api/v1/models").status_code == 200
