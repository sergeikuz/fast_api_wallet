.PHONY: install test lint format up down migrate help logs

help:
	@echo "Wallet REST API — Available commands:"
	@echo ""
	@echo "  install   Install dependencies (uv sync)"
	@echo "  test      Run tests (requires PostgreSQL on localhost)"
	@echo "  lint      Run ruff linter + format check"
	@echo "  format    Auto-fix lint issues + format code"
	@echo "  up        Start Docker containers (app + PostgreSQL)"
	@echo "  down      Stop and remove Docker containers"
	@echo "  migrate   Apply database migrations locally"
	@echo "  logs      Show app container logs"
	@echo "  help      Show this help message"

install:
	uv sync

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check app/ tests/
	uv run ruff format --check app/ tests/

format:
	uv run ruff check --fix app/ tests/
	uv run ruff format app/ tests/

up:
	docker compose up -d --build

down:
	docker compose down -v

migrate:
	uv run alembic upgrade head

logs:
	docker compose logs -f app
