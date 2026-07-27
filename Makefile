# BriefPilot — developer entry points.
#
# `make dev` is the documented way to run the project (CLAUDE.md §3): the demo
# strategy is a local Docker Compose stack, not paid hosting.
#
# Windows note: `make` is not installed by default. Either install it
# (`choco install make`) or run the docker compose commands shown under each
# target directly — every target here is a thin wrapper, nothing is hidden.

.DEFAULT_GOAL := help

BACKEND  := backend
FRONTEND := frontend
COMPOSE  := docker compose

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# --- running ----------------------------------------------------------

.PHONY: dev
dev: ## Run the full stack (frontend + backend + postgres) via Docker
	$(COMPOSE) up --build

.PHONY: dev-detached
dev-detached: ## Same as `dev`, in the background
	$(COMPOSE) up --build -d

.PHONY: down
down: ## Stop and remove containers
	$(COMPOSE) down

.PHONY: logs
logs: ## Follow container logs
	$(COMPOSE) logs -f

.PHONY: db
db: ## Start only Postgres (for running services locally)
	$(COMPOSE) up postgres

# --- setup ------------------------------------------------------------

.PHONY: install
install: ## Install backend + frontend deps and register git hooks
	cd $(BACKEND) && pip install -r requirements-dev.txt
	cd $(FRONTEND) && npm install
	pre-commit install

.PHONY: env
env: ## Create .env files from the .env.example templates
	bash infrastructure/scripts/setup-env.sh

# --- quality ----------------------------------------------------------

.PHONY: lint
lint: ## Lint and format-check both apps (no files modified)
	cd $(BACKEND) && ruff check app && black --check app && isort --check-only app
	cd $(FRONTEND) && npm run lint && npm run format:check

.PHONY: format
format: ## Auto-format both apps
	cd $(BACKEND) && ruff check app --fix && black app && isort app
	cd $(FRONTEND) && npm run format

.PHONY: typecheck
typecheck: ## Run mypy (strict) on the backend
	cd $(BACKEND) && mypy app

.PHONY: test
test: ## Run backend tests
	cd $(BACKEND) && pytest

.PHONY: build
build: ## Production build of the frontend
	cd $(FRONTEND) && npm run build

.PHONY: hooks
hooks: ## Run every pre-commit hook against all files
	pre-commit run --all-files

.PHONY: ci
ci: lint typecheck test build ## Run everything CI runs, in CI's order
	@echo "All CI checks passed locally."

# --- cleanup ----------------------------------------------------------

.PHONY: clean
clean: ## Remove build artifacts and caches
	$(COMPOSE) down -v
	rm -rf $(FRONTEND)/.next $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache $(BACKEND)/.mypy_cache
