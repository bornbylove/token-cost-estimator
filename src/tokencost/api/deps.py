from typing import Annotated

from fastapi import Depends, Request

from tokencost.core.service import PricingService


def get_pricing_service(request: Request) -> PricingService:
    service: PricingService = request.app.state.pricing_service
    return service


PricingServiceDep = Annotated[PricingService, Depends(get_pricing_service)]
