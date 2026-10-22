UV ?= uv

.PHONY: install dev test lint format typecheck check

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
