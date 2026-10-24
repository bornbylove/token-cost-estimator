from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.conftest import TODAY
from tokencost.api.app import create_app
from tokencost.core.config import Settings


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (tmp_path / "assets" / "index-abc123.js").write_text("js", encoding="utf-8")
    (tmp_path / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path.parent / "secret.txt").write_text("secret", encoding="utf-8")
    return tmp_path


@pytest.fixture
def web(settings: Settings, dist: Path) -> TestClient:
    app = create_app(
        settings.model_copy(update={"frontend_dir": dist}), today=lambda: TODAY
    )
    return TestClient(app)


def test_serves_index_at_root(web: TestClient) -> None:
    response = web.get("/")

    assert response.status_code == 200
    assert response.text == "<html>app</html>"
    assert response.headers["cache-control"] == "no-cache"


def test_client_side_routes_fall_back_to_index(web: TestClient) -> None:
    response = web.get("/compare")

    assert response.status_code == 200
    assert response.text == "<html>app</html>"


def test_fingerprinted_assets_are_cached_forever(web: TestClient) -> None:
    response = web.get("/assets/index-abc123.js")

    assert response.text == "js"
    assert "immutable" in response.headers["cache-control"]


def test_other_static_files_are_revalidated(web: TestClient) -> None:
    response = web.get("/favicon.svg")

    assert response.text == "<svg/>"
    assert response.headers["cache-control"] == "no-cache"


def test_api_still_wins_and_unknown_api_paths_stay_json(web: TestClient) -> None:
    assert web.get("/api/v1/models").status_code == 200

    response = web.get("/api/v1/nope")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_path_traversal_serves_index_not_the_file(web: TestClient) -> None:
    response = web.get("/%2e%2e/secret.txt")

    assert "secret" not in response.text


def test_missing_build_fails_fast(settings: Settings, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="frontend build not found"):
        create_app(settings.model_copy(update={"frontend_dir": tmp_path}))


def test_no_frontend_configured_means_no_catch_all(client: TestClient) -> None:
    assert client.get("/compare").status_code == 404
