from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class CaboPlacementInput(BaseModel):
    team_id: str
    placement: int = Field(..., ge=1, le=24)
    notes: Optional[str] = None

class RecordGamePlacementsInput(BaseModel):
    placements: List[CaboPlacementInput]

class CaboConfigSchema(BaseModel):
    scoring_direction: str = "higher_is_better"
    tie_policy: str = "strict_unique"
    point_table: Dict[str, float] = {}
    is_finalized: bool = False
    finalized_at: Optional[str] = None
    finalized_by: Optional[str] = None

class UpdateCaboConfigInput(BaseModel):
    scoring_direction: Optional[str] = None
    point_table: Optional[Dict[str, float]] = None

class CaboGameResponse(BaseModel):
    id: str
    game_number: int
    name: str
    is_completed: bool
    placements: Dict[str, Any] = {}

class TeamRound2RecordResponse(BaseModel):
    team_id: str
    team_number: int
    team_name: str
    round1_qualified: bool
    game1_placement: Optional[int] = None
    game1_points: Optional[float] = None
    game2_placement: Optional[int] = None
    game2_points: Optional[float] = None
    game3_placement: Optional[int] = None
    game3_points: Optional[float] = None
    total_points: Optional[float] = None
    games_completed_count: int = 0
    is_complete: bool = False
    rank: Optional[int] = None
    tie_requires_review: bool = False
    tie_reason: Optional[str] = None
    qualification_status: str

class Round2OverviewResponse(BaseModel):
    config: CaboConfigSchema
    games: List[CaboGameResponse]
    records: List[TeamRound2RecordResponse]
    can_finalize: bool
    issues: List[Any] = []
    ties_affecting_cutoff: bool = False
    complete_count: int = 0
    incomplete_count: int = 0
