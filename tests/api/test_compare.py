from typing import Any

from fastapi.testclient import TestClient


def post_compare(client: TestClient, **body: Any) -> Any:
    return client.post("/api/v1/compare", json=body)


def test_compares_all_models_cheapest_first(client: TestClient) -> None:
    response = post_compare(client, input_tokens=1_000_000, output_tokens=1_000_000)

    assert response.status_code == 200
    body = response.json()
    # test-expired $1.00, test-old $2.00, test-model $3.00
    assert [e["model_id"] for e in body["estimates"]] == [
        "test-expired",
        "test-old",
        "test-model",
    ]
    assert body["cheapest_model_ids"] == ["test-expired"]
    assert [e["total_cost_usd"] for e in body["estimates"]] == [
        "1.000000",
        "2.000000",
        "3.000000",
    ]


def test_compares_selected_models_and_ignores_duplicates(client: TestClient) -> None:
    response = post_compare(
        client,
        model_ids=["test-model", "test-old", "test-model"],
        input_tokens=10,
        output_tokens=10,
    )

    assert [e["model_id"] for e in response.json()["estimates"]] == [
        "test-old",
        "test-model",
    ]


def test_compare_applies_each_models_price_tier(client: TestClient) -> None:
    response = post_compare(
        client,
        model_ids=["test-model", "test-old"],
        input_tokens=2_000_001,
        output_tokens=0,
    )

    tiers = {e["model_id"]: e["price_tier"] for e in response.json()["estimates"]}
    assert tiers == {"test-model": "long_context", "test-old": "standard"}


def test_compare_includes_projection(client: TestClient) -> None:
    response = post_compare(
        client,
        model_ids=["test-old"],
        input_tokens=1_000,
        output_tokens=1_000,
        requests_per_day=100,
    )

    projection = response.json()["estimates"][0]["projection"]
    assert projection == {
        "requests_per_day": 100,
        "days_per_month": 30,
        "daily_cost_usd": "0.200000",
        "monthly_cost_usd": "6.000000",
    }


def test_compare_reports_every_model_tied_for_cheapest(client: TestClient) -> None:
    response = post_compare(
        client, model_ids=["test-model", "test-old"], input_tokens=0, output_tokens=0
    )

    assert response.json()["cheapest_model_ids"] == ["test-model", "test-old"]


def test_compare_unknown_model_fails_whole_request(client: TestClient) -> None:
    response = post_compare(
        client, model_ids=["test-model", "nope"], input_tokens=1, output_tokens=1
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "model_not_found"


def test_compare_rejects_empty_model_list(client: TestClient) -> None:
    response = post_compare(client, model_ids=[], input_tokens=1, output_tokens=1)

    assert response.status_code == 422
