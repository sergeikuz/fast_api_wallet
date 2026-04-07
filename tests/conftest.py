import os

import asyncpg
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import get_db
from app.main import app
from app.models import Base

TEST_DB_NAME = "wallet_test_db"
TEST_PG_USER = os.getenv("TEST_PG_USER", "postgres")
TEST_PG_PASSWORD = os.getenv("TEST_PG_PASSWORD", "postgres")
TEST_PG_HOST = os.getenv("TEST_PG_HOST", "localhost")
TEST_PG_PORT = int(os.getenv("TEST_PG_PORT", "5432"))
TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{TEST_PG_USER}:{TEST_PG_PASSWORD}@{TEST_PG_HOST}:{TEST_PG_PORT}/{TEST_DB_NAME}"
)

engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
async_test_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _create_test_database() -> None:
    conn = await asyncpg.connect(
        host=TEST_PG_HOST,
        port=TEST_PG_PORT,
        user=TEST_PG_USER,
        password=TEST_PG_PASSWORD,
        database="postgres",
    )
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        await conn.close()


async def _drop_test_database() -> None:
    conn = await asyncpg.connect(
        host=TEST_PG_HOST,
        port=TEST_PG_PORT,
        user=TEST_PG_USER,
        password=TEST_PG_PASSWORD,
        database="postgres",
    )
    try:
        await conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1 AND pid <> pg_backend_pid()",
            TEST_DB_NAME,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"')
    finally:
        await conn.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    await _create_test_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    await _drop_test_database()


@pytest_asyncio.fixture(autouse=True)
async def truncate_tables():
    async with engine.connect() as conn:
        await conn.execute(text("DELETE FROM wallets"))
        await conn.commit()
    yield


@pytest_asyncio.fixture(scope="session", autouse=True)
async def override_db():
    async def _override_get_db():
        async with async_test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
