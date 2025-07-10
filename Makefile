.PHONY: dev clean install sync run-backend run-frontend test lint

# Check if uv is installed, install if not
check-uv:
	@which uv > /dev/null || (echo "Installing uv..." && curl -LsSf https://astral.sh/uv/install.sh | sh)

# Sync dependencies with uv
sync: check-uv
	@echo "Syncing dependencies with uv..."
	uv sync

# Development environment setup
dev: sync
	@echo "Starting development environment..."
	@mkdir -p .bench
	@touch .bench/config
	@echo "Development environment ready"
	@echo "Run: source env/dev.sh to set environment variables"

# Run backend with uv
run-backend: sync
	@echo "Starting backend server with uv..."
	source env/dev.sh && uv run uvicorn apps.backend.main:app --reload --host 0.0.0.0 --port 8000

# Run frontend
run-frontend:
	@echo "Starting frontend server..."
	cd apps/frontend && pnpm dev

# Run database migrations
migrate: sync
	@echo "Running database migrations..."
	source env/dev.sh && uv run alembic upgrade head

# Run tests
test: sync
	@echo "Running tests..."
	uv run pytest

# Run linting
lint: sync
	@echo "Running linter..."
	uv run ruff check .
	uv run mypy .

# Install (legacy compatibility)
install: sync
	@echo "Installing frontend dependencies..."
	cd apps/frontend && pnpm install

# Clean up
clean:
	@echo "Cleaning up development environment..."
	@rm -rf .bench
	@rm -f local.db
	@rm -rf .venv