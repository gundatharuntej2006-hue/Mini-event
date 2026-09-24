import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Text, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base
from app.core.constants import (
    R4_FINALISTS,
    R4_ADVANCING_COUNT,
    R4_MAX_SCORE,
    R4_RUBRIC_LOGICAL_STRUCTURE_MAX,
    R4_RUBRIC_EVIDENCE_MAX,
    R4_RUBRIC_REBUTTAL_MAX,
    R4_RUBRIC_RESOURCE_PERSON_MAX,
    R4_RUBRIC_PRESENTATION_TEAMWORK_MAX,
    R4_RUBRIC_TIME_MAX,
    R4_RUBRIC_TOTAL_MAX,
    DEFAULT_CARRYOVER_WEIGHT_PERCENT,
    AGENT_CORRECT_GUESS,
    AGENT_WRONG_GUESS,
)


def default_round4_rubric():
    return [
        {"id": "logical_structure", "name": "Logical Structure", "maxMarks": int(R4_RUBRIC_LOGICAL_STRUCTURE_MAX), "isConfirmed": False},
        {"id": "evidence", "name": "Use of Evidence", "maxMarks": int(R4_RUBRIC_EVIDENCE_MAX), "isConfirmed": False},
        {"id": "rebuttal", "name": "Rebuttal", "maxMarks": int(R4_RUBRIC_REBUTTAL_MAX), "isConfirmed": False},
        {"id": "resource_person_questioning", "name": "Questioning the Resource Person", "maxMarks": int(R4_RUBRIC_RESOURCE_PERSON_MAX), "isConfirmed": False},
        {"id": "presentation_teamwork", "name": "Presentation and Teamwork", "maxMarks": int(R4_RUBRIC_PRESENTATION_TEAMWORK_MAX), "isConfirmed": False},
        {"id": "time", "name": "Time Management", "maxMarks": int(R4_RUBRIC_TIME_MAX), "isConfirmed": False},
    ]


def default_final_score_formula():
    return {
        "panelScoreWeight": 1.0,
        "agentGuessingWeight": 1.0,
        "blackMarketWeightPercent": DEFAULT_CARRYOVER_WEIGHT_PERCENT,
        "isFormulaConfirmed": False,
        "confirmedAt": None,
        "confirmedBy": None,
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
    advancing_teams_count = Column(Integer, default=R4_ADVANCING_COUNT, nullable=True)
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
    scores = Column("scores_json", JSON, default=dict, nullable=False)
    total_score = Column(Float, nullable=False)
    is_submitted = Column(Boolean, default=True, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    comments = Column(Text, nullable=True)

    @property
    def scores_json(self):
        return self.scores

    @scores_json.setter
    def scores_json(self, value):
        self.scores = value


class Round4AgentGuessModel(Base):
    __tablename__ = "round4_agent_guesses"
    __table_args__ = {"extend_existing": True}

    id = Column(String(100), primary_key=True, default=lambda: f"r4ag-{uuid.uuid4().hex[:8]}")
    team_id = Column(String(50), ForeignKey("teams.id"), primary_key=True)
    outcome = Column(String(50), default="none", nullable=False)
    points_awarded = Column(Float, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
