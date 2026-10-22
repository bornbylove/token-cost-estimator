from typing import Any

import pytest
from fastapi.testclient import TestClient

from tokencost.core.schemas import MAX_TOKENS


def post_estimate(client: TestClient, **body: Any) -> Any:
    return client.post("/api/v1/estimate", json=body)


def test_estimate(client: TestClient) -> None:
    response = post_estimate(
        client, model_id="test-model", input_tokens=1_500_000, output_tokens=250_000
    )

    assert response.status_code == 200
    assert response.json() == {
        "model_id": "test-model",
        "provider": "TestAI",
        "model_name": "Test model",
        "input_tokens": 1_500_000,
        "output_tokens": 250_000,
        "input_cost_usd": "1.500000",
        "output_cost_usd": "0.500000",
        "total_cost_usd": "2.000000",
        "currency": "USD",
        "pricing_status": "verified",
        "effective_date": "2026-01-01",
        "stale": False,
    }


def test_estimate_flags_stale_pricing(client: TestClient) -> None:
    response = post_estimate(
        client, model_id="test-old", input_tokens=1, output_tokens=1
    )

    assert response.json()["stale"] is True


def test_estimate_unknown_model(client: TestClient) -> None:
    response = post_estimate(client, model_id="nope", input_tokens=1, output_tokens=1)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "model_not_found"


@pytest.mark.parametrize(
    "body",
    [
        {"model_id": "test-model", "input_tokens": -1, "output_tokens": 0},
        {"model_id": "test-model", "input_tokens": MAX_TOKENS + 1, "output_tokens": 0},
        {"model_id": "test-model", "input_tokens": 1},
        {"model_id": "test-model", "input_tokens": 1, "output_tokens": 1, "typo": 1},
    ],
)
def test_estimate_validation_errors(client: TestClient, body: dict[str, Any]) -> None:
    response = post_estimate(client, **body)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]
    assert all("input" not in detail for detail in error["details"])


def test_old_unversioned_routes_are_gone(client: TestClient) -> None:
    assert client.get("/api/models").status_code == 404
