from importlib.resources import files
from pathlib import Path

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
    stale_after_days: int = Field(default=90, ge=1)
