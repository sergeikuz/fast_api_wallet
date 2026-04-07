import logging
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Wallet
from app.schemas import OperationType

logger = logging.getLogger(__name__)


async def get_wallet(db: AsyncSession, wallet_id: UUID) -> Wallet:
    result = await db.execute(select(Wallet).where(Wallet.id == wallet_id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    return wallet


async def ensure_wallet_exists(db: AsyncSession, wallet_id: UUID) -> None:
    await db.execute(
        pg_insert(Wallet).values(id=wallet_id, balance=Decimal("0")).on_conflict_do_nothing(index_elements=["id"])
    )


async def lock_wallet(db: AsyncSession, wallet_id: UUID) -> Wallet:
    result = await db.execute(select(Wallet).where(Wallet.id == wallet_id).with_for_update())
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    return wallet


def apply_operation(wallet: Wallet, operation_type: OperationType, amount: Decimal) -> None:
    logger.info(
        "Wallet operation: wallet_id=%s, type=%s, amount=%s, balance_before=%s",
        wallet.id,
        operation_type,
        amount,
        wallet.balance,
    )

    if operation_type == OperationType.DEPOSIT:
        wallet.balance += amount
    elif operation_type == OperationType.WITHDRAW:
        if wallet.balance < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient funds",
            )
        wallet.balance -= amount
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown operation type: {operation_type}",
        )

    logger.info(
        "Wallet operation result: wallet_id=%s, balance_after=%s",
        wallet.id,
        wallet.balance,
    )
