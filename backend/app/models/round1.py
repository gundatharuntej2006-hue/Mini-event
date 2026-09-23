from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base

class Round1ConfigModel(Base):
    __tablename__ = "round1_config"

    id = Column(Integer, primary_key=True, default=1)
    penalty_per_hint_seconds = Column(Integer, default=120, nullable=False)
    checkpoint_names = Column(JSON, default=lambda: ["Checkpoint Alpha", "Checkpoint Bravo", "Checkpoint Charlie"])
    is_finalized = Column(Boolean, default=False, nullable=False)
    finalized_at = Column(DateTime, nullable=True)
    finalized_by = Column(String(100), nullable=True)

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
    adjusted_seconds = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
