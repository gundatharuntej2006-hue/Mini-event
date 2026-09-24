import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base
from app.core.constants import (
    AGENT_CORRECT_GUESS,
    AGENT_WRONG_GUESS,
    AGENT_GUESS_MIN,
    AGENT_GUESS_MAX,
    DEFAULT_CARRYOVER_WEIGHT_PERCENT,
    PODIUM_SIZE,
    R4_ADVANCING_COUNT,
)

def default_finale_criteria():
    return [
        {"id": "climax_defense", "name": "Grand Finale Oral Defense & Case Climax", "maxMarks": 50, "weight": 1.0, "isConfirmed": False},
        {"id": "cross_examination", "name": "Grand Panel Cross-Examination & Q&A", "maxMarks": 30, "weight": 1.0, "isConfirmed": False},
        {"id": "synergy_decorum", "name": "Team Cohesion & Courtroom Decorum", "maxMarks": 20, "weight": 1.0, "isConfirmed": False}
    ]

class FinaleConfigModel(Base):
    __tablename__ = "finale_config"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, default=1)
    is_scoring_rules_confirmed = Column(Boolean, default=False, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    confirmed_by = Column(String(100), nullable=True)
    criteria = Column(JSON, default=default_finale_criteria, nullable=False)
    round4_score_carried_over = Column(Boolean, default=True, nullable=False)
    round4_score_weight = Column(Float, default=1.0, nullable=False)
    finale_activity_weight = Column(Float, default=1.0, nullable=False)
    advancing_teams_count = Column(Integer, default=R4_ADVANCING_COUNT, nullable=True)
    min_guesses = Column(Integer, default=AGENT_GUESS_MIN, nullable=False)
    max_guesses = Column(Integer, default=AGENT_GUESS_MAX, nullable=False)
    correct_guess_points = Column(Float, default=AGENT_CORRECT_GUESS, nullable=False)
    wrong_guess_points = Column(Float, default=AGENT_WRONG_GUESS, nullable=False)
    carryover_wallet_percent = Column(Float, default=DEFAULT_CARRYOVER_WEIGHT_PERCENT, nullable=False)
    is_guessing_open = Column(Boolean, default=True, nullable=False)
    scoring_direction = Column(String(50), default="higher_wins", nullable=False)
    is_finalized = Column(Boolean, default=False, nullable=False)
    finalized_at = Column(DateTime, nullable=True)
    finalized_by = Column(String(100), nullable=True)
    is_revealed = Column(Boolean, default=False, nullable=False)
    revealed_at = Column(DateTime, nullable=True)
    revealed_by = Column(String(100), nullable=True)
    is_top_four_revealed = Column(Boolean, default=False, nullable=False)
    top_four_revealed_at = Column(DateTime, nullable=True)
    top_four_revealed_by = Column(String(100), nullable=True)
    is_podium_revealed = Column(Boolean, default=False, nullable=False)
    podium_revealed_at = Column(DateTime, nullable=True)
    podium_revealed_by = Column(String(100), nullable=True)
    is_agents_revealed = Column(Boolean, default=False, nullable=False)
    agents_revealed_at = Column(DateTime, nullable=True)
    agents_revealed_by = Column(String(100), nullable=True)

class FinaleScorecardModel(Base):
    __tablename__ = "finale_scorecards"
    __table_args__ = {"extend_existing": True}

    team_id = Column(String(50), ForeignKey("teams.id"), primary_key=True)
    judge_name = Column(String(100), nullable=False)
    scores = Column(JSON, default=dict, nullable=False)
    total_score = Column(Float, nullable=True)
    is_complete = Column(Boolean, default=False, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    comments = Column(Text, nullable=True)

class FinaleAgentVerdictModel(Base):
    __tablename__ = "finale_agent_verdicts"
    __table_args__ = {"extend_existing": True}

    team_id = Column(String(50), ForeignKey("teams.id"), primary_key=True)
    suspected_agent = Column(String(100), nullable=True)
    actual_agent = Column(String(100), nullable=True)
    is_correct = Column(Boolean, nullable=True)
    bonus_points = Column(Float, nullable=True)
    penalty_points = Column(Float, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)


class FinaleTeamGuessSubmissionModel(Base):
    """
    Submission header containing all secret agent guesses for a finalist squad (1-5 guesses).
    """
    __tablename__ = "finale_team_guess_submissions"
    __table_args__ = {"extend_existing": True}

    id = Column(String(100), primary_key=True)  # fg-sub-{team_id}
    guessing_team_id = Column(String(50), ForeignKey("teams.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    total_guesses = Column(Integer, default=0, nullable=False)
    correct_guesses = Column(Integer, default=0, nullable=False)
    wrong_guesses = Column(Integer, default=0, nullable=False)
    total_guessing_points = Column(Float, default=0.0, nullable=False)
    is_submitted = Column(Boolean, default=True, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    submitted_by = Column(String(100), nullable=True)

    guesses = relationship("FinaleAgentGuessModel", back_populates="submission", cascade="all, delete-orphan", lazy="joined")


class FinaleAgentGuessModel(Base):
    """
    Individual agent unmasking guess targeting another team.
    Scores +30.0 for correct identification, -20.0 for wrong accusation.
    """
    __tablename__ = "finale_agent_guesses"
    __table_args__ = {"extend_existing": True}

    id = Column(String(100), primary_key=True, default=lambda: f"fag-{uuid.uuid4().hex[:8]}")
    submission_id = Column(String(100), ForeignKey("finale_team_guess_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    guessing_team_id = Column(String(50), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    target_team_id = Column(String(50), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    suspected_participant_id = Column(String(50), ForeignKey("participants.id", ondelete="SET NULL"), nullable=True)
    suspected_agent_name = Column(String(100), nullable=True)
    is_resolved = Column(Boolean, default=False, nullable=False)
    is_correct = Column(Boolean, nullable=True)
    points_awarded = Column(Float, default=0.0, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    submission = relationship("FinaleTeamGuessSubmissionModel", back_populates="guesses")


class FinaleChampionshipStandingModel(Base):
    """
    Final overall championship standings for the 8 finalist squads.
    Combines:
    - Legal Battle panel score (max 100.0)
    - Agent Guessing points (+30 correct, -20 wrong, 0 unguessed)
    - 10% Black Market wallet balance carryover
    """
    __tablename__ = "finale_championship_standings"
    __table_args__ = {"extend_existing": True}

    id = Column(String(100), primary_key=True)  # fcs-{team_id}
    team_id = Column(String(50), ForeignKey("teams.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    team_number = Column(Integer, nullable=False)
    team_name = Column(String(200), nullable=False)
    legal_battle_score = Column(Float, nullable=True)
    agent_guessing_points = Column(Float, default=0.0, nullable=False)
    remaining_black_market_points = Column(Float, default=0.0, nullable=False)
    black_market_carryover_points = Column(Float, default=0.0, nullable=False)
    final_score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=False)
    is_top_four = Column(Boolean, default=False, nullable=False)
    podium_position = Column(Integer, nullable=True)
    placement_title = Column(String(100), nullable=True)
    tie_requires_review = Column(Boolean, default=False, nullable=False)
    tie_reason = Column(Text, nullable=True)
    is_tie_resolved = Column(Boolean, default=True, nullable=False)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


# Class aliases for easy imports
FinaleTeamGuessSubmission = FinaleTeamGuessSubmissionModel
FinaleAgentGuess = FinaleAgentGuessModel
FinaleChampionshipStanding = FinaleChampionshipStandingModel
