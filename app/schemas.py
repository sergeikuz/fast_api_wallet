from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class OperationType(StrEnum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"


class OperationRequest(BaseModel):
    operation_type: OperationType
    amount: Decimal = Field(gt=0, decimal_places=2, description="Amount with max 2 decimal places")

    model_config = {"json_schema_extra": {"examples": [{"operation_type": "DEPOSIT", "amount": "100.00"}]}}


class BalanceResponse(BaseModel):
    wallet_id: UUID
    balance: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "wallet_id": "550e8400-e29b-41d4-a716-446655440000",
                    "balance": "1000.00",
                    "created_at": "2026-04-06T12:00:00Z",
                    "updated_at": "2026-04-06T12:05:00Z",
                }
            ]
        }
    }


class WalletListItem(BaseModel):
    wallet_id: UUID
    balance: Decimal
    created_at: datetime

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "wallet_id": "550e8400-e29b-41d4-a716-446655440000",
                    "balance": "1000.00",
                    "created_at": "2026-04-06T12:00:00Z",
                }
            ]
        }
    }


class WalletListResponse(BaseModel):
    wallets: list[WalletListItem]
    total: int
