"""Live auction/game state for the event-account (team ID) experience."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Round3LiveConfig(Base):
    __tablename__ = "round3_live_config"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Round3LiveTeam(Base):
    __tablename__ = "round3_live_teams"
    team_id: Mapped[str] = mapped_column(String(50), ForeignKey("teams.id"), primary_key=True)
    opening_points: Mapped[float] = mapped_column(Float, nullable=False)
    is_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Round3DealerTable(Base):
    __tablename__ = "round3_dealer_tables"
    table_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_number: Mapped[int] = mapped_column(Integer, nullable=False)
    game_mode: Mapped[str] = mapped_column(String(10), nullable=False)
    game_name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_points: Mapped[float] = mapped_column(Float, nullable=False, default=20)
    admin_id: Mapped[str | None] = mapped_column(String(40), ForeignKey("event_accounts.id"), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Round3GameAttempt(Base):
    __tablename__ = "round3_game_attempts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: f"r3game-{uuid.uuid4().hex[:18]}")
    team_id: Mapped[str] = mapped_column(String(50), ForeignKey("teams.id"), nullable=False, index=True)
    participant_id: Mapped[str] = mapped_column(String(36), ForeignKey("participants.id"), nullable=False)
    table_number: Mapped[int] = mapped_column(Integer, ForeignKey("round3_dealer_tables.table_number"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(14), nullable=False)  # OFFERED, QUEUED, RESERVED, ACTIVE, COMPLETE, EXPIRED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reserved_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    points: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    scored_by: Mapped[str | None] = mapped_column(String(40), ForeignKey("event_accounts.id"), nullable=True)


class Round3LiveLedger(Base):
    __tablename__ = "round3_live_ledger"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: f"r3tx-{uuid.uuid4().hex[:18]}")
    team_id: Mapped[str] = mapped_column(String(50), ForeignKey("teams.id"), nullable=False, index=True)
    delta: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Round3AuctionLot(Base):
    __tablename__ = "round3_auction_lots"
    __table_args__ = (UniqueConstraint("level", "token_number", name="uq_r3_clue_level_number"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: f"r3lot-{uuid.uuid4().hex[:18]}")
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    token_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    clue_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="DRAFT")
    opening_bid: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    winner_team_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("teams.id"), nullable=True)
    winning_bid: Mapped[float | None] = mapped_column(Float, nullable=True)


class Round3AuctionBid(Base):
    __tablename__ = "round3_auction_bids"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: f"r3bid-{uuid.uuid4().hex[:18]}")
    lot_id: Mapped[str] = mapped_column(String(40), ForeignKey("round3_auction_lots.id"), nullable=False, index=True)
    team_id: Mapped[str] = mapped_column(String(50), ForeignKey("teams.id"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Round3TeamSession(Base):
    __tablename__ = "round3_team_sessions"
    jti: Mapped[str] = mapped_column(String(40), primary_key=True)
    team_id: Mapped[str] = mapped_column(String(50), ForeignKey("teams.id"), nullable=False, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    signed_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Round3PuzzleUse(Base):
    """Permanent one-use ledger for the 275 Round 3 questions."""

    __tablename__ = "round3_puzzle_uses"
    puzzle_key: Mapped[str] = mapped_column(String(20), primary_key=True)
    table_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    attempt_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("round3_game_attempts.id"), nullable=False, unique=True
    )
    team_id: Mapped[str] = mapped_column(String(50), ForeignKey("teams.id"), nullable=False, index=True)
    participant_id: Mapped[str] = mapped_column(String(36), ForeignKey("participants.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Round3QualificationRule(Base):
    __tablename__ = "round3_qualification_rule"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    qualifying_count: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_by: Mapped[str | None] = mapped_column(String(40), ForeignKey("event_accounts.id"), nullable=True)


class Round3QualifiedTeam(Base):
    __tablename__ = "round3_qualified_teams"
    team_id: Mapped[str] = mapped_column(String(50), ForeignKey("teams.id"), primary_key=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    points_snapshot: Mapped[float] = mapped_column(Float, nullable=False)
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
