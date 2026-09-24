import uuid
import enum
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.participant import Participant
    from app.models.wallet import TeamWallet, WalletTransaction
    from app.models.cabo import CaboTableAssignment, CaboPlayerScorecard
    from app.models.agent import SecretAgentDossier
    from app.models.code_hunt import FinalCodeRecord
    from app.models.black_market import BlackMarketPurchase


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

    # Relationships - preserve participants and tournament audit records on team updates
    members: Mapped[List["Participant"]] = relationship(
        "Participant",
        back_populates="team",
        cascade="save-update, merge",
        order_by="Participant.role.desc(), Participant.name.asc()"
    )
    wallet: Mapped[Optional["TeamWallet"]] = relationship(
        "TeamWallet",
        back_populates="team",
        uselist=False,
        cascade="save-update, merge"
    )
    wallet_transactions: Mapped[List["WalletTransaction"]] = relationship(
        "WalletTransaction",
        back_populates="team",
        cascade="save-update, merge"
    )
    cabo_table_assignments: Mapped[List["CaboTableAssignment"]] = relationship(
        "CaboTableAssignment",
        back_populates="team",
        cascade="save-update, merge"
    )
    cabo_player_scorecards: Mapped[List["CaboPlayerScorecard"]] = relationship(
        "CaboPlayerScorecard",
        back_populates="team",
        cascade="save-update, merge"
    )
    secret_agent_dossier: Mapped[Optional["SecretAgentDossier"]] = relationship(
        "SecretAgentDossier",
        back_populates="team",
        uselist=False,
        cascade="save-update, merge"
    )
    final_code_record: Mapped[Optional["FinalCodeRecord"]] = relationship(
        "FinalCodeRecord",
        back_populates="team",
        uselist=False,
        cascade="save-update, merge"
    )
    black_market_purchases: Mapped[List["BlackMarketPurchase"]] = relationship(
        "BlackMarketPurchase",
        back_populates="team",
        cascade="save-update, merge"
    )