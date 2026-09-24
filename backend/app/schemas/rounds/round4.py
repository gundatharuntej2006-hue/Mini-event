from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.core.constants import R4_FINALISTS, R4_ADVANCING_COUNT


class CreatePairInput(BaseModel):
    pair_number: int = Field(..., ge=1, le=4, alias="pairNumber")
    team_a_id: str = Field(..., alias="teamAId")
    team_b_id: str = Field(..., alias="teamBId")
    case_name: Optional[str] = Field(None, alias="caseName")
    team_a_side: Optional[str] = Field("Prosecution / Plaintiff", alias="teamASide")
    team_b_side: Optional[str] = Field("Defense / Respondent", alias="teamBSide")

    model_config = {"populate_by_name": True}


class AutoAssignPairsInput(BaseModel):
    seed: Optional[int] = None
    confirm: bool = True

    model_config = {"populate_by_name": True}


class UpdatePairCaseInput(BaseModel):
    case_id: Optional[str] = Field(None, alias="caseId")
    case_name: Optional[str] = Field(None, alias="caseName")
    case_details: Optional[str] = Field(None, alias="caseDetails")
    team_a_side: Optional[str] = Field(None, alias="teamASide")
    team_b_side: Optional[str] = Field(None, alias="teamBSide")
    team_a_has_case_file: Optional[bool] = Field(None, alias="teamAHasCaseFile")
    team_a_has_opposing_file: Optional[bool] = Field(None, alias="teamAHasOpposingFile")
    team_b_has_case_file: Optional[bool] = Field(None, alias="teamBHasCaseFile")
    team_b_has_opposing_file: Optional[bool] = Field(None, alias="teamBHasOpposingFile")
    resource_person_name: Optional[str] = Field(None, alias="resourcePersonName")
    resource_person_notes: Optional[str] = Field(None, alias="resourcePersonNotes")
    resource_person_questions: Optional[List[Dict[str, Any]]] = Field(None, alias="resourcePersonQuestions")
    is_confirmed: Optional[bool] = Field(None, alias="isConfirmed")

    model_config = {"populate_by_name": True}


class ResourcePersonQuestionInput(BaseModel):
    team_id: str = Field(..., alias="teamId")
    question: str
    answer: Optional[str] = None
    score: Optional[float] = None
    notes: Optional[str] = None

    model_config = {"populate_by_name": True}


class UpdateStageInput(BaseModel):
    status: str = Field(..., pattern="^(not_started|in_progress|completed|paused)$")
    actual_duration_seconds: Optional[int] = Field(None, alias="actualDurationSeconds")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True}


class SubmitJudgeScoreInput(BaseModel):
    judge_id: str = Field(..., alias="judgeId")
    judge_name: str = Field(..., alias="judgeName")
    team_id: Optional[str] = Field(None, alias="teamId")
    scores: Dict[str, float]  # category_id -> score
    comments: Optional[str] = None

    model_config = {"populate_by_name": True}


class SubmitAgentGuessInput(BaseModel):
    team_id: Optional[str] = Field(None, alias="teamId")
    outcome: str = Field(..., pattern="^(correct|incorrect|pending|none)$")
    points_awarded: Optional[float] = Field(None, alias="pointsAwarded")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True}


class FinalizeRound4Input(BaseModel):
    override_discrepancy: bool = Field(False, alias="overrideDiscrepancy")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True}


class Round4ConfigSchema(BaseModel):
    rubric_categories: List[Dict[str, Any]] = Field(default_factory=list, alias="rubricCategories")
    is_rubric_confirmed: bool = Field(False, alias="isRubricConfirmed")
    judge_aggregation: str = Field("average", alias="judgeAggregation")
    judges_list: List[Dict[str, Any]] = Field(default_factory=list, alias="judgesList")
    final_score_formula: Dict[str, Any] = Field(default_factory=dict, alias="finalScoreFormula")
    advancing_teams_count: int = Field(R4_ADVANCING_COUNT, alias="advancingTeamsCount")
    is_finalized: bool = Field(False, alias="isFinalized")
    finalized_at: Optional[str] = Field(None, alias="finalizedAt")
    finalized_by: Optional[str] = Field(None, alias="finalizedBy")

    model_config = {"populate_by_name": True}


class UpdateRound4ConfigInput(BaseModel):
    is_rubric_confirmed: Optional[bool] = Field(None, alias="isRubricConfirmed")
    rubric_categories: Optional[List[Dict[str, Any]]] = Field(None, alias="rubricCategories")
    judge_aggregation: Optional[str] = Field(None, alias="judgeAggregation")
    final_score_formula: Optional[Dict[str, Any]] = Field(None, alias="finalScoreFormula")
    advancing_teams_count: Optional[int] = Field(None, alias="advancingTeamsCount")

    model_config = {"populate_by_name": True}


