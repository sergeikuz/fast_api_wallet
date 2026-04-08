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


def apply_operation(wallet: Wallet, operation_type: OperationType, amount: Decimal) -> None:
    """Apply operation to wallet balance. Pure business logic without HTTP dependencies."""
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
            raise ValueError("Insufficient funds")
        wallet.balance -= amount
    else:
        raise ValueError(f"Unknown operation type: {operation_type}")

    logger.info(
        "Wallet operation result: wallet_id=%s, balance_after=%s",
        wallet.id,
        wallet.balance,
    )


async def get_wallet(db: AsyncSession, wallet_id: UUID) -> Wallet | None:
    """Get wallet by ID. Returns None if not found."""
    result = await db.execute(select(Wallet).where(Wallet.id == wallet_id))
    return result.scalar_one_or_none()


async def ensure_wallet_exists(db: AsyncSession, wallet_id: UUID) -> None:
    """Ensure wallet exists, creating it with zero balance if needed."""
    await db.execute(
        pg_insert(Wallet).values(id=wallet_id, balance=Decimal("0")).on_conflict_do_nothing(index_elements=["id"])
    )


async def lock_wallet(db: AsyncSession, wallet_id: UUID) -> Wallet | None:
    """Lock wallet for update. Returns None if not found."""
    result = await db.execute(select(Wallet).where(Wallet.id == wallet_id).with_for_update())
    return result.scalar_one_or_none()


class WalletService:
    """Service class orchestrating wallet operations with proper error handling."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_wallet_or_404(self, wallet_id: UUID) -> Wallet:
        """Get wallet or raise HTTP 404."""
        wallet = await get_wallet(self.db, wallet_id)
        if not wallet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
        return wallet

    async def ensure_wallet_exists(self, wallet_id: UUID) -> None:
        """Ensure wallet exists."""
        await ensure_wallet_exists(self.db, wallet_id)

    async def lock_wallet_or_404(self, wallet_id: UUID) -> Wallet:
        """Lock wallet or raise HTTP 404."""
        wallet = await lock_wallet(self.db, wallet_id)
        if not wallet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
        return wallet

    async def perform_operation(self, wallet_id: UUID, operation_type: OperationType, amount: Decimal) -> Wallet:
        """Perform wallet operation within a transaction."""
        async with self.db.begin():
            await self.ensure_wallet_exists(wallet_id)
            wallet = await self.lock_wallet_or_404(wallet_id)

            # Apply business logic (pure function)
            try:
                apply_operation(wallet, operation_type, amount)
            except ValueError as e:
                if "Insufficient funds" in str(e):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds") from e
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown operation type: {operation_type}"
                    ) from e

            await self.db.flush()
            await self.db.refresh(wallet)
            return wallet
