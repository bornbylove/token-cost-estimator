# Token Cost Estimator

Estimate and compare the cost of AI model usage across providers.

> **Status:** early development (milestone M1). Prices in the app are
> illustrative placeholders, not verified provider pricing. Estimates are
> not invoices.

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
| POST   | `/api/v1/estimate`         | Cost for given input/output tokens     |

```sh
curl -X POST localhost:8000/api/v1/estimate \
  -H 'Content-Type: application/json' \
  -d '{"model_id": "anthropic-example", "input_tokens": 1000000, "output_tokens": 500000}'
```

Money values are strings in USD with 6 decimal places. Responses include
`pricing_status`, `effective_date`, and `stale` (price older than 90 days).
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
