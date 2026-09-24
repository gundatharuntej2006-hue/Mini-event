import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base

from app.core.constants import (
    CABO_PLACEMENT_POINTS,
    CABO_GAMES,
    CABO_TABLE_SIZE,
    CABO_MAX_TEAM_SCORE,
    DEPRECATED_CABO_24_POINT_SCALE,
)

def default_cabo_point_table():
    """
    DEPRECATED: Legacy 24-point scale (24..1) used by initial round 2 prototype.
    Official tournament rule specifies table scoring (1st=5, 2nd=3, 3rd=2, 4th=1, 5th=0)
    across 5-player tables, max team score 75.
    Retained for backward-compatibility with existing unit tests.
    """
    return dict(DEPRECATED_CABO_24_POINT_SCALE)

class CaboConfigModel(Base):
    __tablename__ = "round2_config"

    id = Column(Integer, primary_key=True, default=1)
    scoring_direction = Column(String(50), default="higher_is_better", nullable=False)
    tie_policy = Column(String(50), default="strict_unique", nullable=False)
    point_table = Column(JSON, default=default_cabo_point_table, nullable=False)
    is_finalized = Column(Boolean, default=False, nullable=False)
    finalized_at = Column(DateTime, nullable=True)
    finalized_by = Column(String(100), nullable=True)

class CaboGameModel(Base):
    __tablename__ = "round2_games"

    id = Column(String(50), primary_key=True)  # r2-game-1, r2-game-2, r2-game-3
    game_number = Column(Integer, unique=True, nullable=False)  # 1, 2, 3
    name = Column(String(100), nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)

class CaboPlacementModel(Base):
    __tablename__ = "round2_cabo_placements"

    id = Column(String(100), primary_key=True)  # r2-g{game_num}-{team_id}
    game_id = Column(String(50), ForeignKey("round2_games.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id = Column(String(50), ForeignKey("teams.id"), nullable=False)
    placement = Column(Integer, nullable=False)  # 1 to 24
    points = Column(Float, nullable=False)
    notes = Column(String(255), nullable=True)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