class StageTimingResponse(BaseModel):
    stage_id: str = Field(..., alias="stageId")
    status: str
    started_at: Optional[str] = Field(None, alias="startedAt")
    ended_at: Optional[str] = Field(None, alias="endedAt")
    actual_duration_seconds: Optional[int] = Field(None, alias="actualDurationSeconds")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True}


class Round4PairResponse(BaseModel):
    id: str
    pair_number: int = Field(..., alias="pairNumber")
    team_a_id: Optional[str] = Field(None, alias="teamAId")
    team_b_id: Optional[str] = Field(None, alias="teamBId")
    team_a_name: Optional[str] = Field(None, alias="teamAName")
    team_b_name: Optional[str] = Field(None, alias="teamBName")
    is_confirmed: bool = Field(False, alias="isConfirmed")
    confirmed_at: Optional[str] = Field(None, alias="confirmedAt")
    confirmed_by: Optional[str] = Field(None, alias="confirmedBy")
    case_id: Optional[str] = Field(None, alias="caseId")
    case_name: Optional[str] = Field(None, alias="caseName")
    case_details: Optional[str] = Field(None, alias="caseDetails")
    team_a_side: str = Field("Prosecution / Plaintiff", alias="teamASide")
    team_b_side: str = Field("Defense / Respondent", alias="teamBSide")
    team_a_has_case_file: bool = Field(False, alias="teamAHasCaseFile")
    team_a_has_opposing_file: bool = Field(False, alias="teamAHasOpposingFile")
    team_b_has_case_file: bool = Field(False, alias="teamBHasCaseFile")
    team_b_has_opposing_file: bool = Field(False, alias="teamBHasOpposingFile")
    resource_person_name: Optional[str] = Field(None, alias="resourcePersonName")
    resource_person_notes: Optional[str] = Field(None, alias="resourcePersonNotes")
    resource_person_questions: List[Dict[str, Any]] = Field(default_factory=list, alias="resourcePersonQuestions")
    is_questioning_complete: bool = Field(False, alias="isQuestioningComplete")
    stages: Dict[str, StageTimingResponse] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class FinalScoreBreakdownResponse(BaseModel):
    team_id: str = Field(..., alias="teamId")
    raw_panel_score: Optional[float] = Field(None, alias="rawPanelScore")
    weighted_panel_score: Optional[float] = Field(None, alias="weightedPanelScore")
    agent_guessing_points: Optional[float] = Field(None, alias="agentGuessingPoints")
    black_market_balance: float = Field(0.0, alias="blackMarketBalance")
    black_market_contribution: float = Field(0.0, alias="blackMarketContribution")
    final_score: Optional[float] = Field(None, alias="finalScore")
    is_complete: bool = Field(False, alias="isComplete")
    missing_components: List[str] = Field(default_factory=list, alias="missingComponents")

    model_config = {"populate_by_name": True}


class TeamRound4RecordResponse(BaseModel):
    team_id: str = Field(..., alias="teamId")
    team_number: int = Field(..., alias="teamNumber")
    team_name: str = Field(..., alias="teamName")
    round3_qualified: bool = Field(True, alias="round3Qualified")
    pairing_id: Optional[str] = Field(None, alias="pairingId")
    side: str = "Unassigned"
    case_name: Optional[str] = Field(None, alias="caseName")
    panel_score: Optional[float] = Field(None, alias="panelScore")
    is_judge_panel_complete: bool = Field(False, alias="isJudgePanelComplete")
    final_score_breakdown: FinalScoreBreakdownResponse = Field(..., alias="finalScoreBreakdown")
    rank: Optional[int] = None
    is_advancing: bool = Field(True, alias="isAdvancing")
    tie_requires_review: bool = Field(False, alias="tieRequiresReview")
    tie_reason: Optional[str] = Field(None, alias="tieReason")
    review_status: str = Field("Ready for Review", alias="reviewStatus")

    model_config = {"populate_by_name": True}


class Round4OverviewResponse(BaseModel):
    id: int = 4
    name: str = "Round 4 — The Legal Battle"
    codename: str = "ROUND_4_LEGAL_BATTLE"
    status: str = "In Progress"
    is_finalized: bool = Field(False, alias="isFinalized")
    qualifying_teams_count: int = Field(R4_ADVANCING_COUNT, alias="qualifyingTeamsCount")
    config_json: Dict[str, Any] = Field(default_factory=dict, alias="configJson")
    config: Round4ConfigSchema
    pairs: List[Round4PairResponse]
    records: List[TeamRound4RecordResponse]
    can_finalize: bool = Field(False, alias="canFinalize")
    issues: List[Any] = Field(default_factory=list)
    checklist: List[Any] = Field(default_factory=list)
    ties_affecting_cutoff: bool = Field(False, alias="tiesAffectingCutoff")

    model_config = {"populate_by_name": True}
