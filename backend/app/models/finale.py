from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Text, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base

def default_finale_criteria():
    return [
        {"id": "climax_defense", "name": "Grand Finale Oral Defense & Case Climax", "maxMarks": 50, "weight": 1.0, "isConfirmed": False},
        {"id": "cross_examination", "name": "Grand Panel Cross-Examination & Q&A", "maxMarks": 30, "weight": 1.0, "isConfirmed": False},
        {"id": "synergy_decorum", "name": "Team Cohesion & Courtroom Decorum", "maxMarks": 20, "weight": 1.0, "isConfirmed": False}
    ]

class FinaleConfigModel(Base):
    __tablename__ = "finale_config"

    id = Column(Integer, primary_key=True, default=1)
    is_scoring_rules_confirmed = Column(Boolean, default=False, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    confirmed_by = Column(String(100), nullable=True)
    criteria = Column(JSON, default=default_finale_criteria, nullable=False)
    round4_score_carried_over = Column(Boolean, default=True, nullable=False)
    round4_score_weight = Column(Float, default=0.2, nullable=False)
    finale_activity_weight = Column(Float, default=1.0, nullable=False)
    agent_bonus_points_for_correct = Column(Float, nullable=True)
    agent_penalty_points_for_incorrect = Column(Float, nullable=True)
    scoring_direction = Column(String(50), default="higher_wins", nullable=False)
    is_finalized = Column(Boolean, default=False, nullable=False)
    finalized_at = Column(DateTime, nullable=True)
    finalized_by = Column(String(100), nullable=True)

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
