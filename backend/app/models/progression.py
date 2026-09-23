from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base

class RoundQualification(Base):
    """
    Authoritative record of finalized qualification across tournament rounds.
    Immutable once created, unless explicit audit resolution occurs.
    """
    __tablename__ = "round_qualifications"

    id = Column(String(100), primary_key=True, index=True)
    round_number = Column(Integer, nullable=False, index=True)
    team_id = Column(String(50), ForeignKey("teams.id"), nullable=False, index=True)
    rank = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False)  # 'Finalized Qualified' | 'Finalized Eliminated'
    score_snapshot = Column(Float, nullable=True)
    is_advancing = Column(Boolean, default=False, nullable=False)
    finalized_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    finalized_by = Column(String(100), nullable=False)

class TieReview(Base):
    """
    Generic tie-review record when ranking metrics result in unresolved cutoff ties.
    Prevents silent winner selection.
    """
    __tablename__ = "tie_reviews"

    id = Column(String(100), primary_key=True, index=True)
    round_number = Column(Integer, nullable=False, index=True)
    teams_involved = Column(JSON, nullable=False)  # List of {team_id, team_number, team_name, score}
    ranking_metric = Column(String(100), nullable=False)
    cutoff_position = Column(Integer, nullable=False)
    tie_breaker_status = Column(String(50), default="EXHAUSTED")
    review_status = Column(String(50), default="PENDING_REVIEW", index=True)  # PENDING_REVIEW | RESOLVED | BLOCKED
    organizer_decision = Column(String(100), nullable=True)
    advancing_team_ids = Column(JSON, nullable=True)
    eliminated_team_ids = Column(JSON, nullable=True)
    decision_timestamp = Column(DateTime, nullable=True)
    decided_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AuditLog(Base):
    """
    Authoritative audit event log for tournament actions.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(100), nullable=False, index=True)
    round_number = Column(Integer, nullable=True, index=True)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=False)
    actor_id = Column(String(100), nullable=False)
    actor_role = Column(String(50), nullable=False)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
