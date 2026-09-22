import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey,
    UniqueConstraint, JSON, Enum, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now


class RoundState(Base):
    """Stores high-level metadata and configuration for each tournament round (1 to 5)."""
    __tablename__ = "round_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True) # 1..5
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    codename: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    initial_teams_count: Mapped[int] = mapped_column(Integer, default=32, nullable=False)
    qualifying_teams_count: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Scheduled", nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str] = mapped_column(String(255), default="Main Auditorium / Campus Grounds", nullable=False)
    
    is_finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


# =========================================================================
# ROUND 1: Clue Hunt / Expedition
# =========================================================================
class Round1Record(Base):
    __tablename__ = "round1_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: f"r1-{uuid.uuid4().hex[:8]}")
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    
    mini_rounds_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    raw_total_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_penalty_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    adjusted_total_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fastest_mini_round_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    qualification_status: Mapped[str] = mapped_column(String(50), default="Incomplete", nullable=False)
    tie_requires_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tie_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    hidden_code_recovered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hidden_code_recovered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    hidden_code_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    last_edited_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    team = relationship("Team")


# =========================================================================
# ROUND 2: Cabo
# =========================================================================
class Round2Placement(Base):
    __tablename__ = "round2_placements"
    __table_args__ = (
        UniqueConstraint("game_number", "team_id", name="uq_round2_game_team"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: f"r2p-{uuid.uuid4().hex[:8]}")
    game_number: Mapped[int] = mapped_column(Integer, nullable=False) # 1, 2, or 3
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False)
    placement: Mapped[int] = mapped_column(Integer, nullable=False) # 1..24
    points: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    team = relationship("Team")


# =========================================================================
# ROUND 3: The Black Market
# =========================================================================
class Round3Transaction(Base):
    __tablename__ = "round3_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: f"r3tx-{uuid.uuid4().hex[:8]}")
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False) # earn, spend, adjustment, reversal
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    organizer_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    is_reversed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reversal_transaction_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    reversed_transaction_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    team = relationship("Team")


class Round3CodeRecord(Base):
    __tablename__ = "round3_code_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: f"r3c-{uuid.uuid4().hex[:8]}")
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    fragments_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    team = relationship("Team")


# =========================================================================
# ROUND 4: The Legal Battle
# =========================================================================
class Round4Pair(Base):
    __tablename__ = "round4_pairs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: f"pair-{uuid.uuid4().hex[:6]}")
    pair_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False) # 1 to 4
    team_a_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    team_b_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    case_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    case_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    case_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    team_a_side: Mapped[str] = mapped_column(String(100), default="Prosecution / Plaintiff", nullable=False)
    team_b_side: Mapped[str] = mapped_column(String(100), default="Defense / Respondent", nullable=False)
    
    team_a_has_case_file: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    team_a_case_file_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    team_a_has_opposing_file: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    team_a_opposing_file_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    team_b_has_case_file: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    team_b_case_file_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    team_b_has_opposing_file: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    team_b_opposing_file_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    stages_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    resource_person_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resource_person_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resource_person_questions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_questioning_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    team_a = relationship("Team", foreign_keys=[team_a_id])
    team_b = relationship("Team", foreign_keys=[team_b_id])


class Round4JudgeScore(Base):
    __tablename__ = "round4_judge_scores"
    __table_args__ = (
        UniqueConstraint("judge_id", "team_id", name="uq_round4_judge_team"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: f"r4js-{uuid.uuid4().hex[:8]}")
    judge_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    judge_name: Mapped[str] = mapped_column(String(255), nullable=False)
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False)
    scores_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False) # categoryId -> mark
    total_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    is_submitted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    team = relationship("Team")


class Round4AgentGuess(Base):
    __tablename__ = "round4_agent_guesses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: f"r4ag-{uuid.uuid4().hex[:8]}")
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    outcome: Mapped[str] = mapped_column(String(50), default="none", nullable=False) # correct, incorrect, pending, none
    points_awarded: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    team = relationship("Team")


# =========================================================================
# GRAND FINALE (Round 5)
# =========================================================================
class FinaleScorecard(Base):
    __tablename__ = "finale_scorecards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: f"finsc-{uuid.uuid4().hex[:8]}")
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    judge_name: Mapped[str] = mapped_column(String(255), default="Grand Jury Panel", nullable=False)
    scores_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False) # criterionId -> score
    total_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_edited_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    team = relationship("Team")


class FinaleAgentVerdict(Base):
    __tablename__ = "finale_agent_verdicts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: f"finav-{uuid.uuid4().hex[:8]}")
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    suspected_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actual_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    bonus_points: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    penalty_points: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    team = relationship("Team")