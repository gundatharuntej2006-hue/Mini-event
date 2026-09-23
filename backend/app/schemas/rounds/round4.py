from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class CreatePairInput(BaseModel):
    pair_number: int = Field(..., ge=1, le=4)
    team_a_id: str
    team_b_id: str
    case_name: Optional[str] = None
    team_a_side: Optional[str] = "Prosecution / Plaintiff"
    team_b_side: Optional[str] = "Defense / Respondent"

class UpdatePairCaseInput(BaseModel):
    case_id: Optional[str] = None
    case_name: Optional[str] = None
    case_details: Optional[str] = None
    team_a_side: Optional[str] = None
    team_b_side: Optional[str] = None
    team_a_has_case_file: Optional[bool] = None
    team_a_has_opposing_file: Optional[bool] = None
    team_b_has_case_file: Optional[bool] = None
    team_b_has_opposing_file: Optional[bool] = None
    resource_person_name: Optional[str] = None

class UpdateStageInput(BaseModel):
    status: str = Field(..., pattern="^(not_started|in_progress|completed|paused)$")
    actual_duration_seconds: Optional[int] = None
    notes: Optional[str] = None

class SubmitJudgeScoreInput(BaseModel):
    judge_id: str
    judge_name: str
    scores: Dict[str, float]  # category_id -> score
    comments: Optional[str] = None

class SubmitAgentGuessInput(BaseModel):
    outcome: str = Field(..., pattern="^(correct|incorrect|pending|none)$")
    points_awarded: Optional[float] = None
    notes: Optional[str] = None

class Round4ConfigSchema(BaseModel):
    rubric_categories: List[Dict[str, Any]] = []
    is_rubric_confirmed: bool = False
    judge_aggregation: str = "average"
    judges_list: List[Dict[str, Any]] = []
    final_score_formula: Dict[str, Any] = {}
    advancing_teams_count: int = 3
    is_finalized: bool = False
    finalized_at: Optional[str] = None
    finalized_by: Optional[str] = None

class UpdateRound4ConfigInput(BaseModel):
    is_rubric_confirmed: Optional[bool] = None
    rubric_categories: Optional[List[Dict[str, Any]]] = None
    judge_aggregation: Optional[str] = None
    final_score_formula: Optional[Dict[str, Any]] = None
    advancing_teams_count: Optional[int] = None

class StageTimingResponse(BaseModel):
    stage_id: str
    status: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    actual_duration_seconds: Optional[int] = None
    notes: Optional[str] = None

class Round4PairResponse(BaseModel):
    id: str
    pair_number: int
    team_a_id: Optional[str] = None
    team_b_id: Optional[str] = None
    team_a_name: Optional[str] = None
    team_b_name: Optional[str] = None
    is_confirmed: bool = False
    confirmed_at: Optional[str] = None
    case_name: Optional[str] = None
    case_details: Optional[str] = None
    team_a_side: str
    team_b_side: str
    team_a_has_case_file: bool = False
    team_a_has_opposing_file: bool = False
    team_b_has_case_file: bool = False
    team_b_has_opposing_file: bool = False
    stages: Dict[str, StageTimingResponse] = {}

class FinalScoreBreakdownResponse(BaseModel):
    team_id: str
    raw_panel_score: Optional[float] = None
    weighted_panel_score: Optional[float] = None
    agent_guessing_points: Optional[float] = None
    black_market_balance: float = 0.0
    black_market_contribution: float = 0.0
    final_score: Optional[float] = None
    is_complete: bool = False
    missing_components: List[str] = []

class TeamRound4RecordResponse(BaseModel):
    team_id: str
    team_number: int
    team_name: str
    round3_qualified: bool
    pairing_id: Optional[str] = None
    side: str = "Unassigned"
    case_name: Optional[str] = None
    panel_score: Optional[float] = None
    is_judge_panel_complete: bool = False
    final_score_breakdown: FinalScoreBreakdownResponse
    rank: Optional[int] = None
    tie_requires_review: bool = False
    tie_reason: Optional[str] = None
    review_status: str

class Round4OverviewResponse(BaseModel):
    id: int = 4
    name: str = "Round 4 — The Legal Battle"
    codename: str = "ROUND_4_LEGAL_BATTLE"
    status: str = "In Progress"
    is_finalized: bool = Field(False, alias="isFinalized")
    qualifying_teams_count: int = Field(3, alias="qualifyingTeamsCount")
    config_json: Dict[str, Any] = Field(default_factory=dict, alias="configJson")
    config: Round4ConfigSchema
    pairs: List[Round4PairResponse]
    records: List[TeamRound4RecordResponse]
    can_finalize: bool
    issues: List[Any] = []
    checklist: List[Any] = []
    ties_affecting_cutoff: bool = False

    model_config = {
        "populate_by_name": True,
    }
