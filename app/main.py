import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.config import settings
from app.database import engine, shutdown_db
from app.routers.wallets import router as wallets_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    logger.info("Application startup")
    yield
    logger.info("Application shutdown")
    await shutdown_db()


app = FastAPI(
    title="Wallet API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(wallets_router)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.error("IntegrityError on %s: %s", request.url, exc)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Database constraint violation"},
    )


@app.exception_handler(OperationalError)
async def operational_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
    logger.error("OperationalError on %s: %s", request.url, exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database unavailable"},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return {"status": "error", "detail": str(e)}
