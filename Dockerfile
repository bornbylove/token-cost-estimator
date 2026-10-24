# syntax=docker/dockerfile:1

# --- Web app: static build served by the API at / ---
FROM node:24.22.1-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json frontend/.npmrc ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Python: locked runtime dependencies in a self-contained venv ---
FROM python:3.14.7-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /src
# Dependencies first, so code changes don't reinstall them.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY src/ ./src/
RUN uv sync --locked --no-dev --no-editable
# Bake in the tokenizer vocabulary so the container never downloads it.
ENV TIKTOKEN_CACHE_DIR=/app/tiktoken
RUN /app/.venv/bin/python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"

# --- Runtime ---
FROM python:3.14.7-slim
RUN useradd --system --uid 10001 --no-create-home app
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/tiktoken /app/tiktoken
COPY --from=web /web/dist /app/web

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    TIKTOKEN_CACHE_DIR=/app/tiktoken \
    TOKENCOST_FRONTEND_DIR=/app/web \
    TOKENCOST_LOG_FORMAT=json \
    TOKENCOST_PRELOAD_TOKENIZER=true \
    TOKENCOST_CORS_ORIGINS=[]
# Set in production:
#   TOKENCOST_ALLOWED_HOSTS    public hostname, e.g. ["tokencost.example.com"];
#                              until set, /mcp only accepts localhost Host headers
#   TOKENCOST_CLIENT_IP_HEADER header your platform's proxy sets to the client IP
#                              (fly-client-ip on Fly.io), for per-client limits

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health', timeout=2)"
# X-Forwarded-For is deliberately not trusted: its first entry is set by the
# client. Real client IPs come from TOKENCOST_CLIENT_IP_HEADER instead.
CMD ["sh", "-c", "exec uvicorn tokencost.api.app:create_app --factory --host 0.0.0.0 --port \"$PORT\" --no-proxy-headers --no-access-log --no-server-header"]
