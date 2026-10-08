"""Round 2 Cabo tables and scoring for the live event control system."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Round2LiveConfig(Base):
    __tablename__ = "round2_live_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    tables_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generated_by: Mapped[str | None] = mapped_column(String(40), ForeignKey("event_accounts.id"), nullable=True)
    is_finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_by: Mapped[str | None] = mapped_column(String(40), ForeignKey("event_accounts.id"), nullable=True)


class Round2CaboTable(Base):
    __tablename__ = "round2_cabo_tables"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: f"r2tbl-{uuid.uuid4().hex[:18]}")
    table_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    assigned_admin_id: Mapped[str | None] = mapped_column(String(40), ForeignKey("event_accounts.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Round2CaboSeat(Base):
    __tablename__ = "round2_cabo_seats"
    __table_args__ = (
        UniqueConstraint("table_id", "participant_id", name="uq_r2_table_participant"),
        UniqueConstraint("table_id", "team_id", name="uq_r2_table_team"),
        UniqueConstraint("table_id", "seat_position", name="uq_r2_table_seat"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: f"r2seat-{uuid.uuid4().hex[:18]}")
    table_id: Mapped[str] = mapped_column(String(40), ForeignKey("round2_cabo_tables.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id: Mapped[str] = mapped_column(String(36), ForeignKey("participants.id"), nullable=False, index=True)
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id"), nullable=False, index=True)
    seat_position: Mapped[int] = mapped_column(Integer, nullable=False)


class Round2CaboScore(Base):
    __tablename__ = "round2_cabo_scores"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: f"r2score-{uuid.uuid4().hex[:18]}")
    seat_id: Mapped[str] = mapped_column(String(40), ForeignKey("round2_cabo_seats.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    outcome: Mapped[str] = mapped_column(String(8), nullable=False)  # WIN or LOSS
    base_points: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(40), ForeignKey("event_accounts.id"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Round2TeamAward(Base):
    __tablename__ = "round2_team_awards"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: f"r2award-{uuid.uuid4().hex[:18]}")
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    points: Mapped[float] = mapped_column(Float, nullable=False)
    applied_by: Mapped[str] = mapped_column(String(40), ForeignKey("event_accounts.id"), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Round2LiveAudit(Base):
    __tablename__ = "round2_live_audit"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: f"r2audit-{uuid.uuid4().hex[:18]}")
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    performed_by: Mapped[str] = mapped_column(String(40), ForeignKey("event_accounts.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
