from fastapi import APIRouter

from tokencost.api.deps import PricingServiceDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """The process is up."""
    return {"status": "healthy"}


@router.get("/ready")
def ready(service: PricingServiceDep) -> dict[str, str | int]:
    """Pricing data is loaded and requests can be served."""
    return {"status": "ready", "models": service.model_count}
