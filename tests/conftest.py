from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tokencost.api.app import create_app
from tokencost.core.config import Settings

FIXTURE_PRICING = Path(__file__).parent / "fixtures" / "pricing.yaml"

# Fixed "today": test-model (2026-01-01) is fresh, test-old (2025-01-01) is stale.
TODAY = date(2026, 3, 1)


@pytest.fixture
def settings() -> Settings:
    return Settings(pricing_file=FIXTURE_PRICING, cors_origins=["http://allowed.test"])


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings, today=lambda: TODAY))
