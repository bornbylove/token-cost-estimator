from collections.abc import Callable
from datetime import date

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.transport_security import TransportSecuritySettings

from tokencost import __version__
from tokencost.api.errors import register_error_handlers
from tokencost.api.frontend import frontend_router
from tokencost.api.routes import estimates, health, models, tokens
from tokencost.core.config import Settings
from tokencost.core.service import PricingService
from tokencost.mcp.server import build_server


def create_app(
    settings: Settings | None = None,
    *,
    today: Callable[[], date] = date.today,
) -> FastAPI:
    """Build the app. Fails fast if the pricing file is missing or invalid."""
    settings = settings or Settings()
    pricing_service = PricingService.from_settings(settings, today=today)

    mcp_server = build_server(pricing_service)
    # Stateless JSON responses: no per-client sessions to keep, which suits an
    # anonymous public service and scales horizontally.
    mcp_app = mcp_server.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=settings.allowed_hosts,
            allowed_origins=settings.cors_origins,
        ),
    )

    app = FastAPI(
        title="Token Cost Estimator API",
        description="Estimate token costs across AI providers.",
        version=__version__,
        # A mounted app's own lifespan never runs, so start MCP's here.
        lifespan=lambda _: mcp_server.session_manager.run(),
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
    app.router.routes.extend(mcp_app.routes)
    # Last, so its catch-all route never shadows the API.
    if settings.frontend_dir is not None:
        app.include_router(frontend_router(settings.frontend_dir))

    return app
