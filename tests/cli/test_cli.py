import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner, Result

from tests.conftest import FIXTURE_PRICING, TODAY
from tokencost import __version__
from tokencost.cli import main
from tokencost.core.schemas import MAX_TOKENS


@pytest.fixture(autouse=True)
def fixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOKENCOST_PRICING_FILE", str(FIXTURE_PRICING))
    monkeypatch.setattr(main, "today", lambda: TODAY)


def run(*args: str, stdin: str | None = None) -> Result:
    return CliRunner().invoke(main.app, list(args), input=stdin)


def test_version() -> None:
    result = run("--version")

    assert result.exit_code == 0
    assert result.stdout.strip() == f"tokencost {__version__}"


def test_models_table() -> None:
    result = run("models")

    assert result.exit_code == 0
    for model_id in ("test-model", "test-old", "test-expired"):
        assert model_id in result.stdout
    assert "over 2M input" in result.stdout
    assert "(stale)" in result.stdout
    assert "until 2026-02-28" in result.stdout
    assert "Promo pricing ended." in result.stdout


def test_models_json_matches_api_shape() -> None:
    result = run("models", "--json")

    models = json.loads(result.stdout)
    assert [m["id"] for m in models] == ["test-model", "test-old", "test-expired"]
    assert models[0]["input_price_per_million"] == "1.00"
    assert models[1]["stale"] is True


def test_estimate_with_projection() -> None:
    result = run(
        "estimate", "test-model", "-i", "1k", "-o", "500", "--per-day", "1,000"
    )

    assert result.exit_code == 0
    assert "Test model (TestAI)" in result.stdout
    assert "$0.002" in result.stdout
    assert "$2.00" in result.stdout
    assert "$60.00" in result.stdout
    assert "Prices checked 2026-01-01" in result.stdout
    assert result.stderr == ""


def test_estimate_json() -> None:
    result = run("estimate", "test-model", "-i", "1000", "-o", "500", "--json")

    body = json.loads(result.stdout)
    assert body["total_cost_usd"] == "0.002000"
    assert body["projection"] is None


def test_estimate_long_prompt_pricing() -> None:
    result = run("estimate", "test-model", "-i", "2000001", "-o", "0")

    assert "Long-prompt pricing applies" in result.stdout


def test_estimate_warns_about_stale_prices_on_stderr() -> None:
    result = run("estimate", "test-expired", "-i", "1", "-o", "1")

    assert result.exit_code == 0
    assert "Promo pricing ended." in result.stdout
    assert "prices may be out of date for test-expired" in result.stderr


def test_estimate_unknown_model() -> None:
    result = run("estimate", "nope", "-i", "1", "-o", "1")

    assert result.exit_code == 1
    assert "Unknown model 'nope'" in result.stderr


def test_estimate_rejects_out_of_range_values_by_option_name() -> None:
    result = run("estimate", "test-model", "-i", str(MAX_TOKENS + 1), "-o", "1")

    assert result.exit_code == 2
    assert "--input: Input should be less than or equal to" in result.stderr


def test_estimate_rejects_unparseable_numbers() -> None:
    result = run("estimate", "test-model", "-i", "lots", "-o", "1")

    assert result.exit_code == 2
    assert "'lots' is not a number" in result.output


def test_compare_all_models_cheapest_first() -> None:
    result = run("compare", "-i", "1M", "-o", "1M", "-d", "10")

    assert result.exit_code == 0
    lines = result.stdout.splitlines()
    rows = [line for line in lines if line.startswith("│")]
    assert [row.split()[1] for row in rows] == [
        "test-expired",
        "test-old",
        "test-model",
    ]
    assert "Per month" in result.stdout
    assert "Cheapest: test-expired" in result.stdout


def test_compare_selected_models_with_tie_and_long_prompt_marker() -> None:
    result = run("compare", "test-model", "test-old", "-i", "2000001", "-o", "0")

    assert "* long-prompt pricing applies" in result.stdout
    assert "Per month" not in result.stdout


def test_compare_reports_ties() -> None:
    result = run("compare", "test-model", "test-old", "-i", "0", "-o", "0")

    assert "Cheapest: test-model, test-old" in result.stdout


def test_compare_json() -> None:
    result = run("compare", "test-old", "-i", "1", "-o", "1", "--json")

    assert json.loads(result.stdout)["cheapest_model_ids"] == ["test-old"]


def test_compare_unknown_model() -> None:
    result = run("compare", "test-model", "nope", "-i", "1", "-o", "1")

    assert result.exit_code == 1
    assert "Unknown model 'nope'" in result.stderr


def test_count_from_stdin() -> None:
    result = run("count", stdin="Hello world")

    assert result.exit_code == 0
    assert "2 tokens (approximate, o200k_base)" in result.stdout
    assert "11 characters" in result.stdout


def test_count_from_file_as_json(tmp_path: Path) -> None:
    path = tmp_path / "prompt.txt"
    path.write_text("Hello world", encoding="utf-8")

    result = run("count", str(path), "--json")

    assert json.loads(result.stdout)["tokens"] == 2


def test_count_dash_reads_stdin() -> None:
    assert run("count", "-", stdin="Hello world").exit_code == 0


def test_count_missing_file() -> None:
    result = run("count", "does-not-exist.txt")

    assert result.exit_code == 1
    assert "Cannot read does-not-exist.txt" in result.stderr


def test_count_rejects_binary_file(tmp_path: Path) -> None:
    path = tmp_path / "image.bin"
    path.write_bytes(b"\xff\xfe\x00")

    result = run("count", str(path))

    assert result.exit_code == 1
    assert "is not UTF-8 text" in result.stderr


def test_count_without_input_on_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    terminal = SimpleNamespace(stdin=SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(main, "sys", terminal)

    result = run("count")

    assert result.exit_code == 1
    assert "pipe text in" in result.stderr


def test_count_explains_tokenizer_download_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def offline(_: str) -> None:
        raise OSError("network unreachable")

    monkeypatch.setattr(main, "count_tokens", offline)

    result = run("count", stdin="Hello")

    assert result.exit_code == 1
    assert "downloaded once on first use" in result.stderr


def test_invalid_pricing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad = tmp_path / "pricing.yaml"
    bad.write_text("models: []", encoding="utf-8")
    monkeypatch.setenv("TOKENCOST_PRICING_FILE", str(bad))

    result = run("models")

    assert result.exit_code == 1
    assert "invalid pricing file" in result.stderr
