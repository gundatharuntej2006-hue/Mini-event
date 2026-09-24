"""
Unified Tournament Wallet and Transaction Ledger Models for EVENT HQ.
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Provides persistent single-wallet-per-team architecture and immutable audit ledger.
Starting balance defaults to canonical STARTING_WALLET_BALANCE (1000 points).
"""

import uuid
import enum
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Float, Boolean, DateTime, ForeignKey, Enum, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now
from app.core.constants import STARTING_WALLET_BALANCE

if TYPE_CHECKING:
    from app.models.team import Team


class TransactionType(str, enum.Enum):
    INITIAL_BALANCE = "INITIAL_BALANCE"
    ROUND1_REWARD = "ROUND1_REWARD"
    ROUND2_REWARD = "ROUND2_REWARD"
    AGENT_TASK_REWARD = "AGENT_TASK_REWARD"
    PENALTY = "PENALTY"
    BLACK_MARKET_PURCHASE = "BLACK_MARKET_PURCHASE"
    REVERSAL = "REVERSAL"
    ADJUSTMENT = "ADJUSTMENT"


class TeamWallet(Base):
    """
    Persistent team tournament wallet.
    Exactly one wallet per team, initialized with canonical 1000 points.
    """
    __tablename__ = "team_wallets"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: f"wal-{uuid.uuid4().hex[:8]}"
    )
    team_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="RESTRICT"),
        unique=True,
        index=True,
        nullable=False
    )
    current_balance: Mapped[float] = mapped_column(
        Numeric(12, 2, asdecimal=False),
        default=STARTING_WALLET_BALANCE,
        nullable=False
    )
    total_earned: Mapped[float] = mapped_column(
        Numeric(12, 2, asdecimal=False),
        default=0.0,
        nullable=False
    )
    total_spent: Mapped[float] = mapped_column(
        Numeric(12, 2, asdecimal=False),
        default=0.0,
        nullable=False
    )
    total_penalties: Mapped[float] = mapped_column(
        Numeric(12, 2, asdecimal=False),
        default=0.0,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False
    )

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="wallet")
    transactions: Mapped[List["WalletTransaction"]] = relationship(
        "WalletTransaction",
        back_populates="wallet",
        cascade="all, delete-orphan",
        order_by="WalletTransaction.created_at.desc()"
    )


class WalletTransaction(Base):
    """
    Unified tournament wallet transaction ledger for full auditability.
    Tracks every balance modification, category, balance snapshots, and reversal status.
    """
    __tablename__ = "wallet_transactions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: f"wtx-{uuid.uuid4().hex[:8]}"
    )
    wallet_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("team_wallets.id", ondelete="RESTRICT"),
        index=True,
        nullable=False
    )
    team_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="RESTRICT"),
        index=True,
        nullable=False
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="wallet_tx_type_enum", create_constraint=True),
        nullable=False
    )
    amount: Mapped[float] = mapped_column(
        Numeric(12, 2, asdecimal=False),
        nullable=False
    )
    balance_before: Mapped[float] = mapped_column(
        Numeric(12, 2, asdecimal=False),
        nullable=False
    )
    balance_after: Mapped[float] = mapped_column(
        Numeric(12, 2, asdecimal=False),
        nullable=False
    )
    reference_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
    )  # e.g., ROUND_1, ROUND_2, AGENT_TASK, BLACK_MARKET, ORGANIZER_MANUAL
    reference_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    description: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    is_reversed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    reversal_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True
    )
    reversed_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    # Relationships
    wallet: Mapped["TeamWallet"] = relationship("TeamWallet", back_populates="transactions")
    team: Mapped["Team"] = relationship("Team", back_populates="wallet_transactions")
