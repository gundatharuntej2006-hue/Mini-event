"""
Black Market Asset Purchases Model for EVENT HQ.
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Manages squad purchases of tactical advantages and missing fragments in Round 3.
Prices are configurable guidelines and link directly to WalletTransaction ledger records.
"""

import uuid
import enum
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    String, Integer, Float, DateTime, ForeignKey, Enum, JSON, desc
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.wallet import WalletTransaction


class BlackMarketAssetType(str, enum.Enum):
    MISSING_CODE_FRAGMENT = "MISSING_CODE_FRAGMENT"
    EXTRA_PREP_TIME = "EXTRA_PREP_TIME"
    EXTRA_WITNESS_QUESTION = "EXTRA_WITNESS_QUESTION"
    AGENT_INTEL = "AGENT_INTEL"
    CUSTOM = "CUSTOM"


class PurchaseStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    REFUNDED = "REFUNDED"
    PENDING = "PENDING"


class AuctionStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class BidStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    WON = "WON"
    LOST = "LOST"
    CANCELLED = "CANCELLED"


class BlackMarketPurchase(Base):
    """
    Log of purchased tactical assets and missing code fragments from the Black Market.
    """
    __tablename__ = "black_market_purchases"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: f"bmp-{uuid.uuid4().hex[:8]}"
    )
    team_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="RESTRICT"),
        index=True,
        nullable=False
    )
    asset_type: Mapped[BlackMarketAssetType] = mapped_column(
        Enum(BlackMarketAssetType, name="bm_asset_type_enum", create_constraint=True),
        nullable=False
    )
    price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )
    transaction_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("wallet_transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    status: Mapped[PurchaseStatus] = mapped_column(
        Enum(PurchaseStatus, name="bm_purchase_status_enum", create_constraint=True),
        default=PurchaseStatus.COMPLETED,
        nullable=False
    )
    details: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=dict,
        nullable=True
    )
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )
    purchased_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="black_market_purchases")
    transaction: Mapped[Optional["WalletTransaction"]] = relationship("WalletTransaction")


class BlackMarketAuction(Base):
    """
    Sealed-bid auction item in Round 3 Black Market.
    """
    __tablename__ = "black_market_auctions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: f"auc-{uuid.uuid4().hex[:8]}"
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    item_type: Mapped[str] = mapped_column(String(100), default="CUSTOM", nullable=False)
    starting_bid: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reserve_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[AuctionStatus] = mapped_column(
        Enum(AuctionStatus, name="bm_auction_status_enum", create_constraint=True),
        default=AuctionStatus.OPEN,
        nullable=False
    )
    winning_bid_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    winning_team_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True
    )
    winning_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Relationships
    winning_team: Mapped[Optional["Team"]] = relationship("Team")
    bids: Mapped[List["BlackMarketBid"]] = relationship(
        "BlackMarketBid",
        back_populates="auction",
        cascade="all, delete-orphan",
        order_by="desc(BlackMarketBid.bid_amount)"
    )


class BlackMarketBid(Base):
    """
    Sealed bid submitted by a squad for an auction item.
    """
    __tablename__ = "black_market_bids"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: f"bid-{uuid.uuid4().hex[:8]}"
    )
    auction_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("black_market_auctions.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    team_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="RESTRICT"),
        index=True,
        nullable=False
    )
    bid_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[BidStatus] = mapped_column(
        Enum(BidStatus, name="bm_bid_status_enum", create_constraint=True),
        default=BidStatus.SUBMITTED,
        nullable=False
    )
    transaction_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("wallet_transactions.id", ondelete="SET NULL"),
        nullable=True
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    auction: Mapped["BlackMarketAuction"] = relationship("BlackMarketAuction", back_populates="bids")
    team: Mapped["Team"] = relationship("Team")
    transaction: Mapped[Optional["WalletTransaction"]] = relationship("WalletTransaction")
