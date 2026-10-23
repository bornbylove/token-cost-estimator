from collections.abc import Callable
from datetime import date

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tokencost import __version__
from tokencost.api.errors import register_error_handlers
from tokencost.api.routes import estimates, health, models, tokens
from tokencost.core.config import Settings
from tokencost.core.service import PricingService


def create_app(
    settings: Settings | None = None,
    *,
    today: Callable[[], date] = date.today,
) -> FastAPI:
    """Build the app. Fails fast if the pricing file is missing or invalid."""
    settings = settings or Settings()
    pricing_service = PricingService.from_settings(settings, today=today)

    app = FastAPI(
        title="Token Cost Estimator API",
        description="Estimate token costs across AI providers.",
        version=__version__,
    )
    app.state.pricing_service = pricing_service

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    register_error_handlers(app)

    app.include_router(health.router)
    api = APIRouter(prefix="/api/v1")
    api.include_router(models.router)
    api.include_router(estimates.router)
    api.include_router(tokens.router)
    app.include_router(api)

    return app
