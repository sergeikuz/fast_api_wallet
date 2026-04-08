import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Wallet
from app.schemas import BalanceResponse, OperationRequest, WalletListResponse
from app.services.wallet_service import WalletService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/wallets", tags=["wallets"])


@router.get(
    "",
    response_model=WalletListResponse,
    summary="List all wallets",
    description="Returns a paginated list of all wallets ordered by creation date.",
)
async def list_wallets(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    count_result = await db.execute(select(func.count(Wallet.id)))
    total = count_result.scalar_one()

    result = await db.execute(select(Wallet).order_by(Wallet.created_at.desc()).limit(limit).offset(offset))
    wallets = result.scalars().all()

    return WalletListResponse(
        wallets=[{"wallet_id": w.id, "balance": w.balance, "created_at": w.created_at} for w in wallets],
        total=total,
    )


@router.get(
    "/{wallet_id}",
    response_model=BalanceResponse,
    summary="Get wallet balance",
    description="Returns the current balance of the specified wallet.",
    responses={404: {"description": "Wallet not found"}},
)
async def get_balance(wallet_id: UUID, db: AsyncSession = Depends(get_db)) -> BalanceResponse:
    wallet_service = WalletService(db)
    wallet = await wallet_service.get_wallet_or_404(wallet_id)
    return BalanceResponse(
        wallet_id=wallet.id,
        balance=wallet.balance,
        created_at=wallet.created_at,
        updated_at=wallet.updated_at,
    )


@router.post(
    "/{wallet_id}/operation",
    response_model=BalanceResponse,
    summary="Perform wallet operation",
    description="Deposit or withdraw funds from the specified wallet. Creates wallet if it does not exist.",
    responses={
        400: {"description": "Insufficient funds or invalid operation"},
        404: {"description": "Wallet not found"},
        409: {"description": "Database constraint violation"},
    },
)
async def perform_operation(
    wallet_id: UUID,
    data: OperationRequest,
    db: AsyncSession = Depends(get_db),
) -> BalanceResponse:
    wallet_service = WalletService(db)
    wallet = await wallet_service.perform_operation(wallet_id, data.operation_type, data.amount)

    return BalanceResponse(
        wallet_id=wallet.id,
        balance=wallet.balance,
        created_at=wallet.created_at,
        updated_at=wallet.updated_at,
    )
