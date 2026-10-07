from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base
from app.core.constants import DEFAULT_R1_HINT_PENALTY_SECONDS, DEFAULT_R1_CHECKPOINTS

class Round1ConfigModel(Base):
    __tablename__ = "round1_config"

    id = Column(Integer, primary_key=True, default=1)
    penalty_per_hint_seconds = Column(Integer, default=DEFAULT_R1_HINT_PENALTY_SECONDS, nullable=False)
    checkpoint_names = Column(JSON, default=lambda: list(DEFAULT_R1_CHECKPOINTS))
    is_finalized = Column(Boolean, default=False, nullable=False)
    finalized_at = Column(DateTime, nullable=True)
    finalized_by = Column(String(100), nullable=True)
    started_at = Column(DateTime, nullable=True)
    started_by = Column(String(100), nullable=True)

class MiniRoundTimingModel(Base):
    __tablename__ = "round1_timings"

    id = Column(String(100), primary_key=True)  # r1-{team_id}-{mini_round_number}
    team_id = Column(String(50), ForeignKey("teams.id"), nullable=False, index=True)
    mini_round_number = Column(Integer, nullable=False)  # 1, 2, 3
    status = Column(String(50), default="Not Started")  # Not Started | In Progress | Completed
    start_time = Column(DateTime, nullable=True)
    completion_time = Column(DateTime, nullable=True)
    hints_used = Column(Integer, default=0, nullable=False)
    checkpoints = Column(JSON, default=list)
    duration_seconds = Column(Integer, nullable=True)
    hint_penalty_seconds = Column(Integer, default=0, nullable=False)
    phone_penalties_count = Column(Integer, default=0, nullable=False)
    phone_penalty_seconds = Column(Integer, default=0, nullable=False)
    separation_penalties_count = Column(Integer, default=0, nullable=False)
    separation_penalty_seconds = Column(Integer, default=0, nullable=False)
    # Migration a7b8c9d0e1f2 adds this column and round_service reads it in
    # three places, but the model never mapped it. Every call into
    # get_round1_records / update_round1_record therefore raised
    # AttributeError and the Round 1 records endpoints answered 500 - which is
    # the screen organisers use to enter and save Round 1 scores. The column
    # already exists in the database; only the mapping was missing.
    rule_penalty_seconds = Column(Integer, default=0, nullable=False)
    clue_tampering_deduction = Column(Integer, default=0, nullable=False)
    is_disqualified = Column(Boolean, default=False, nullable=False)
    disqualification_reason = Column(String(255), nullable=True)
    adjusted_seconds = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class GateCheckinModel(Base):
    __tablename__ = "round1_gate_checkins"

    id = Column(String(100), primary_key=True)  # chk-{uuid}
    team_id = Column(String(50), ForeignKey("teams.id"), nullable=False, index=True)
    team_name = Column(String(100), nullable=False)
    round_number = Column(Integer, default=1, nullable=False)
    gate_number = Column(Integer, nullable=False, index=True)  # 1, 2, 3
    scanned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    is_duplicate = Column(Boolean, default=False, nullable=False)
    attempt_number = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="VERIFIED", nullable=False)  # VERIFIED | DUPLICATE
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class Round1RouteAllocationModel(Base):
    """
    32 teams x 3 checkpoints allocation.
    Stores assigned physical location (1..8) and question set ('A'..'D') for each checkpoint.
    """
    __tablename__ = "round1_route_allocations"

    id = Column(String(100), primary_key=True)  # alloc-{team_identifier}
    team_identifier = Column(String(50), nullable=False, index=True, unique=True)  # e.g. "1001"
    team_id = Column(String(50), ForeignKey("teams.id"), nullable=True, index=True)
    team_name = Column(String(100), nullable=True)

    # Checkpoint 1 (R1.1)
    cp1_location = Column(Integer, nullable=False)  # 1..8
    cp1_set = Column(String(5), nullable=False)       # A, B, C, D
    cp1_completed = Column(Boolean, default=False, nullable=False)
    cp1_completed_at = Column(DateTime, nullable=True)
    cp1_attempts = Column(Integer, default=0, nullable=False)

    # Checkpoint 2 (R1.2)
    cp2_location = Column(Integer, nullable=False)  # 1..8
    cp2_set = Column(String(5), nullable=False)       # A, B, C, D
    cp2_completed = Column(Boolean, default=False, nullable=False)
    cp2_completed_at = Column(DateTime, nullable=True)
    cp2_attempts = Column(Integer, default=0, nullable=False)

    # Checkpoint 3 (R1.3)
    cp3_location = Column(Integer, nullable=False)  # 1..8
    cp3_set = Column(String(5), nullable=False)       # A, B, C, D
    cp3_completed = Column(Boolean, default=False, nullable=False)
    cp3_completed_at = Column(DateTime, nullable=True)
    cp3_attempts = Column(Integer, default=0, nullable=False)

    is_frozen = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Round1CheckpointAttemptModel(Base):
    """
    Logs every answer submission attempt at each checkpoint (max 3 allowed per checkpoint).
    Also logs scan validations / invalid scans.
    """
    __tablename__ = "round1_checkpoint_attempts"

    id = Column(String(100), primary_key=True)  # att-{uuid}
    team_identifier = Column(String(50), nullable=False, index=True)
    team_id = Column(String(50), ForeignKey("teams.id"), nullable=True)
    checkpoint_number = Column(Integer, nullable=False)  # 1, 2, 3
    location_number = Column(Integer, nullable=False)    # 1..8
    question_set = Column(String(5), nullable=False)     # A, B, C, D
    attempt_number = Column(Integer, nullable=False)     # 1, 2, 3
    submitted_answer = Column(String(255), nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class Round1ParticipantSessionModel(Base):
    """
    Temporary signed session for participant device bound to 4-digit Team ID.
    Prevents front-end tampering and cross-team impersonation.
    """
    __tablename__ = "round1_participant_sessions"

    id = Column(String(100), primary_key=True)  # sess-{token_hash_or_uuid}
    session_token = Column(String(100), unique=True, nullable=False, index=True)
    team_identifier = Column(String(50), nullable=False, index=True)
    team_id = Column(String(50), ForeignKey("teams.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_active_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True, nullable=False)

