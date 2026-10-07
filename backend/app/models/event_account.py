import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EventRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    PARTICIPANT = "PARTICIPANT"


class EventAccount(Base):
    """Custom non-email credentials for the live Round 1 experience."""

    __tablename__ = "event_accounts"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: f"evt-{uuid.uuid4().hex[:18]}")
    login_id: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[EventRole] = mapped_column(Enum(EventRole, name="event_role_enum"), nullable=False)
    team_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("teams.id"), nullable=True, unique=True)
    location_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Round1Override(Base):
    __tablename__ = "round1_overrides"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: f"ovr-{uuid.uuid4().hex[:18]}")
    team_identifier: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    checkpoint_number: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    performed_by: Mapped[str] = mapped_column(String(40), ForeignKey("event_accounts.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Round1FinishOutcome(Base):
    """Immutable finish order used to enforce the first-16 qualification gate."""

    __tablename__ = "round1_finish_outcomes"
    __table_args__ = (UniqueConstraint("rank", name="uq_round1_finish_rank"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: f"fin-{uuid.uuid4().hex[:18]}")
    team_id: Mapped[str] = mapped_column(String(50), ForeignKey("teams.id"), nullable=False, unique=True, index=True)
    team_identifier: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    is_qualified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    points_snapshot: Mapped[float] = mapped_column(Float, nullable=False, default=400.0)


class Round1SecretAgentSelection(Base):
    """One confidential agent nomination per team, entered before the hunt begins."""

    __tablename__ = "round1_secret_agent_selections"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: f"agent-{uuid.uuid4().hex[:18]}")
    team_id: Mapped[str] = mapped_column(String(50), ForeignKey("teams.id"), nullable=False, unique=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(120), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
