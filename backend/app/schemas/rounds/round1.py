from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict

class CheckpointInput(BaseModel):
    checkpoint_id: str
    name: str
    arrival_time: Optional[str] = None

class MiniRoundTimingInput(BaseModel):
    mini_round_number: int = Field(..., ge=1, le=3)
    start_time: Optional[str] = None
    completion_time: Optional[str] = None
    hints_used: int = Field(default=0, ge=0)
    checkpoints: Optional[List[CheckpointInput]] = None

class UpdateHintsInput(BaseModel):
    mini_round_number: int = Field(..., ge=1, le=3)
    hints_used: int = Field(..., ge=0)

class Round1ConfigSchema(BaseModel):
    penalty_per_hint_seconds: int = 120
    checkpoint_names: List[str] = []
    is_finalized: bool = False
    finalized_at: Optional[str] = None
    finalized_by: Optional[str] = None

class UpdateRound1ConfigInput(BaseModel):
    penalty_per_hint_seconds: Optional[int] = Field(None, ge=0)
    checkpoint_names: Optional[List[str]] = None

class MiniRoundTimingResponse(BaseModel):
    mini_round_number: int
    status: str
    start_time: Optional[str] = None
    completion_time: Optional[str] = None
    hints_used: int = 0
    hint_penalty_seconds: int = 0
    duration_seconds: Optional[int] = None
    adjusted_seconds: Optional[int] = None
    checkpoints: List[Any] = []

class TeamRound1RecordResponse(BaseModel):
    team_id: str
    team_number: int
    team_name: str
    mini_rounds: List[MiniRoundTimingResponse]
    raw_total_seconds: Optional[int] = None
    total_penalty_seconds: int = 0
    adjusted_total_seconds: Optional[int] = None
    fastest_mini_round_seconds: Optional[int] = None
    is_complete: bool = False
    rank: Optional[int] = None
    tie_requires_review: bool = False
    tie_reason: Optional[str] = None
    qualification_status: str

class Round1OverviewResponse(BaseModel):
    id: int = 1
    name: str = "Clue Hunt / Expedition"
    codename: str = "ROUND_1_CLUE_HUNT"
    status: str = "In Progress"
    isFinalized: bool = False
    config_json: Dict[str, Any] = Field(default_factory=dict, alias="configJson")
    config: Round1ConfigSchema
    records: List[TeamRound1RecordResponse]
    can_finalize: bool
    issues: List[Any] = []
    completed_count: int
    incomplete_count: int
    top24_cutoff_time: Optional[int] = None

    model_config = {
        "populate_by_name": True,
    }
