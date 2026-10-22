# Token Cost Estimator

Estimate and compare the cost of AI model usage across providers.

> **Status:** early development (milestone M3). Prices are checked by hand
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

## Quickstart

```sh
make install   # create .venv and install locked dependencies
make dev       # run the API at http://127.0.0.1:8000 (docs at /docs)
```

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
  core/     business logic: schemas, pricing math, repository, service
  api/      FastAPI app factory, routes, error handling
  data/     pricing.yaml
tests/      unit/ (core) and api/ tests, with fixed fixture pricing
```

## Development

| Command          | What it does                              |
| ---------------- | ----------------------------------------- |
| `make test`      | Run tests with coverage                   |
| `make lint`      | Ruff lint and format check                |
| `make format`    | Auto-fix lint issues and format code      |
| `make typecheck` | mypy in strict mode                       |
| `make check`     | Everything CI runs (lint, types, tests)   |

Dependencies are pinned in `uv.lock`. Add one with `uv add <package>`
(or `uv add --dev <package>`) and commit the updated lockfile.
