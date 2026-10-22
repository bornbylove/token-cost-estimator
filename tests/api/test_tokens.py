from fastapi.testclient import TestClient

from tokencost.core.schemas import MAX_TEXT_CHARS


def test_count_tokens(client: TestClient) -> None:
    response = client.post("/api/v1/tokens/count", json={"text": "Hello world"})

    assert response.status_code == 200
    body = response.json()
    assert body["characters"] == 11
    assert body["tokens"] == 2
    assert body["method"] == "approximate"
    assert "Approximate" in body["note"]


def test_rejects_oversized_text_without_echoing_it(client: TestClient) -> None:
    secret = "s3cr3t-" + "x" * MAX_TEXT_CHARS

    response = client.post("/api/v1/tokens/count", json={"text": secret})

    assert response.status_code == 422
    assert "s3cr3t" not in response.text


def test_requires_text(client: TestClient) -> None:
    response = client.post("/api/v1/tokens/count", json={})

    assert response.status_code == 422
