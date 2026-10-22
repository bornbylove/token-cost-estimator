from pathlib import Path

import pytest

from tokencost.core.config import DEFAULT_PRICING_FILE
from tokencost.core.repository import PricingDataError, PricingRepository

VALID_ENTRY = """
  - id: {id}
    provider: P
    name: M
    input_price_per_million: "1.00"
    output_price_per_million: "2.00"
    pricing_status: illustrative
    effective_date: 2026-01-01
"""


def write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "pricing.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_shipped_pricing_file_is_valid() -> None:
    repository = PricingRepository.from_yaml(DEFAULT_PRICING_FILE)

    assert len(repository) > 0


def test_loads_and_looks_up_models(tmp_path: Path) -> None:
    path = write(
        tmp_path, "models:" + VALID_ENTRY.format(id="a") + VALID_ENTRY.format(id="b")
    )

    repository = PricingRepository.from_yaml(path)

    assert [m.id for m in repository.all()] == ["a", "b"]
    assert repository.get("a") is not None
    assert repository.get("missing") is None


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(PricingDataError, match="cannot read"):
        PricingRepository.from_yaml(tmp_path / "nope.yaml")


@pytest.mark.parametrize(
    ("content", "error"),
    [
        ("models: []", "at least 1 item"),
        ("models:" + VALID_ENTRY.format(id="a") * 2, "duplicate model id: a"),
        (
            "models:" + VALID_ENTRY.format(id="a").replace('"1.00"', "1.00"),
            "quoted strings",
        ),
        (
            "models:" + VALID_ENTRY.format(id="a").replace("illustrative", "verified"),
            "source_url",
        ),
        ("models:" + VALID_ENTRY.format(id="Bad ID"), "pattern"),
        ("models:\n  - [unclosed", "cannot read"),
    ],
)
def test_rejects_invalid_files(tmp_path: Path, content: str, error: str) -> None:
    with pytest.raises(PricingDataError, match=error):
        PricingRepository.from_yaml(write(tmp_path, content))
