from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_ready_reports_loaded_models(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "models": 2}


def test_unexpected_errors_use_envelope_without_leaking_details(
    client: TestClient,
) -> None:
    def boom() -> None:
        raise RuntimeError("secret internals")

    client.app.add_api_route("/boom", boom)  # type: ignore[attr-defined]
    safe_client = TestClient(client.app, raise_server_exceptions=False)

    response = safe_client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "An unexpected error occurred."}
    }
