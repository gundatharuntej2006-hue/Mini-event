from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict

from app.core.constants import DEFAULT_R1_HINT_PENALTY_SECONDS, R1_RULE_VIOLATIONS

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

class RuleViolationInput(BaseModel):
    """
    One ODDyssey Section 4 rule violation logged against a Round 1 gate.

    `count` is the gate's new total for that violation, not an increment, so a
    marshal corrects a mis-entry by writing the right number.
    """
    mini_round_number: int = Field(..., ge=1, le=3)
    violation: str = Field(
        ...,
        description=f"One of: {', '.join(R1_RULE_VIOLATIONS)}",
    )
    count: int = Field(default=1, ge=0)
    # "Moving or damaging a clue: -20 points OR disqualification." The marshal
    # chooses; the platform never escalates on its own.
    disqualify: bool = False

class Round1ConfigSchema(BaseModel):
    # Was 120 - two minutes - which contradicted the plan's "+5 minutes" and
    # would have been served to any client that read a config with the field
    # missing.
    penalty_per_hint_seconds: int = DEFAULT_R1_HINT_PENALTY_SECONDS
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
    # ODDyssey Section 4 rule penalties, alongside the hint penalty.
    phone_use_count: int = 0
    separation_count: int = 0
    clue_damage_count: int = 0
    rule_penalty_seconds: int = 0
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
    total_hint_penalty_seconds: int = 0
    total_rule_penalty_seconds: int = 0
    clue_damage_count: int = 0
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
