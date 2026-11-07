import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
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
    phone_number: Mapped[str | None] = mapped_column(String(24), nullable=True)
    skills: Mapped[str] = mapped_column(Text, default="", nullable=False)
    linkedin_url: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class AxiomLoginGuard(Base):
    """Persistent brute-force guard for the private Axiom roster.

    Unlike the short in-memory burst throttle, this state survives API restarts
    and applies consistently when Render runs more than one worker.
    """

    __tablename__ = "axiom_login_guards"

    account_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("event_accounts.id"), primary_key=True
    )
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    __table_args__ = (
        UniqueConstraint("mentor_account_id", "client_request_id", name="uq_axiom_project_publish_request"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    mentor_account_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("event_accounts.id"), index=True, nullable=False
    )
    statement_slot: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    client_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
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


class AxiomOriginalityAgreement(Base):
    __tablename__ = "axiom_originality_agreements"

    account_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("event_accounts.id"), primary_key=True
    )
    agreement_version: Mapped[str] = mapped_column(String(40), nullable=False, default="axiom-v1")
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class AxiomProjectAccessAgreement(Base):
    """Append-only evidence of access to confidential Project Axiom briefs.

    The evidence seal is a server-side HMAC over the canonical signing record.
    It lets the platform detect post-signing record modification without storing
    raw network identifiers.
    """

    __tablename__ = "axiom_project_access_agreements"
    __table_args__ = (
        UniqueConstraint("account_id", "agreement_version", name="uq_axiom_access_agreement_version"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    account_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("event_accounts.id"), index=True, nullable=False
    )
    signed_email: Mapped[str] = mapped_column(String(255), nullable=False)
    signer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    agreement_version: Mapped[str] = mapped_column(String(40), nullable=False)
    document_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signature_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_seal: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AxiomProjectApplication(Base):
    """A participant's private solution/application for one project brief."""

    __tablename__ = "axiom_project_applications"
    __table_args__ = (
        UniqueConstraint("participant_account_id", "statement_id", name="uq_axiom_project_application"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    participant_account_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("event_accounts.id"), index=True, nullable=False
    )
    statement_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("axiom_problem_statements.id"), index=True, nullable=False
    )
    proposed_solution: Mapped[str] = mapped_column(Text, nullable=False)
    contribution: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class AxiomProjectTeamSelection(Base):
    """Publisher-controlled team choices. A project has at most three invitees."""

    __tablename__ = "axiom_project_team_selections"
    __table_args__ = (
        UniqueConstraint("statement_id", "participant_account_id", name="uq_axiom_project_selection"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    statement_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("axiom_problem_statements.id"), index=True, nullable=False
    )
    participant_account_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("event_accounts.id"), index=True, nullable=False
    )
    selected_by_account_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("event_accounts.id"), nullable=False
    )
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AxiomProjectPreference(Base):
    __tablename__ = "axiom_project_preferences"
    __table_args__ = (
        UniqueConstraint("participant_account_id", "statement_id", name="uq_axiom_participant_statement"),
        UniqueConstraint("participant_account_id", "preference_rank", name="uq_axiom_participant_rank"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    participant_account_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("event_accounts.id"), index=True, nullable=False
    )
    statement_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("axiom_problem_statements.id"), index=True, nullable=False
    )
    preference_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    proposed_solution: Mapped[str] = mapped_column(Text, nullable=False)
    contribution: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
