import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class AxiomRosterType(str, enum.Enum):
    MENTOR_CANDIDATE = "MENTOR_CANDIDATE"
    MEMBER = "MEMBER"


class AxiomRoleChoice(str, enum.Enum):
    PENDING = "PENDING"
    MENTOR = "MENTOR"
    PARTICIPANT = "PARTICIPANT"
    OPTED_OUT = "OPTED_OUT"


class AxiomProfile(Base):
    """Project Axiom identity attached to an event login account."""

    __tablename__ = "axiom_profiles"

    account_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("event_accounts.id"), primary_key=True
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    college_email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    roster_type: Mapped[AxiomRosterType] = mapped_column(
        Enum(AxiomRosterType, name="axiom_roster_type_enum"), nullable=False
    )
    role_choice: Mapped[AxiomRoleChoice] = mapped_column(
        Enum(AxiomRoleChoice, name="axiom_role_choice_enum"),
        default=AxiomRoleChoice.PENDING,
        nullable=False,
    )
    is_program_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class AxiomBootstrapState(Base):
    """Records one-time production roster changes across service restarts."""

    __tablename__ = "axiom_bootstrap_state"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class AxiomStatementStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"


class AxiomProblemStatement(Base):
    __tablename__ = "axiom_problem_statements"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    mentor_account_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("event_accounts.id"), unique=True, index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    project_track: Mapped[str] = mapped_column(String(20), nullable=False, default="RESEARCH")
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    project_context: Mapped[str] = mapped_column(Text, nullable=False)
    helpful_skills: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[AxiomStatementStatus] = mapped_column(
        Enum(AxiomStatementStatus, name="axiom_statement_status_enum"),
        default=AxiomStatementStatus.DRAFT,
        nullable=False,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
