import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
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
