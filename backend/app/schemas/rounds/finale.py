from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SubmitScorecardInput(BaseModel):
    judge_name: str
    scores: Dict[str, Optional[float]]  # criterion_id -> score
    comments: Optional[str] = None

class SubmitAgentVerdictInput(BaseModel):
    suspected_agent: Optional[str] = None
    actual_agent: Optional[str] = None
    is_correct: Optional[bool] = None
    bonus_points: Optional[float] = None
    penalty_points: Optional[float] = None
    notes: Optional[str] = None

class FinaleConfigSchema(BaseModel):
    is_scoring_rules_confirmed: bool = False
    confirmed_at: Optional[str] = None
    confirmed_by: Optional[str] = None
    criteria: List[Dict[str, Any]] = []
    round4_score_carried_over: bool = True
    round4_score_weight: float = 0.2
    finale_activity_weight: float = 1.0
    agent_bonus_points_for_correct: Optional[float] = None
    agent_penalty_points_for_incorrect: Optional[float] = None
    scoring_direction: str = "higher_wins"
    is_finalized: bool = False
    finalized_at: Optional[str] = None
    finalized_by: Optional[str] = None

class UpdateFinaleConfigInput(BaseModel):
    is_scoring_rules_confirmed: Optional[bool] = None
    criteria: Optional[List[Dict[str, Any]]] = None
    round4_score_carried_over: Optional[bool] = None
    round4_score_weight: Optional[float] = None
    finale_activity_weight: Optional[float] = None
    agent_bonus_points_for_correct: Optional[float] = None
    agent_penalty_points_for_incorrect: Optional[float] = None
    scoring_direction: Optional[str] = None

class FinaleScorecardResponse(BaseModel):
    team_id: str
    judge_name: str
    scores: Dict[str, Optional[float]] = {}
    total_score: Optional[float] = None
    is_complete: bool = False
    submitted_at: Optional[str] = None
    comments: Optional[str] = None

class FinaleScoreBreakdownResponse(BaseModel):
    team_id: str
    round4_carried_score: Optional[float] = None
    round4_weight: float = 0.2
    round4_contribution: float = 0.0
    finale_activity_score: Optional[float] = None
    finale_activity_weight: float = 1.0
    finale_activity_contribution: Optional[float] = None
    agent_adjustment: float = 0.0
    total_finale_score: Optional[float] = None
    is_complete: bool = False
    missing_components: List[str] = []

class TeamFinaleRecordResponse(BaseModel):
    team_id: str
    team_number: int
    team_name: str
    round4_score: Optional[float] = None
    scorecard: FinaleScorecardResponse
    score_breakdown: FinaleScoreBreakdownResponse
    placement: Optional[int] = None
    placement_title: Optional[str] = None
    tie_requires_review: bool = False
    tie_reason: Optional[str] = None
    review_status: str

class FinaleOverviewResponse(BaseModel):
    config: FinaleConfigSchema
    records: List[TeamFinaleRecordResponse]
    can_finalize: bool
    issues: List[Any] = []
    checklist: List[Any] = []
    ties_affecting_placement: bool = False
    champion_team_id: Optional[str] = None
    runner_up1_team_id: Optional[str] = None
    runner_up2_team_id: Optional[str] = None
