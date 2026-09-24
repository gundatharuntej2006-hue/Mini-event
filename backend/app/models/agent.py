"""
Secret Agent Track Models for EVENT HQ.
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Manages confidential undercover agent assignments (exactly one active agent per team)
and sabotages/tasks with +50 points reward upon organizer verification.
"""

import uuid
import enum
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    String, Float, DateTime, ForeignKey, Enum, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now
from app.core.constants import AGENT_TASK_REWARD

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.participant import Participant


class AgentDossierStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPROMISED = "COMPROMISED"
    REVEALED = "REVEALED"
    DEACTIVATED = "DEACTIVATED"


class AgentTaskStatus(str, enum.Enum):
    ASSIGNED = "ASSIGNED"
    SUBMITTED = "SUBMITTED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class SecretAgentDossier(Base):
    """
    Confidential record linking an undercover agent to their assigned squad.
    Security & Privacy Rules:
    - Exactly one active agent per squad.
    - Restricted to ORGANIZER / MARSHAL roles; MUST NEVER be exposed via public team/participant APIs.
    """
    __tablename__ = "secret_agent_dossiers"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: f"sad-{uuid.uuid4().hex[:8]}"
    )
    team_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="RESTRICT"),
        unique=True,
        index=True,
        nullable=False
    )
    participant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("participants.id", ondelete="RESTRICT"),
        unique=True,
        index=True,
        nullable=False
    )
    codename: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    status: Mapped[AgentDossierStatus] = mapped_column(
        Enum(AgentDossierStatus, name="agent_dossier_status_enum", create_constraint=True),
        default=AgentDossierStatus.ACTIVE,
        nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
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
    team: Mapped["Team"] = relationship("Team", back_populates="secret_agent_dossier")
    participant: Mapped["Participant"] = relationship("Participant")
    tasks: Mapped[List["SecretAgentTask"]] = relationship(
        "SecretAgentTask",
        back_populates="dossier",
        cascade="all, delete-orphan",
        order_by="SecretAgentTask.created_at.asc()"
    )


class SecretAgentTask(Base):
    """
    Undercover task/sabotage assigned to a secret agent.
    Upon organizer review and verification, awards canonical AGENT_TASK_REWARD (+50 points).
    """
    __tablename__ = "secret_agent_tasks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: f"sat-{uuid.uuid4().hex[:8]}"
    )
    dossier_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("secret_agent_dossiers.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    task_description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    status: Mapped[AgentTaskStatus] = mapped_column(
        Enum(AgentTaskStatus, name="agent_task_status_enum", create_constraint=True),
        default=AgentTaskStatus.ASSIGNED,
        nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    evidence_reference: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    organizer_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    reward_points: Mapped[float] = mapped_column(
        Float,
        default=AGENT_TASK_REWARD,
        nullable=False
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
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
    dossier: Mapped["SecretAgentDossier"] = relationship("SecretAgentDossier", back_populates="tasks")
