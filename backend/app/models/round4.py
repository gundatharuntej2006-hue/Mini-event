import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Text, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base

def default_round4_rubric():
    return [
        {"id": "logical_structure", "name": "Logical structure", "maxMarks": 20, "isConfirmed": False},
        {"id": "evidence_use", "name": "Use of evidence", "maxMarks": 20, "isConfirmed": False},
        {"id": "rebuttal", "name": "Rebuttal", "maxMarks": 20, "isConfirmed": False},
        {"id": "resource_questioning", "name": "Questioning the resource person", "maxMarks": 15, "isConfirmed": False},
        {"id": "presentation_teamwork", "name": "Presentation and teamwork", "maxMarks": 15, "isConfirmed": False},
        {"id": "time_management", "name": "Time management", "maxMarks": 10, "isConfirmed": False}
    ]

def default_final_score_formula():
    return {
        "panelScoreWeight": 1.0,
        "agentGuessingWeight": 1.0,
        "blackMarketWeightPercent": 10,
        "isFormulaConfirmed": False,
        "confirmedAt": None,
        "confirmedBy": None
    }

class Round4ConfigModel(Base):
    __tablename__ = "round4_config"

    id = Column(Integer, primary_key=True, default=1)
    rubric_categories = Column(JSON, default=default_round4_rubric, nullable=False)
    is_rubric_confirmed = Column(Boolean, default=False, nullable=False)
    judge_aggregation = Column(String(50), default="average", nullable=False)
    judges_list = Column(JSON, default=lambda: [{"id": "judge-1", "name": "Faculty Judge 1"}, {"id": "judge-2", "name": "Faculty Judge 2"}])
    is_guessing_rules_configured = Column(Boolean, default=False, nullable=False)
    guessing_points_for_correct = Column(Float, nullable=True)
    guessing_points_for_incorrect = Column(Float, nullable=True)
    final_score_formula = Column(JSON, default=default_final_score_formula, nullable=False)
    advancing_teams_count = Column(Integer, default=3, nullable=True)
    is_finalized = Column(Boolean, default=False, nullable=False)
    finalized_at = Column(DateTime, nullable=True)
    finalized_by = Column(String(100), nullable=True)

from app.models.round_models import Round4Pair
Round4PairModel = Round4Pair

class Round4StageTimingModel(Base):
    __tablename__ = "round4_stages"

    id = Column(String(100), primary_key=True)  # r4-{pair_id}-{stage_id}
    pair_id = Column(String(50), ForeignKey("round4_pairs.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_id = Column(String(50), nullable=False)  # prep_1 | hearing_1 | file_exchange | prep_2 | hearing_2
    status = Column(String(50), default="not_started", nullable=False)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    actual_duration_seconds = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

class Round4JudgeScoreModel(Base):
    __tablename__ = "round4_judge_scores"
    __table_args__ = {"extend_existing": True}

    id = Column(String(100), primary_key=True, default=lambda: f"r4js-{uuid.uuid4().hex[:8]}")  # js-{judge_id}-{team_id}
    judge_id = Column(String(50), nullable=False)
    judge_name = Column(String(100), nullable=False)
    team_id = Column(String(50), ForeignKey("teams.id"), nullable=False)
    scores = Column(JSON, default=dict, nullable=False)
    total_score = Column(Float, nullable=False)
    is_submitted = Column(Boolean, default=False, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    comments = Column(Text, nullable=True)

class Round4AgentGuessModel(Base):
    __tablename__ = "round4_agent_guesses"
    __table_args__ = {"extend_existing": True}

    team_id = Column(String(50), ForeignKey("teams.id"), primary_key=True)
    outcome = Column(String(50), default="none", nullable=False)
    points_awarded = Column(Float, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
