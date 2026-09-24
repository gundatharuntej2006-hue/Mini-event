"""
Final Code Gate and Fragment Hunt Models for EVENT HQ.
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Manages the 2-fragment QR/physical clue recovery across Round 1 (Expedition)
and Round 2 (Cabo), gatekeeping entry into Round 4 (The Legal Battle).
"""

import uuid
import enum
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.team import Team


class FragmentStatus(str, enum.Enum):
    PENDING = "PENDING"
    RECOVERED = "RECOVERED"
    PURCHASED = "PURCHASED"
    MISSING = "MISSING"


class FinalCodeRecord(Base):
    """
    Tracks squad code recovery for Fragment 1 (R1) and Fragment 2 (R2).
    Both fragments compose the Final Code gate required to participate in Round 4.
    """
    __tablename__ = "final_code_records"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: f"fcr-{uuid.uuid4().hex[:8]}"
    )
    team_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="RESTRICT"),
        unique=True,
        index=True,
        nullable=False
    )
    fragment_1_status: Mapped[FragmentStatus] = mapped_column(
        Enum(FragmentStatus, name="fragment_status_enum", create_constraint=True),
        default=FragmentStatus.PENDING,
        nullable=False
    )
    fragment_1_value: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    fragment_1_discovered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    fragment_2_status: Mapped[FragmentStatus] = mapped_column(
        Enum(FragmentStatus, name="fragment_status_enum", create_constraint=False),
        default=FragmentStatus.PENDING,
        nullable=False
    )
    fragment_2_value: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    fragment_2_discovered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    final_code_assembled: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    final_code_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    verified_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    verification_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
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
    team: Mapped["Team"] = relationship("Team", back_populates="final_code_record")
