import json
import logging
import sys
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import TODAY
from tokencost.api.app import create_app
from tokencost.api.logs import JsonFormatter, configure_json_logging
from tokencost.api.middleware import RateLimit, RateLimitMiddleware
from tokencost.core import tokenizer
from tokencost.core.config import Settings

ESTIMATE = {"model_id": "test-model", "input_tokens": 1, "output_tokens": 1}


def make_client(settings: Settings, **overrides: Any) -> TestClient:
    return TestClient(
        create_app(settings.model_copy(update=overrides), today=lambda: TODAY)
    )


# --- request IDs, security headers, access log ---


def test_every_response_gets_a_request_id(client: TestClient) -> None:
    first = client.get("/health").headers["x-request-id"]
    second = client.get("/health").headers["x-request-id"]

    assert len(first) == 32
    assert first != second


def test_a_valid_incoming_request_id_is_kept(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "edge-abc.123"})

    assert response.headers["x-request-id"] == "edge-abc.123"


def test_an_unsafe_incoming_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "bad id\r\nX-Evil: 1"})

    assert response.headers["x-request-id"] != "bad id\r\nX-Evil: 1"
    assert len(response.headers["x-request-id"]) == 32


def test_security_headers(client: TestClient) -> None:
    headers = client.get("/api/v1/models").headers

    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert "default-src 'self'" in headers["content-security-policy"]


def test_docs_page_has_no_csp_so_swagger_ui_loads(client: TestClient) -> None:
    headers = client.get("/docs").headers

    assert "content-security-policy" not in headers
    assert headers["x-content-type-options"] == "nosniff"


def test_error_responses_carry_headers_too(client: TestClient) -> None:
    response = client.post("/api/v1/estimate", json={**ESTIMATE, "model_id": "nope"})

    assert response.status_code == 404
    assert "x-request-id" in response.headers


def test_access_log_records_request_without_body_or_query(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="tokencost.access"):
        client.post("/api/v1/tokens/count?secret=q", json={"text": "my private prompt"})

    (record,) = [r for r in caplog.records if r.name == "tokencost.access"]
    assert record.getMessage() == "POST /api/v1/tokens/count 200"
    assert record.__dict__["status"] == 200
    assert record.__dict__["path"] == "/api/v1/tokens/count"
    assert isinstance(record.__dict__["duration_ms"], float)
    assert "private" not in caplog.text
    assert "secret" not in caplog.text


# --- body size ---


