"""Use cases shared by every interface (REST API, MCP, CLI)."""

from collections.abc import Callable
from datetime import date

from tokencost.core import pricing
from tokencost.core.repository import PricingRepository
from tokencost.core.schemas import Estimate, EstimateRequest, ModelInfo, ModelPrice


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

    @property
    def model_count(self) -> int:
        return len(self._repository)

    def list_models(self) -> list[ModelInfo]:
        return [self._info(model) for model in self._repository.all()]

    def get_model(self, model_id: str) -> ModelInfo:
        return self._info(self._require(model_id))

    def estimate(self, request: EstimateRequest) -> Estimate:
        return pricing.estimate(
            self._require(request.model_id),
            request.input_tokens,
            request.output_tokens,
            today=self._today(),
            stale_after_days=self._stale_after_days,
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
