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
    phone_penalties_count: int = Field(default=0, ge=0)
    separation_penalties_count: int = Field(default=0, ge=0)
    clue_tampering_deduction: int = Field(default=0, ge=0)
    is_disqualified: bool = Field(default=False)
    disqualification_reason: Optional[str] = None
    checkpoints: Optional[List[CheckpointInput]] = None

class UpdateHintsInput(BaseModel):
    mini_round_number: int = Field(..., ge=1, le=3)
    hints_used: int = Field(..., ge=0)

class Round1ConfigSchema(BaseModel):
    penalty_per_hint_seconds: int = 300
    phone_penalty_seconds: int = 600
    separation_penalty_seconds: int = 300
    checkpoint_names: List[str] = []
    is_finalized: bool = False
    finalized_at: Optional[str] = None
    finalized_by: Optional[str] = None
    started_at: Optional[str] = None
    started_by: Optional[str] = None
    is_started: bool = False

class UpdateRound1ConfigInput(BaseModel):
    penalty_per_hint_seconds: Optional[int] = Field(None, ge=0)
    phone_penalty_seconds: Optional[int] = Field(None, ge=0)
    separation_penalty_seconds: Optional[int] = Field(None, ge=0)
    checkpoint_names: Optional[List[str]] = None

class MiniRoundTimingResponse(BaseModel):
    mini_round_number: int
    gate_name: Optional[str] = None
    status: str
    start_time: Optional[str] = None
    completion_time: Optional[str] = None
    hints_used: int = 0
    hint_penalty_seconds: int = 0
    phone_penalties_count: int = 0
    phone_penalty_seconds: int = 0
    separation_penalties_count: int = 0
    separation_penalty_seconds: int = 0
    clue_tampering_deduction: int = 0
    is_disqualified: bool = False
    disqualification_reason: Optional[str] = None
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
    rank_points: Optional[int] = None
    point_deductions: int = 0
    net_score_points: Optional[int] = None
    is_disqualified: bool = False
    disqualification_reason: Optional[str] = None
    gate_1_fragment_status: str = "PENDING"
    gate_2_fragment_status: str = "PENDING"
    gate_3_confirmed: bool = False
    tie_requires_review: bool = False
    tie_reason: Optional[str] = None
    qualification_status: str
    gate_1_seconds: Optional[int] = None
    gate_2_seconds: Optional[int] = None
    gate_3_seconds: Optional[int] = None

class StartRound1Response(BaseModel):
    is_started: bool = True
    started_at: str
    started_by: str
    round_number: int = 1
    message: str

class Round1OverviewResponse(BaseModel):
    id: int = 1
    name: str = "The ODDyssey Protocol"
    codename: str = "ROUND_1_ODDYSSEY_PROTOCOL"
    status: str = "In Progress"
    isFinalized: bool = False
    started_at: Optional[str] = None
    is_started: bool = False
    config_json: Dict[str, Any] = Field(default_factory=dict, alias="configJson")
    config: Round1ConfigSchema
    records: List[TeamRound1RecordResponse]
    can_finalize: bool
    issues: List[Any] = []
    completed_count: int
    incomplete_count: int
    top16_cutoff_time: Optional[int] = None
    top24_cutoff_time: Optional[int] = None

    model_config = {
        "populate_by_name": True,
    }

class GateCheckinInput(BaseModel):
    team_name: Optional[str] = None
    team_id: Optional[str] = None
    team_identifier: Optional[str] = None  # e.g., "1024", "0001", "1", "T01"

class GateNavigationResponse(BaseModel):
    raw_text: str
    system_status: str
    fragment_info: str
    access_key: Optional[str] = None
    protocol_status: Optional[str] = None
    instructions: str
    fallback_instructions: str

class GateCheckinResponse(BaseModel):
    checkin_id: str
    team_id: str
    team_name: str
    team_number: int
    round_number: int = 1
    gate_number: int
    scanned_at: str
    official_scanned_at: str
    is_duplicate: bool
    attempt_number: int
    status: str
    notes: Optional[str] = None
    split_seconds: Optional[int] = None
    split_time_formatted: Optional[str] = None
    navigation: GateNavigationResponse

class GateCheckinSummaryItem(BaseModel):
    id: str
    team_id: str
    team_name: str
    round_number: int = 1
    gate_number: int
    scanned_at: str
    is_duplicate: bool
    attempt_number: int
    status: str
    notes: Optional[str] = None


# ==============================================================================
# Round 1 Final Spec — Participant Session & Allocation Schemas
# ==============================================================================

class ParticipantSessionRequest(BaseModel):
    team_identifier: str  # 4-digit Team ID e.g. "1001"

class ParticipantSessionResponse(BaseModel):
    session_token: str
    team_identifier: str
    team_name: str
    current_checkpoint: int  # 1, 2, 3, or 4 (4 = complete)
    is_round_active: bool
    is_complete: bool

class ParticipantCurrentStateResponse(BaseModel):
    team_identifier: str
    team_name: str
    current_checkpoint: int  # 1, 2, 3, or 4
    current_location_number: Optional[int] = None
    location_name: Optional[str] = None
    location_riddle: Optional[str] = None
    location_target: Optional[str] = None
    qr_scanned: bool = False
    attempts_used: int = 0
    attempts_remaining: int = 3
    is_locked: bool = False
    is_round_active: bool = False
    is_complete: bool = False
    status_message: str

class ParticipantScanRequest(BaseModel):
    location: int  # 1..8

class ParticipantScanResponse(BaseModel):
    valid: bool
    location: int
    message: str
    question_set: Optional[str] = None
    is_duplicate: Optional[bool] = False

class ParticipantSubmitAnswerRequest(BaseModel):
    answer: str

class ParticipantSubmitAnswerResponse(BaseModel):
    is_correct: bool
    attempt_number: int
    attempts_remaining: int
    is_complete: bool
    is_locked: bool
    message: str
    next_checkpoint: Optional[int] = None
    next_location_clue: Optional[str] = None

class RouteAllocationItem(BaseModel):
    team_identifier: str
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    cp1_location: int
    cp1_set: str
    cp1_completed: bool
    cp1_completed_at: Optional[str] = None
    cp2_location: int
    cp2_set: str
    cp2_completed: bool
    cp2_completed_at: Optional[str] = None
    cp3_location: int
    cp3_set: str
    cp3_completed: bool
    cp3_completed_at: Optional[str] = None
    total_time_seconds: Optional[int] = None
    rank: Optional[int] = None
    is_qualified: bool = False

class RouteAllocationMatrixResponse(BaseModel):
    allocations: List[RouteAllocationItem]
    is_valid: bool
    validation_errors: List[str]
    is_frozen: bool
    summary: Dict[str, Any]

class LocationVolunteerItem(BaseModel):
    checkpoint_number: int
    location_number: int
    location_name: str
    expected_teams: List[Dict[str, Any]]  # team_identifier, team_name, set, status

class EnvelopePreparationItem(BaseModel):
    checkpoint: int
    location: int
    team_identifier: str
    team_name: str
    question_set: str

