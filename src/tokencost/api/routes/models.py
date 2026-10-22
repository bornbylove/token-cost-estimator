from fastapi import APIRouter

from tokencost.api.deps import PricingServiceDep
from tokencost.api.errors import ERROR_RESPONSES
from tokencost.core.schemas import ModelInfo

router = APIRouter(prefix="/models", tags=["models"], responses=ERROR_RESPONSES)


@router.get("")
def list_models(service: PricingServiceDep) -> list[ModelInfo]:
    return service.list_models()


@router.get("/{model_id}")
def get_model(model_id: str, service: PricingServiceDep) -> ModelInfo:
    return service.get_model(model_id)
