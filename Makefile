UV ?= uv

.PHONY: install dev test lint format typecheck check openapi web-install web-dev web-check web-build serve

install:  ## Create .venv and install all dependencies from uv.lock
	$(UV) sync --locked

dev:  ## Run the API with auto-reload on http://127.0.0.1:8000
	$(UV) run uvicorn tokencost.api.app:create_app --factory --reload

test:  ## Run the test suite with coverage
	$(UV) run pytest --cov=tokencost --cov-report=term-missing

lint:  ## Check linting and formatting
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format:  ## Format code and auto-fix lint issues
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

typecheck:  ## Run mypy in strict mode
	$(UV) run mypy

check: lint typecheck test  ## Everything CI runs

openapi:  ## Regenerate frontend/openapi.json and the typed TS client from the API
	$(UV) run python -c "import json; from tokencost.api.app import create_app; print(json.dumps(create_app().openapi(), indent=2))" > frontend/openapi.json
	cd frontend && npm run gen:api

web-install:  ## Install frontend dependencies from package-lock.json
	cd frontend && npm ci

web-dev:  ## Run the web app with hot reload on http://localhost:5173 (needs `make dev`)
	cd frontend && npm run dev

web-check:  ## Typecheck, test, and build the web app
	cd frontend && npm run check

web-build:  ## Build the web app into frontend/dist
	cd frontend && npm run build

serve: web-build  ## Production-like: API + built web app on http://127.0.0.1:8000
	TOKENCOST_FRONTEND_DIR=frontend/dist $(UV) run uvicorn tokencost.api.app:create_app --factory
