"""Serve the built web app (frontend/dist) from the same origin as the API."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

# Paths owned by the backend. They must 404 as JSON, never fall back to the app.
_BACKEND_PREFIXES = ("api/", "mcp", "health", "ready", "docs", "redoc", "openapi")


def frontend_router(dist: Path) -> APIRouter:
    """Static files from `dist`, with index.html for client-side routes."""
    root = dist.resolve()
    index = root / "index.html"
    if not index.is_file():
        raise RuntimeError(f"frontend build not found: {index} is missing")

    router = APIRouter(include_in_schema=False)

    @router.get("/{path:path}")
    def serve(path: str) -> FileResponse:
        if path.startswith(_BACKEND_PREFIXES):
            raise HTTPException(status_code=404)

        candidate = (root / path).resolve()
        if candidate.is_file() and candidate.is_relative_to(root):
            # Vite fingerprints asset names, so they can be cached forever.
            immutable = candidate.parent == root / "assets"
            headers = (
                {"Cache-Control": "public, max-age=31536000, immutable"}
                if immutable
                else {"Cache-Control": "no-cache"}
            )
            return FileResponse(candidate, headers=headers)

        # Anything else is a client-side route such as /compare.
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return router