def test_rejects_declared_oversized_body(settings: Settings) -> None:
    client = make_client(settings, max_body_bytes=1024)

    response = client.post(
        "/api/v1/tokens/count",
        content=json.dumps({"text": "x" * 2000}),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "content_too_large"


def test_rejects_oversized_streamed_body(settings: Settings) -> None:
    client = make_client(settings, max_body_bytes=1024)

    def chunks() -> Iterator[bytes]:
        yield b'{"text": "'
        for _ in range(10):
            yield b"x" * 200
        yield b'"}'

    # A generator body is sent chunked, with no Content-Length to check.
    response = client.post(
        "/api/v1/tokens/count",
        content=chunks(),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "content_too_large"


def test_accepts_body_under_the_limit(settings: Settings) -> None:
    client = make_client(settings, max_body_bytes=1024)

    assert client.post("/api/v1/estimate", json=ESTIMATE).status_code == 200


# --- rate limiting ---


def test_rate_limits_api_per_client(settings: Settings) -> None:
    client = make_client(settings, rate_limit_per_minute=3)

    statuses = [
        client.post("/api/v1/estimate", json=ESTIMATE).status_code for _ in range(4)
    ]

    assert statuses == [200, 200, 200, 429]
    limited = client.get("/api/v1/models")
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert int(limited.headers["retry-after"]) >= 1
    assert "x-request-id" in limited.headers


def test_token_counting_has_its_own_stricter_limit(settings: Settings) -> None:
    client = make_client(
        settings, rate_limit_per_minute=100, token_count_rate_limit_per_minute=2
    )
    count = {"text": "hi"}

    statuses = [
        client.post("/api/v1/tokens/count", json=count).status_code for _ in range(3)
    ]

    assert statuses == [200, 200, 429]
    assert client.get("/api/v1/models").status_code == 200


def test_health_checks_and_preflights_are_never_limited(settings: Settings) -> None:
    client = make_client(settings, rate_limit_per_minute=1)
    client.get("/api/v1/models")

    assert all(client.get("/health").status_code == 200 for _ in range(5))
    preflight = client.options(
        "/api/v1/models",
        headers={
            "Origin": "http://allowed.test",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert preflight.status_code == 200


def test_zero_disables_a_limit(settings: Settings) -> None:
    client = make_client(settings, rate_limit_per_minute=0)

    assert all(client.get("/api/v1/models").status_code == 200 for _ in range(100))


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_bucket_refills_over_time() -> None:
    clock = FakeClock()
    limiter = RateLimitMiddleware(app=None, rules=[RateLimit("/", 60)], clock=clock)  # type: ignore[arg-type]
    rule = limiter.rules[0]

    for _ in range(60):
        assert limiter._take(rule, "1.2.3.4") is None
    assert limiter._take(rule, "1.2.3.4") == 1
    assert limiter._take(rule, "5.6.7.8") is None  # other clients unaffected

    clock.now += 1.0  # 60/min refills one token per second
    assert limiter._take(rule, "1.2.3.4") is None
    assert limiter._take(rule, "1.2.3.4") == 1


def test_idle_clients_are_forgotten(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FakeClock()
    limiter = RateLimitMiddleware(app=None, rules=[RateLimit("/", 60)], clock=clock)  # type: ignore[arg-type]
    monkeypatch.setattr(RateLimitMiddleware, "MAX_TRACKED", 2)
    rule = limiter.rules[0]

    limiter._take(rule, "a")
    limiter._take(rule, "b")
    clock.now += 120  # both buckets refill completely
    limiter._take(rule, "c")

    assert set(limiter._buckets) == {("/", "c")}


# --- logging and startup ---


def test_json_formatter_includes_extra_fields() -> None:
    record = logging.makeLogRecord(
        {"name": "tokencost.access", "msg": "GET / 200", "levelname": "INFO"}
    )
    record.request_id = "abc"
    record.color_message = "\x1b[36mGET\x1b[0m"

    line = json.loads(JsonFormatter().format(record))

    assert "color_message" not in line

    assert line["message"] == "GET / 200"
    assert line["level"] == "info"
    assert line["request_id"] == "abc"
    assert "time" in line


def test_json_formatter_includes_exceptions() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.getLogger("t").makeRecord(
            "t",
            logging.ERROR,
            __file__,
            1,
            "failed",
            (),
            exc_info=sys.exc_info(),
        )

    assert "ValueError: boom" in json.loads(JsonFormatter().format(record))["exception"]


def test_configure_json_logging_routes_uvicorn_through_one_handler() -> None:
    root = logging.getLogger()
    saved = (root.handlers[:], root.level)
    try:
        configure_json_logging()

        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0].formatter, JsonFormatter)
        assert logging.getLogger("uvicorn.error").propagate is True
        assert logging.getLogger("uvicorn.access").hasHandlers() is False
    finally:
        root.handlers, root.level = saved


def test_json_log_format_setting_configures_logging(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[bool] = []
    monkeypatch.setattr(
        "tokencost.api.app.configure_json_logging", lambda: calls.append(True)
    )

    make_client(settings, log_format="json")

    assert calls == [True]


def test_preload_tokenizer_at_startup(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(tokenizer, "count_tokens", lambda text: calls.append(text))

    with make_client(settings, preload_tokenizer=True):
        pass

    assert calls == [""]


def test_preload_failure_does_not_stop_startup(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def offline(_: str) -> None:
        raise OSError("no network")

    monkeypatch.setattr(tokenizer, "count_tokens", offline)

    with make_client(settings, preload_tokenizer=True) as client:
        assert client.get("/health").status_code == 200

    assert "tokenizer preload failed" in caplog.text
