from fastapi.testclient import TestClient


def test_list_models(client: TestClient) -> None:
    response = client.get("/api/v1/models")

    assert response.status_code == 200
    models = {m["id"]: m for m in response.json()}
    assert set(models) == {"test-model", "test-old", "test-expired"}
    assert models["test-model"] == {
        "id": "test-model",
        "provider": "TestAI",
        "name": "Test model",
        "input_price_per_million": "1.00",
        "output_price_per_million": "2.00",
        "long_context": {
            "above_input_tokens": 2_000_000,
            "input_price_per_million": "3.00",
            "output_price_per_million": "6.00",
        },
        "pricing_status": "verified",
        "effective_date": "2026-01-01",
        "valid_until": None,
        "source_url": "https://example.com/pricing",
        "notes": None,
        "stale": False,
    }
    assert models["test-old"]["stale"] is True
    assert models["test-expired"]["stale"] is True


def test_get_model(client: TestClient) -> None:
    response = client.get("/api/v1/models/test-old")

    assert response.status_code == 200
    assert response.json()["name"] == "Old test model"


def test_get_unknown_model_returns_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/models/nope")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "model_not_found",
            "message": "Unknown model_id 'nope'. List available models first.",
        }
    }


def test_unknown_route_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/nothing-here")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_cors_allows_configured_origin_only(client: TestClient) -> None:
    allowed = client.get("/api/v1/models", headers={"Origin": "http://allowed.test"})
    denied = client.get("/api/v1/models", headers={"Origin": "http://evil.test"})

    assert allowed.headers["access-control-allow-origin"] == "http://allowed.test"
    assert "access-control-allow-origin" not in denied.headers
