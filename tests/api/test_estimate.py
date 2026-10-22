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
        "price_tier": "standard",
        "input_cost_usd": "1.500000",
        "output_cost_usd": "0.500000",
        "total_cost_usd": "2.000000",
        "currency": "USD",
        "projection": None,
        "pricing_status": "verified",
        "effective_date": "2026-01-01",
        "valid_until": None,
        "stale": False,
        "notes": None,
    }


def test_estimate_flags_stale_pricing(client: TestClient) -> None:
    response = post_estimate(
        client, model_id="test-old", input_tokens=1, output_tokens=1
    )

    assert response.json()["stale"] is True


def test_estimate_applies_long_context_tier(client: TestClient) -> None:
    response = post_estimate(
        client, model_id="test-model", input_tokens=2_000_001, output_tokens=1_000_000
    )

    body = response.json()
    assert body["price_tier"] == "long_context"
    assert body["input_cost_usd"] == "6.000003"
    assert body["output_cost_usd"] == "6.000000"


def test_estimate_flags_expired_pricing_with_notes(client: TestClient) -> None:
    response = post_estimate(
        client, model_id="test-expired", input_tokens=1, output_tokens=1
    )

    body = response.json()
    assert body["stale"] is True
    assert body["valid_until"] == "2026-02-28"
    assert body["notes"] == "Promo pricing ended."


def test_estimate_with_projection(client: TestClient) -> None:
    response = post_estimate(
        client,
        model_id="test-model",
        input_tokens=1_000,
        output_tokens=500,
        requests_per_day=1_000,
    )

    assert response.json()["projection"] == {
        "requests_per_day": 1_000,
        "days_per_month": 30,
        "daily_cost_usd": "2.000000",
        "monthly_cost_usd": "60.000000",
    }


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
        {
            "model_id": "test-model",
            "input_tokens": 1,
            "output_tokens": 1,
            "requests_per_day": 0,
        },
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
