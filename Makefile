.DEFAULT_GOAL := help

.PHONY: help install format lint typecheck test security-check check run migrate env demo compose-up compose-down

help:
	@awk 'BEGIN {FS = ":.*## "; printf "Available targets:\n"} /^[a-zA-Z_-]+:.*?## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Create the locked development environment
	UV_CACHE_DIR=$(CURDIR)/.uv-cache uv sync --frozen --extra dev

format: ## Format Python source and tests
	.venv/bin/ruff format .

lint: ## Run Ruff without modifying files
	.venv/bin/ruff check .

typecheck: ## Run strict mypy checks
	.venv/bin/mypy

test: ## Run deterministic tests
	.venv/bin/pytest

security-check: ## Scan Python source and locked dependencies
	.venv/bin/bandit -q -r src
	UV_CACHE_DIR=$(CURDIR)/.uv-cache uv export --frozen --no-dev --no-emit-project --format requirements-txt | .venv/bin/pip-audit --cache-dir .pip-audit-cache --disable-pip -r /dev/stdin

check: lint typecheck test security-check ## Run the complete local quality gate

run: ## Run the API from local environment variables
	.venv/bin/uvicorn secure_cloud_platform.main:create_app --factory --reload

migrate: ## Apply database migrations
	.venv/bin/alembic upgrade head

env: ## Generate a local .env with random secrets
	./scripts/init-env.sh

demo: ## Run the two-minute authenticated control-plane demo
	./scripts/demo.sh

compose-up: ## Build and start the local platform
	docker compose up --build -d

compose-down: ## Stop local services without deleting data
	docker compose down
