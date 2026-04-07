"""create wallets table

Revision ID: 001
Revises:
Create Date: 2026-04-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("balance", sa.Numeric(15, 2), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("balance >= 0", name="check_balance_non_negative"),
    )
    op.create_index("ix_wallets_created_at", "wallets", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_wallets_created_at", "wallets")
    op.drop_table("wallets")
