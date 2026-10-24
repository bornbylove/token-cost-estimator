# Deploying

The app ships as one container: the REST API, the MCP endpoint at `/mcp`, and
the web app at `/`, all on one origin. It needs no database, no secrets, and
no outbound network access at runtime.

```sh
docker build -t tokencost .
docker run -p 8000:8000 tokencost          # or: docker compose up --build
```

## Required configuration

| Variable | Value | Why |
| --- | --- | --- |
| `TOKENCOST_ALLOWED_HOSTS` | `["tokencost.example.com"]` | `/mcp` rejects any other `Host` header (DNS rebinding protection). Until this is set, remote MCP clients get `421`. |
| `TOKENCOST_CLIENT_IP_HEADER` | `fly-client-ip` on Fly.io | A header **your platform's proxy sets** to the real client IP. Rate limits are per client IP; without this, every request appears to come from the proxy and all users share one limit. Never use `X-Forwarded-For`: its first entry comes from the client, so anyone could dodge the limits. |

Everything else has production defaults baked into the image:

| Variable | Image default | Notes |
| --- | --- | --- |
| `PORT` | `8000` | Most platforms set this for you. |
| `TOKENCOST_LOG_FORMAT` | `json` | One JSON object per line on stdout. |
| `TOKENCOST_RATE_LIMIT_PER_MINUTE` | `60` | Per client IP for `/api/*` and `/mcp`. `0` disables it. |
| `TOKENCOST_TOKEN_COUNT_RATE_LIMIT_PER_MINUTE` | `10` | Stricter limit for `/api/v1/tokens/count`. |
| `TOKENCOST_MAX_BODY_BYTES` | `4194304` | Larger bodies get `413`. |
| `TOKENCOST_CORS_ORIGINS` | `[]` | The web app is same-origin, so CORS isn't needed. |

## Fly.io

`fly.toml` is ready for `https://token-cost-estimator.fly.dev`:

```sh
brew install flyctl
fly auth login
fly launch --no-deploy --copy-config --name token-cost-estimator   # first time only
fly deploy
```

Machines stop when idle and start on the next request, so an unused app costs
nothing to run. The first request after idling waits a few seconds while the
machine starts.

## Platform notes

- **Health check:** `GET /health` (process up) and `GET /ready` (prices loaded).
- **Scaling:** stateless; MCP runs in stateless mode. Rate limits are kept in
  memory **per instance**, so N instances allow up to N times the configured
  rate. Start with one instance; it handles far more traffic than the limits
  admit.
- **HTTPS:** terminate TLS at the platform (all of Fly.io, Render and Railway do
  this automatically). The app sends `Strict-Transport-Security`.
- **Read-only filesystem:** supported; only `/tmp` needs to be writable.

## Launch checklist

- [ ] `TOKENCOST_ALLOWED_HOSTS` set to the public hostname
- [ ] `https://<host>/ready` returns `{"status": "ready", "models": 6}`
- [ ] Web app loads at `/` and `/compare`; no CSP errors in the browser console
- [ ] `claude mcp add --transport http tokencost https://<host>/mcp` lists 4 tools
- [ ] 61 quick requests to `/api/v1/models` return a `429` on the 61st
- [ ] Price check scheduled before **2026-11-30** (Gemini 4 Argon changes on 2026-12-01; see docs/updating-prices.md)

## After launch: updating prices

Edit `src/tokencost/data/pricing.yaml`, run `make check`, then rebuild and
redeploy the image. Prices are baked into the image, so a running instance
never changes underneath its users.
