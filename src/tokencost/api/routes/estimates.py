from fastapi import APIRouter

from tokencost.api.deps import PricingServiceDep
from tokencost.api.errors import ERROR_RESPONSES
from tokencost.core.schemas import CompareRequest, Comparison, Estimate, EstimateRequest

router = APIRouter(tags=["estimates"], responses=ERROR_RESPONSES)


@router.post("/estimate")
def estimate_cost(request: EstimateRequest, service: PricingServiceDep) -> Estimate:
    return service.estimate(request)


@router.post("/compare")
def compare_models(request: CompareRequest, service: PricingServiceDep) -> Comparison:
    """Estimate the same usage across models, cheapest first."""
    return service.compare(request)
