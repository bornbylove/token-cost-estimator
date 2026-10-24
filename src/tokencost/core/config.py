from importlib.resources import files
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_PRICING_FILE = Path(str(files("tokencost.data") / "pricing.yaml"))


class Settings(BaseSettings):
    """Runtime configuration, read from TOKENCOST_* environment variables or .env."""

    model_config = SettingsConfigDict(
        env_prefix="TOKENCOST_",
        env_file=".env",
        extra="ignore",
    )

    cors_origins: list[str] = ["http://localhost:5173"]
    # Host headers accepted by the /mcp endpoint (DNS rebinding protection).
    # Add the public hostname in production, e.g. ["tokencost.example.com"].
    allowed_hosts: list[str] = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    pricing_file: Path = DEFAULT_PRICING_FILE
    # Built web app (frontend/dist) to serve at /. Unset in development, where
    # the Vite dev server serves the app and proxies API calls.
    frontend_dir: Path | None = None
    stale_after_days: int = Field(default=90, ge=1)

    # Abuse protection. Limits are per client IP per process; 0 disables one.
    rate_limit_per_minute: int = Field(default=60, ge=0)
    token_count_rate_limit_per_minute: int = Field(default=10, ge=0)
    # Fits a 1,000,000-character text plus JSON overhead; MCP enforces the same.
    max_body_bytes: int = Field(default=4 * 1024 * 1024, ge=1024)

    # "json" for production log pipelines: one JSON object per line on stdout.
    log_format: Literal["text", "json"] = "text"
    # Load the tokenizer at startup so the first count isn't slow. Containers
    # ship the vocabulary file, so this needs no network there.
    preload_tokenizer: bool = False
