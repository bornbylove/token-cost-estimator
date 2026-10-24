# Token Cost Estimator

Estimate and compare the cost of AI model usage across providers.

> **Status:** early development (milestone M6). Prices are checked by hand
> against each provider's official pricing page; each estimate shows the date
> its prices were checked. Estimates are not invoices.

## Supported models

| Provider  | Model                 | id                      |
| --------- | --------------------- | ----------------------- |
| Anthropic | Claude Fable 5.1      | `claude-fable-5-1`      |
| Anthropic | Claude Haiku 5.5      | `claude-haiku-5-5`      |
| OpenAI    | GPT-6 Astra           | `gpt-6-astra`           |
| OpenAI    | GPT-6 Luna            | `gpt-6-luna`            |
| Google    | Gemini 4 Argon        | `gemini-4-argon`        |
| Google    | Gemini 3.5 Flash-Lite | `gemini-3.5-flash-lite` |

Prices are the standard text rates. When a model charges more for long
prompts, the higher rate is applied automatically. To add or update a price,
see [docs/updating-prices.md](docs/updating-prices.md).

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — install with `brew install uv`
- Node.js 24 LTS, for the web app only — install with `brew install node@24`

## Quickstart

```sh
make install   # create .venv and install locked dependencies
make dev       # run the API at http://127.0.0.1:8000 (docs at /docs)
```

## Web app

Three pages: **Estimate** (one model, with a breakdown and monthly
projection), **Compare** (every model, cheapest first, as a chart and a
table), and **Prices** (the price list with sources and check dates). Form
values are kept in the URL, so any result can be shared as a link.

```sh
make web-install   # once
make dev           # terminal 1: API on :8000
make web-dev       # terminal 2: app on http://localhost:5173 (proxies /api)
make serve         # or: production build served by the API on :8000
```

The TypeScript API client is generated from the backend's OpenAPI schema.
After changing an endpoint or schema, run `make openapi` and commit the
result. CI fails if they drift apart.

## Command line

Install the `tokencost` command (works offline against the bundled prices):

```sh
pipx install .        # or, inside the repo: uv run tokencost ...
```

```sh
tokencost models                                   # prices per 1M tokens
tokencost estimate claude-haiku-5-5 -i 3k -o 800   # one request
tokencost estimate gpt-6-luna -i 3k -o 800 -d 5000 # + daily/monthly totals
tokencost compare -i 3k -o 800 -d 5000             # all models, cheapest first
tokencost compare gpt-6-astra claude-fable-5-1 -i 300k -o 1k
cat prompt.txt | tokencost count                   # approximate token count
```

Token counts accept `3000`, `3,000`, `3k`, or `1.5M`. Add `--json` to any
command for machine-readable output in the same shape as the REST API.
Warnings and errors go to stderr. The exit code is 1 for an unknown model or
an unreadable file, and 2 for invalid arguments.

## MCP server (for AI agents)

The same features are available as [MCP](https://modelcontextprotocol.io)
tools: `list_models`, `estimate_cost`, `compare_models`, and `count_tokens`.
All of them are read-only, and results use the same JSON shape as the REST API.

**Claude Code (this repo):** `.mcp.json` registers the server automatically.
Approve it when Claude Code asks.

**Claude Code (anywhere), after `pipx install .`:**

```sh
claude mcp add tokencost -- tokencost-mcp
```

**Claude Desktop:** add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tokencost": { "command": "tokencost-mcp" }
  }
}
```

**Remote (Streamable HTTP):** the web app serves MCP at `/mcp`, statelessly.
In production, set `TOKENCOST_ALLOWED_HOSTS` to the public hostname, e.g.
`["tokencost.example.com"]`. Requests with any other `Host` header are
rejected (DNS rebinding protection).

## API

All endpoints are documented interactively at `/docs`.

| Method | Path                       | Purpose                                |
| ------ | -------------------------- | -------------------------------------- |
| GET    | `/health`                  | Process is up                          |
| GET    | `/ready`                   | Pricing loaded; reports model count    |
| GET    | `/api/v1/models`           | List models with prices                |
| GET    | `/api/v1/models/{id}`      | One model's prices                     |
| POST   | `/api/v1/estimate`         | Cost of one request, optional projection |
| POST   | `/api/v1/compare`          | Same usage across models, cheapest first |
| POST   | `/api/v1/tokens/count`     | Approximate token count for some text  |

```sh
curl -X POST localhost:8000/api/v1/estimate \
  -H 'Content-Type: application/json' \
  -d '{"model_id": "claude-haiku-5-5", "input_tokens": 1000000, "output_tokens": 500000}'
```

Add `"requests_per_day": 5000` to `/estimate` or `/compare` to get a
`projection` with daily and monthly (30-day) cost. `/compare` takes optional
`model_ids` (all models when omitted) and returns `cheapest_model_ids`, which
lists every model tied for the lowest cost.

`/tokens/count` takes `{"text": "..."}` (up to 1,000,000 characters) and
returns an **approximate** count from OpenAI's public `o200k_base` tokenizer.
No provider publishes an offline tokenizer for current models, so real
counts vary by model. Text is counted in memory and never stored or logged.

Money values are strings in USD with 6 decimal places. Responses include
`price_tier` (`standard` or `long_context`), `effective_date`, `valid_until`,
`notes`, and `stale`. `stale` is true when the price was last checked more
than 90 days ago or its `valid_until` date has passed.
Errors always look like `{"error": {"code": "...", "message": "..."}}`.

## Configuration

Settings come from `TOKENCOST_*` environment variables or a `.env` file;
see `.env.example`. Prices live in `src/tokencost/data/pricing.yaml` and are
validated when the app starts — an invalid file stops the app from booting.

## Project layout

```
src/tokencost/
  core/     business logic: schemas, pricing math, repository, service, tokenizer
  api/      FastAPI app factory, routes, error handling
  cli/      tokencost command (Typer + Rich)
  mcp/      MCP server: stdio (tokencost-mcp) and HTTP (/mcp)
frontend/   web app: Vite + React + TypeScript, typed client from openapi.json
  data/     pricing.yaml
tests/      unit/, api/, cli/ and mcp/ tests, with fixed fixture pricing
```

## Development

| Command          | What it does                              |
| ---------------- | ----------------------------------------- |
| `make test`      | Run tests with coverage                   |
| `make lint`      | Ruff lint and format check                |
| `make format`    | Auto-fix lint issues and format code      |
| `make typecheck` | mypy in strict mode                       |
| `make check`     | Everything CI runs (lint, types, tests)   |
| `make web-check` | Web app: typecheck, tests, build          |
| `make openapi`   | Regenerate the web app's typed API client |

Dependencies are pinned in `uv.lock`. Add one with `uv add <package>`
(or `uv add --dev <package>`) and commit the updated lockfile.
