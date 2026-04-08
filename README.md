# Wallet REST API

Async REST API for managing user wallets with concurrent-safe balance operations.

## Features

- **Deposit/Withdraw** — `POST /api/v1/wallets/<uuid>/operation`
- **Get balance** — `GET /api/v1/wallets/<uuid>`
- **List wallets** — `GET /api/v1/wallets`
- **Health check** — `GET /health`

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | FastAPI (async) |
| ORM | SQLAlchemy 2.0 (asyncio) |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Testing | pytest + httpx + asyncpg |
| Linting | Ruff |
| Containerization | Docker + Docker Compose |
| Package manager | uv |
| CI/CD | GitHub Actions |

## Recent Improvements

- **Service Layer Refactored**: Separated pure business logic, data access, and service orchestration concerns
- **Single Source of Truth**: `OperationType` enum now defined only in `schemas.py`
- **Database Constraint**: Added explicit `CHECK (balance >= 0)` at DB level
- **Clean Architecture**: Better separation of concerns following SOLID principles

## Architecture

```
┌─────────────────────────────────────────┐
│              FastAPI App                │
│  ┌───────────────────────────────────┐  │
│  │  main.py — lifespan, middleware,  │  │
│  │  exception handlers, health check │  │
│  └───────────────┬───────────────────┘  │
│                  │                      │
│  ┌───────────────▼───────────────────┐  │
│  │  routers/wallets.py — HTTP layer  │  │
│  │  (request parsing, response fmt)  │  │
│  └───────────────┬───────────────────┘  │
│                  │                      │
│  ┌───────────────▼───────────────────┐  │
│  │  services/wallet_service.py —     │  │
│  │  business logic, DB queries       │  │
│  └───────────────┬───────────────────┘  │
│                  │                      │
│  ┌───────────────▼───────────────────┐  │
│  │  models.py — SQLAlchemy ORM       │  │
│  │  schemas.py — Pydantic DTOs       │  │
│  └───────────────────────────────────┘  │
└──────────────────┬──────────────────────┘
                   │
           ┌────────▼────────┐
           │   PostgreSQL    │
           │  (asyncpg)      │
           └─────────────────┘
                    ↑
            (Pure business logic & data access layers)
```

## Concurrency Safety

Two mechanisms protect against race conditions on concurrent wallet operations:

1. **`SELECT ... FOR UPDATE`** — pessimistic row-level lock. When a transaction reads a wallet for modification, it locks the row. Other transactions must wait until the lock is released.

2. **`INSERT ... ON CONFLICT DO NOTHING`** — atomic wallet creation. When multiple requests try to create the same wallet simultaneously, only one succeeds; others silently skip.

3. **`CHECK (balance >= 0)`** — database-level constraint. Final safety net preventing negative balances even if application logic fails.

## SOLID Principles

| Principle | Implementation |
|-----------|---------------|
| **S** — Single Responsibility | Each layer has one concern: `routers` handle HTTP, `services` handle business logic, `models` handle data mapping, `schemas` handle validation/serialization |
| **O** — Open/Closed | New operation types can be added by extending `OperationType` enum and updating `apply_operation()` without modifying the router or schema layers |
| **L** — Liskov Substitution | `OperationType` inherits from `StrEnum`, behaving as both an enum and a string — interchangeable in all contexts |
| **I** — Interface Segregation | Separate functions for each DB operation: `get_wallet`, `ensure_wallet_exists`, `lock_wallet`, `apply_operation` — callers use only what they need |
| **D** — Dependency Inversion | Router depends on abstract `get_db` dependency injection, not concrete session creation. Service layer depends on `AsyncSession` interface, not a specific implementation |

## Recent Improvements

- **Service Layer Refactored**: Separated pure business logic, data access, and service orchestration concerns
- **Single Source of Truth**: `OperationType` enum now defined only in `schemas.py`
- **Database Constraint**: Added explicit `CHECK (balance >= 0)` at DB level
- **Clean Architecture**: Better separation of concerns following SOLID principles

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env

# 2. Start everything (app + PostgreSQL)
docker compose up -d

# 3. Verify
curl http://localhost:8000/health
# {"status":"ok"}
```

## API Endpoints

### List all wallets

```bash
GET /api/v1/wallets?limit=50&offset=0
```

```json
{
  "wallets": [
    {
      "wallet_id": "550e8400-e29b-41d4-a716-446655440000",
      "balance": "1000.00",
      "created_at": "2026-04-06T12:00:00Z"
    }
  ],
  "total": 1
}
```

### Get wallet balance

```bash
GET /api/v1/wallets/<uuid>
```

```json
{
  "wallet_id": "550e8400-e29b-41d4-a716-446655440000",
  "balance": "1000.00",
  "created_at": "2026-04-06T12:00:00Z",
  "updated_at": "2026-04-06T12:05:00Z"
}
```

### Perform operation (deposit/withdraw)

```bash
POST /api/v1/wallets/<uuid>/operation
Content-Type: application/json

{
  "operation_type": "DEPOSIT",
  "amount": "100.00"
}
```

Creates wallet if it doesn't exist. Auto-creates on first operation.

### Health check

```bash
GET /health
```

Returns `200 {"status":"ok"}` if both app and database are healthy, `503` otherwise.

## Swagger UI

Interactive API documentation: `http://localhost:8000/docs`

## Project Structure

```
├── app/
│   ├── main.py                  # FastAPI app, middleware, exception handlers
│   ├── config.py                # Pydantic settings (env vars)
│   ├── database.py              # Async engine, session factory
│   ├── models.py                # SQLAlchemy ORM models
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── routers/
│   │   └── wallets.py           # HTTP endpoints
│   └── services/
│       └── wallet_service.py    # Business logic
├── alembic/
│   ├── env.py                   # Async migration runner
│   └── versions/
│       └── 001_create_wallets.py
├── tests/
│   ├── conftest.py              # Test fixtures, test DB management
│   └── test_wallets.py          # 15 integration tests
├── .github/workflows/ci.yml     # GitHub Actions CI
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── pyproject.toml
```

## Development

```bash
# Install dependencies
make install

# Run tests (requires PostgreSQL on localhost)
make test

# Lint and format
make lint
make format

# Start/stop Docker
make up
make down

# Run migrations locally
make migrate
```

## CI/CD

GitHub Actions runs on every push and PR:
- **lint** — ruff check + format check
- **test** — pytest with PostgreSQL service container

## Configuration

All settings via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/wallet_db` | Database connection string |
| `ECHO_SQL` | `false` | Log SQL queries |
| `DB_POOL_SIZE` | `20` | Connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Max overflow connections |
| `DB_POOL_TIMEOUT` | `30` | Pool acquire timeout (seconds) |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |
