# Token Cost Estimator

Estimate and compare the cost of AI model usage across providers.

> **Status:** early development (milestone M0). Prices in the app are
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
