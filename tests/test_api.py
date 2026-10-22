from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_models_serializes_prices_as_strings() -> None:
    response = client.get("/api/models")

    assert response.status_code == 200
    models = response.json()
    assert {m["id"] for m in models} == {
        "openai-example",
        "anthropic-example",
        "google-example",
    }
    assert all(isinstance(m["input_price_per_million"], str) for m in models)


def test_estimate_cost() -> None:
    response = client.post(
        "/api/estimate",
        json={
            "model_id": "anthropic-example",
            "input_tokens": 1_000_000,
            "output_tokens": 500_000,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["input_cost_usd"]) == Decimal("0.80")
    assert Decimal(body["output_cost_usd"]) == Decimal("2.00")
    assert Decimal(body["total_cost_usd"]) == Decimal("2.80")
    assert body["pricing_status"] == "illustrative"


def test_estimate_zero_tokens_costs_nothing() -> None:
    response = client.post(
        "/api/estimate",
        json={"model_id": "openai-example", "input_tokens": 0, "output_tokens": 0},
    )

    assert response.status_code == 200
    assert Decimal(response.json()["total_cost_usd"]) == 0


def test_estimate_unknown_model_returns_404() -> None:
    response = client.post(
        "/api/estimate",
        json={"model_id": "nope", "input_tokens": 1, "output_tokens": 1},
    )

    assert response.status_code == 404


def test_estimate_rejects_negative_tokens() -> None:
    response = client.post(
        "/api/estimate",
        json={"model_id": "openai-example", "input_tokens": -1, "output_tokens": 0},
    )

    assert response.status_code == 422
