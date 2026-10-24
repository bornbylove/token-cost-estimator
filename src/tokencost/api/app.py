import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import date

import anyio
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.transport_security import TransportSecuritySettings

from tokencost import __version__
from tokencost.api.errors import register_error_handlers
from tokencost.api.frontend import frontend_router
from tokencost.api.logs import configure_json_logging
from tokencost.api.middleware import (
    BodySizeLimitMiddleware,
    RateLimit,
    RateLimitMiddleware,
    RequestContextMiddleware,
)
from tokencost.api.routes import estimates, health, models, tokens
from tokencost.core import tokenizer
from tokencost.core.config import Settings
from tokencost.core.service import PricingService
from tokencost.mcp.server import build_server

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    today: Callable[[], date] = date.today,
) -> FastAPI:
    """Build the app. Fails fast if the pricing file is missing or invalid."""
    settings = settings or Settings()
    if settings.log_format == "json":
        configure_json_logging()
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

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if settings.preload_tokenizer:
            await anyio.to_thread.run_sync(_preload_tokenizer)
        # A mounted app's own lifespan never runs, so start MCP's here.
        async with mcp_server.session_manager.run():
            yield

    app = FastAPI(
        title="Token Cost Estimator API",
        description="Estimate token costs across AI providers.",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.pricing_service = pricing_service

    # Each add_middleware wraps the previous, so the last added runs first:
    # request context -> rate limit -> body size -> CORS -> app.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes)
    app.add_middleware(
        RateLimitMiddleware,
        rules=[
            RateLimit(
                "/api/v1/tokens/count", settings.token_count_rate_limit_per_minute
            ),
            RateLimit("/api/", settings.rate_limit_per_minute),
            RateLimit("/mcp", settings.rate_limit_per_minute),
        ],
    )
    app.add_middleware(
        RequestContextMiddleware, client_ip_header=settings.client_ip_header
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


def _preload_tokenizer() -> None:
    try:
        tokenizer.count_tokens("")
    except OSError:
        # Counting retries on first use; everything else still works.
        logger.warning("tokenizer preload failed", exc_info=True)
