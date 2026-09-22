import uuid
import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now


class TeamStatus(str, enum.Enum):
    REGISTERED = "Registered"
    CHECKED_IN = "Checked In"
    ACTIVE = "Active"
    ELIMINATED = "Eliminated"
    DISQUALIFIED = "Disqualified"


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: f"team-{uuid.uuid4().hex[:8]}"
    )
    team_number: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_table: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[TeamStatus] = mapped_column(
        Enum(TeamStatus, name="team_status_enum", create_constraint=True),
        default=TeamStatus.REGISTERED,
        nullable=False
    )
    current_round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_qualified_for_next_round: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    total_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships - preserve participants on team deletion
    members: Mapped[List["Participant"]] = relationship(
        "Participant",
        back_populates="team",
        cascade="save-update, merge",
        order_by="Participant.role.desc(), Participant.name.asc()"
    )