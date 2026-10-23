"""Use cases shared by every interface (REST API, MCP, CLI)."""

from collections.abc import Callable
from datetime import date
from typing import Self

from tokencost.core import pricing
from tokencost.core.config import Settings
from tokencost.core.repository import PricingRepository
from tokencost.core.schemas import (
    CompareRequest,
    Comparison,
    Estimate,
    EstimateRequest,
    ModelInfo,
    ModelPrice,
)


class ModelNotFoundError(LookupError):
    def __init__(self, model_id: str) -> None:
        super().__init__(f"Unknown model_id {model_id!r}. List available models first.")
        self.model_id = model_id


class PricingService:
    def __init__(
        self,
        repository: PricingRepository,
        *,
        stale_after_days: int,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._repository = repository
        self._stale_after_days = stale_after_days
        self._today = today

    @classmethod
    def from_settings(
        cls, settings: Settings, *, today: Callable[[], date] = date.today
    ) -> Self:
        """Load pricing from the configured file. Raises PricingDataError."""
        repository = PricingRepository.from_yaml(settings.pricing_file)
        return cls(repository, stale_after_days=settings.stale_after_days, today=today)

    @property
    def model_count(self) -> int:
        return len(self._repository)

    def list_models(self) -> list[ModelInfo]:
        return [self._info(model) for model in self._repository.all()]

    def get_model(self, model_id: str) -> ModelInfo:
        return self._info(self._require(model_id))

    def estimate(self, request: EstimateRequest) -> Estimate:
        return self._estimate(self._require(request.model_id), request)

    def compare(self, request: CompareRequest) -> Comparison:
        if request.model_ids is None:
            models = self._repository.all()
        else:
            # Look up every id first, so one unknown id fails the whole request.
            unique_ids = dict.fromkeys(request.model_ids)
            models = [self._require(model_id) for model_id in unique_ids]

        estimates = sorted(
            (self._estimate(model, request) for model in models),
            key=lambda e: (e.total_cost_usd, e.model_id),
        )
        lowest = estimates[0].total_cost_usd
        return Comparison(
            estimates=estimates,
            cheapest_model_ids=[
                e.model_id for e in estimates if e.total_cost_usd == lowest
            ],
        )

    def _estimate(
        self, model: ModelPrice, usage: EstimateRequest | CompareRequest
    ) -> Estimate:
        return pricing.estimate(
            model,
            usage.input_tokens,
            usage.output_tokens,
            today=self._today(),
            stale_after_days=self._stale_after_days,
            requests_per_day=usage.requests_per_day,
        )

    def _require(self, model_id: str) -> ModelPrice:
        model = self._repository.get(model_id)
        if model is None:
            raise ModelNotFoundError(model_id)
        return model

    def _info(self, model: ModelPrice) -> ModelInfo:
        stale = pricing.is_stale(
            model, today=self._today(), stale_after_days=self._stale_after_days
        )
        return ModelInfo(**model.model_dump(), stale=stale)
