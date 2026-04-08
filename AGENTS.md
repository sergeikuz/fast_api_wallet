# AGENTS.md — Wallet REST API

## Commands

```bash
uv run pytest tests/ -v          # Run tests (requires PostgreSQL on localhost)
uv run ruff check app/ tests/    # Lint
uv run ruff format app/ tests/   # Format
uv run alembic upgrade head      # Run migrations
make help                        # All commands
```

## Critical Gotchas

- **`uv` is the package manager** — not pip. Always use `uv run <cmd>` or `uv sync`.
- **Tests require PostgreSQL** running on localhost. `conftest.py` creates/drops `wallet_test_db` via asyncpg.
- **`truncate_tables` runs BEFORE each test** (not after) — data is cleaned at fixture start.
- **`asyncio_mode = "auto"`** in pyproject.toml — no `@pytest.mark.asyncio` needed on test functions.
- **After `async with db.begin()` exits**, SQLAlchemy objects are expired. Read `wallet.created_at`/`updated_at` inside the transaction block, not after.
- **`db.flush()` + `db.refresh(wallet)`** required after modifying balance to get the server-generated `updated_at` value.

## Architecture

```
routers/wallets.py  →  services/wallet_service.py  →  models.py  →  PostgreSQL
```

- **Balance is `Decimal`**, never `float`. Numeric(15,2) in DB.
- **`SELECT ... FOR UPDATE`** in `lock_wallet()` — pessimistic row lock for concurrent writes. Do not replace with plain SELECT on write paths.
- **`INSERT ... ON CONFLICT DO NOTHING`** in `ensure_wallet_exists()` — atomic wallet creation under concurrent requests.
- **`CHECK (balance >= 0)`** constraint in migration — final safety net at DB level.

## Alembic

- `alembic/env.py` imports `app.config.settings` — requires `PYTHONPATH=/app` in Docker.
- Uses async engine directly, not `alembic.ini` URL (env.py overrides it).
- `make migrate` uses `uv run alembic upgrade head` — do not run bare `alembic`.

## Docker

- `uv pip install --system .` — setuptools with `[tool.setuptools.packages.find] include = ["app*"]`.
- Non-root user `appuser`. HEALTHCHECK uses curl.
- `make down` uses `-v` flag — removes volumes (data loss).
- DB port configurable via `PG_HOST_PORT` env var.

## Ruff

- Ignores `B008` — FastAPI `Depends()` in function defaults is standard pattern.
- Rules: E, F, I, N, UP, B, SIM, RUF.

## Known Issues (from code review, not yet fixed)

- `api_key` defined in config but never enforced.
