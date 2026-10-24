"""ASGI middleware for running as a public service.

Pure ASGI rather than BaseHTTPMiddleware, so request bodies can be metered as
they stream in and nothing is buffered.
"""

import ipaddress
import logging
import math
import re
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from tokencost.api.errors import error_response

access_log = logging.getLogger("tokencost.access")

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

# The web app only loads its own bundled assets and calls its own API.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; "
    "frame-ancestors 'none'"
)
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    # Ignored by browsers over plain HTTP, so safe to send everywhere.
    "Strict-Transport-Security": "max-age=63072000",
}
# FastAPI's interactive docs load Swagger UI / ReDoc from a CDN.
_NO_CSP_PREFIXES = ("/docs", "/redoc")


class RequestContextMiddleware:
    """Request IDs, security headers, client IP, and one access log line.

    `client_ip_header` names a header the hosting platform's proxy sets to the
    real client IP (e.g. Fly-Client-IP). Never use a header clients can set
    themselves, such as X-Forwarded-For, whose first entry is client-supplied.
    """

    def __init__(self, app: ASGIApp, client_ip_header: str | None = None) -> None:
        self.app = app
        self.client_ip_header = client_ip_header

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_headers = Headers(scope=scope)
        if self.client_ip_header:
            ip = _valid_ip(request_headers.get(self.client_ip_header, ""))
            if ip is not None:
                # Everything downstream (rate limits, logs) sees the real client.
                scope = {**scope, "client": (ip, 0)}

        incoming = request_headers.get("x-request-id", "")
        request_id = incoming if _REQUEST_ID.match(incoming) else uuid.uuid4().hex
        path: str = scope["path"]
        started = time.perf_counter()
        status = 500

        async def send_with_headers(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                for name, value in SECURITY_HEADERS.items():
                    headers[name] = value
                if not path.startswith(_NO_CSP_PREFIXES):
                    headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            client = scope.get("client")
            # Never log bodies or query strings: they can carry user text.
            access_log.info(
                "%s %s %s",
                scope["method"],
                path,
                status,
                extra={
                    "request_id": request_id,
                    "method": scope["method"],
                    "path": path,
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    "client": client[0] if client else None,
                },
            )


def _valid_ip(value: str) -> str | None:
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


class BodySizeLimitMiddleware:
    """Reject request bodies over `max_bytes` with 413, declared or streamed."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = Headers(scope=scope).get("content-length")
        if (
            declared is not None
            and declared.isdigit()
            and int(declared) > self.max_bytes
        ):
            await self._too_large()(scope, receive, send)
            return

        received = 0

        async def metered_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    # An HTTPException passes through FastAPI's body parsing
                    # (other errors become a generic 400) to the error handler.
                    raise HTTPException(413, self._message())
            return message

        await self.app(scope, metered_receive, send)

    def _message(self) -> str:
        return f"Request body is larger than {self.max_bytes:,} bytes."

    def _too_large(self) -> ASGIApp:
        return error_response(413, "content_too_large", self._message())


@dataclass(frozen=True)
class RateLimit:
    """Allow `per_minute` requests per client IP to paths under `prefix`."""

    prefix: str
    per_minute: int


class RateLimitMiddleware:
    """Per-client-IP token buckets; the first matching rule applies.

    State is in memory, so limits are per process. Behind a proxy, set
    TOKENCOST_CLIENT_IP_HEADER so the client IP is the real one.
    """

    MAX_TRACKED = 10_000

    def __init__(
        self,
        app: ASGIApp,
        rules: Sequence[RateLimit],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.app = app
        self.rules = [r for r in rules if r.per_minute > 0]
        self.clock = clock
        # (rule prefix, client ip) -> (tokens left, last refill time)
        self._buckets: dict[tuple[str, str], tuple[float, float]] = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        rule = self._rule_for(scope)
        if rule is None:
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        retry_after = self._take(rule, client[0] if client else "unknown")
        if retry_after is None:
            await self.app(scope, receive, send)
            return

        response = error_response(
            429,
            "rate_limited",
            f"Too many requests. Try again in {retry_after} seconds.",
        )
        response.headers["Retry-After"] = str(retry_after)
        await response(scope, receive, send)

    def _rule_for(self, scope: Scope) -> RateLimit | None:
        # Never limit CORS preflights; they carry no work.
        if scope["type"] != "http" or scope["method"] == "OPTIONS":
            return None
        path: str = scope["path"]
        return next((r for r in self.rules if path.startswith(r.prefix)), None)

    def _take(self, rule: RateLimit, client: str) -> int | None:
        """Spend one token. None if allowed, else seconds until one refills."""
        now = self.clock()
        rate = rule.per_minute / 60
        key = (rule.prefix, client)
        tokens, last = self._buckets.get(key, (float(rule.per_minute), now))
        tokens = min(float(rule.per_minute), tokens + (now - last) * rate)

        if tokens >= 1:
            self._buckets[key] = (tokens - 1, now)
            self._prune(now)
            return None
        self._buckets[key] = (tokens, now)
        return max(1, math.ceil((1 - tokens) / rate))

    def _prune(self, now: float) -> None:
        """Forget clients whose buckets have refilled, so memory stays bounded."""
        if len(self._buckets) <= self.MAX_TRACKED:
            return
        limits = {r.prefix: r.per_minute for r in self.rules}
        self._buckets = {
            key: (tokens, last)
            for key, (tokens, last) in self._buckets.items()
            if tokens + (now - last) * limits[key[0]] / 60 < limits[key[0]]
        }
