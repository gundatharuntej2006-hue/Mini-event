from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict


# =========================================================================
# Base / Round State Schemas
# =========================================================================

class RoundSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: int
    name: str
    codename: str
    description: str
    initial_teams_count: int = Field(..., alias="initialTeamsCount", serialization_alias="initialTeamsCount")
    qualifying_teams_count: int = Field(..., alias="qualifyingTeamsCount", serialization_alias="qualifyingTeamsCount")
    status: str
    started_at: Optional[datetime] = Field(None, alias="startedAt", serialization_alias="startedAt")
    ended_at: Optional[datetime] = Field(None, alias="endedAt", serialization_alias="endedAt")
    location: str
    is_finalized: bool = Field(..., alias="isFinalized", serialization_alias="isFinalized")
    finalized_at: Optional[datetime] = Field(None, alias="finalizedAt", serialization_alias="finalizedAt")
    finalized_by: Optional[str] = Field(None, alias="finalizedBy", serialization_alias="finalizedBy")
    config_json: Dict[str, Any] = Field(default_factory=dict, alias="configJson", serialization_alias="configJson")


class RoundUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    initial_teams_count: Optional[int] = Field(None, alias="initialTeamsCount")
    qualifying_teams_count: Optional[int] = Field(None, alias="qualifyingTeamsCount")
    started_at: Optional[datetime] = Field(None, alias="startedAt")
    ended_at: Optional[datetime] = Field(None, alias="endedAt")
    config_json: Optional[Dict[str, Any]] = Field(None, alias="configJson")


class FinalizeRoundRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    finalized_by: Optional[str] = Field(None, alias="finalizedBy")
    notes: Optional[str] = None
    override_discrepancy: bool = Field(False, alias="overrideDiscrepancy")


class FinalizeRoundResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    round_number: int = Field(..., alias="roundNumber", serialization_alias="roundNumber")
    qualified_team_ids: List[str] = Field(..., alias="qualifiedTeamIds", serialization_alias="qualifiedTeamIds")
    total_eligible: int = Field(..., alias="totalEligible", serialization_alias="totalEligible")
    message: str


# =========================================================================
# Round 1: Expedition / Clue Hunt Schemas
# =========================================================================

class MiniRoundData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    round_number: int = Field(..., alias="roundNumber", serialization_alias="roundNumber")
    start_time: Optional[str] = Field(None, alias="startTime", serialization_alias="startTime")
    completion_time: Optional[str] = Field(None, alias="completionTime", serialization_alias="completionTime")
    duration_seconds: Optional[float] = Field(None, alias="durationSeconds", serialization_alias="durationSeconds")
    hints_used: int = Field(0, alias="hintsUsed", serialization_alias="hintsUsed")
    hint_penalty_seconds: float = Field(0.0, alias="hintPenaltySeconds", serialization_alias="hintPenaltySeconds")
    station_id: Optional[str] = Field(None, alias="stationId", serialization_alias="stationId")
    station_name: Optional[str] = Field(None, alias="stationName", serialization_alias="stationName")
    is_completed: bool = Field(False, alias="isCompleted", serialization_alias="isCompleted")


class Round1RecordResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    team_id: str = Field(..., alias="teamId", serialization_alias="teamId")
    team_name: Optional[str] = Field(None, alias="teamName", serialization_alias="teamName")
    team_identifier: Optional[str] = Field(None, alias="teamIdentifier", serialization_alias="teamIdentifier")
    mini_rounds: List[Dict[str, Any]] = Field(default_factory=list, alias="mini_rounds_json", serialization_alias="miniRounds")
    raw_total_seconds: Optional[float] = Field(None, alias="rawTotalSeconds", serialization_alias="rawTotalSeconds")
    total_penalty_seconds: float = Field(0.0, alias="totalPenaltySeconds", serialization_alias="totalPenaltySeconds")
    adjusted_total_seconds: Optional[float] = Field(None, alias="adjustedTotalSeconds", serialization_alias="adjustedTotalSeconds")
    fastest_mini_round_seconds: Optional[float] = Field(None, alias="fastestMiniRoundSeconds", serialization_alias="fastestMiniRoundSeconds")
    is_complete: bool = Field(False, alias="isComplete", serialization_alias="isComplete")
    rank: Optional[int] = None
    qualification_status: str = Field("Incomplete", alias="qualificationStatus", serialization_alias="qualificationStatus")
    tie_requires_review: bool = Field(False, alias="tieRequiresReview", serialization_alias="tieRequiresReview")
    tie_reason: Optional[str] = Field(None, alias="tieReason", serialization_alias="tieReason")
    hidden_code_recovered: bool = Field(False, alias="hiddenCodeRecovered", serialization_alias="hiddenCodeRecovered")
    hidden_code_recovered_at: Optional[datetime] = Field(None, alias="hiddenCodeRecoveredAt", serialization_alias="hiddenCodeRecoveredAt")
    hidden_code_notes: Optional[str] = Field(None, alias="hiddenCodeNotes", serialization_alias="hiddenCodeNotes")
    last_edited_by: Optional[str] = Field(None, alias="lastEditedBy", serialization_alias="lastEditedBy")
    updated_at: datetime = Field(..., alias="updatedAt", serialization_alias="updatedAt")


class Round1RecordUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mini_rounds: Optional[List[Dict[str, Any]]] = Field(None, alias="miniRounds")
    hidden_code_recovered: Optional[bool] = Field(None, alias="hiddenCodeRecovered")
    hidden_code_notes: Optional[str] = Field(None, alias="hiddenCodeNotes")
    last_edited_by: Optional[str] = Field(None, alias="lastEditedBy")


class Round1BatchUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    records: List[Dict[str, Any]]


# =========================================================================
# Round 2: Cabo Schemas
# =========================================================================

class Round2PlacementCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    game_number: int = Field(..., ge=1, le=3, alias="gameNumber")
    team_id: str = Field(..., alias="teamId")
    placement: int = Field(..., ge=1, le=24)
    points: Optional[float] = None
    notes: Optional[str] = None


class Round2PlacementResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    game_number: int = Field(..., alias="gameNumber", serialization_alias="gameNumber")
    team_id: str = Field(..., alias="teamId", serialization_alias="teamId")
    team_name: Optional[str] = Field(None, alias="teamName", serialization_alias="teamName")
    team_identifier: Optional[str] = Field(None, alias="teamIdentifier", serialization_alias="teamIdentifier")
    placement: int
    points: float
    notes: Optional[str] = None
    recorded_by: Optional[str] = Field(None, alias="recordedBy", serialization_alias="recordedBy")
    recorded_at: datetime = Field(..., alias="recordedAt", serialization_alias="recordedAt")


class Round2GameSubmitRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    game_number: int = Field(..., ge=1, le=3, alias="gameNumber")
    placements: List[Dict[str, Any]]  # [{ "teamId": "...", "placement": 1, "points": 100, "notes": "" }]


class Round2TeamSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    team_id: str = Field(..., alias="teamId", serialization_alias="teamId")
    team_name: str = Field(..., alias="teamName", serialization_alias="teamName")
    team_identifier: str = Field(..., alias="teamIdentifier", serialization_alias="teamIdentifier")
    game1_points: Optional[float] = Field(None, alias="game1Points", serialization_alias="game1Points")
    game2_points: Optional[float] = Field(None, alias="game2Points", serialization_alias="game2Points")
    game3_points: Optional[float] = Field(None, alias="game3Points", serialization_alias="game3Points")
    total_points: float = Field(0.0, alias="totalPoints", serialization_alias="totalPoints")
    games_played: int = Field(0, alias="gamesPlayed", serialization_alias="gamesPlayed")
    rank: Optional[int] = None
    qualification_status: str = Field("Pending", alias="qualificationStatus", serialization_alias="qualificationStatus")


# =========================================================================
# Round 3: The Black Market Schemas
# =========================================================================

class Round3TransactionCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    team_id: str = Field(..., alias="teamId")
    amount: float
    type: str  # earn, spend, adjustment, reversal
    reason: str
    organizer_ref: Optional[str] = Field(None, alias="organizerRef")
    notes: Optional[str] = None


class Round3TransferRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_team_id: str = Field(..., alias="fromTeamId")
    to_team_id: str = Field(..., alias="toTeamId")
    amount: float = Field(..., gt=0)
    reason: str = "Market Deal / Asset Transfer"
    notes: Optional[str] = None


class Round3TransactionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    team_id: str = Field(..., alias="teamId", serialization_alias="teamId")
    team_name: Optional[str] = Field(None, alias="teamName", serialization_alias="teamName")
    team_identifier: Optional[str] = Field(None, alias="teamIdentifier", serialization_alias="teamIdentifier")
    amount: float
    type: str
    reason: str
    organizer_ref: Optional[str] = Field(None, alias="organizerRef", serialization_alias="organizerRef")
    timestamp: datetime
    is_reversed: bool = Field(False, alias="isReversed", serialization_alias="isReversed")
    reversal_transaction_id: Optional[str] = Field(None, alias="reversalTransactionId", serialization_alias="reversalTransactionId")
    reversed_transaction_id: Optional[str] = Field(None, alias="reversedTransactionId", serialization_alias="reversedTransactionId")
    notes: Optional[str] = None


class Round3CodeRecordResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    team_id: str = Field(..., alias="teamId", serialization_alias="teamId")
    team_name: Optional[str] = Field(None, alias="teamName", serialization_alias="teamName")
    fragments: List[Dict[str, Any]] = Field(default_factory=list, alias="fragments_json", serialization_alias="fragments")
    is_complete: bool = Field(False, alias="isComplete", serialization_alias="isComplete")
    verified_at: Optional[datetime] = Field(None, alias="verifiedAt", serialization_alias="verifiedAt")
    verified_by: Optional[str] = Field(None, alias="verifiedBy", serialization_alias="verifiedBy")
    updated_at: datetime = Field(..., alias="updatedAt", serialization_alias="updatedAt")


class Round3CodeFragmentUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    team_id: str = Field(..., alias="teamId")
    fragment_index: int = Field(..., alias="fragmentIndex")
    code: Optional[str] = None
    is_discovered: bool = Field(True, alias="isDiscovered")
    clue_station: Optional[str] = Field(None, alias="clueStation")


class Round3TeamSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    team_id: str = Field(..., alias="teamId", serialization_alias="teamId")
    team_name: str = Field(..., alias="teamName", serialization_alias="teamName")
    team_identifier: str = Field(..., alias="teamIdentifier", serialization_alias="teamIdentifier")
    starting_balance: float = Field(100.0, alias="startingBalance", serialization_alias="startingBalance")
    total_earned: float = Field(0.0, alias="totalEarned", serialization_alias="totalEarned")
    total_spent: float = Field(0.0, alias="totalSpent", serialization_alias="totalSpent")
    net_adjustments: float = Field(0.0, alias="netAdjustments", serialization_alias="netAdjustments")
    current_balance: float = Field(100.0, alias="currentBalance", serialization_alias="currentBalance")
    fragments_discovered: int = Field(0, alias="fragmentsDiscovered", serialization_alias="fragmentsDiscovered")
    total_fragments: int = Field(4, alias="totalFragments", serialization_alias="totalFragments")
    is_code_complete: bool = Field(False, alias="isCodeComplete", serialization_alias="isCodeComplete")
    rank: Optional[int] = None
    qualification_status: str = Field("Pending", alias="qualificationStatus", serialization_alias="qualificationStatus")


# =========================================================================
# Round 4: The Legal Battle Schemas
# =========================================================================

class Round4PairCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pair_number: int = Field(..., ge=1, le=4, alias="pairNumber")
    team_a_id: Optional[str] = Field(None, alias="teamAId")
    team_b_id: Optional[str] = Field(None, alias="teamBId")
    case_id: Optional[str] = Field(None, alias="caseId")
    case_name: Optional[str] = Field(None, alias="caseName")
    case_details: Optional[str] = Field(None, alias="caseDetails")
    team_a_side: str = Field("Prosecution / Plaintiff", alias="teamASide")
    team_b_side: str = Field("Defense / Respondent", alias="teamBSide")


class Round4PairUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    is_confirmed: Optional[bool] = Field(None, alias="isConfirmed")
    confirmed_by: Optional[str] = Field(None, alias="confirmedBy")
    case_id: Optional[str] = Field(None, alias="caseId")
    case_name: Optional[str] = Field(None, alias="caseName")
    case_details: Optional[str] = Field(None, alias="caseDetails")
    team_a_side: Optional[str] = Field(None, alias="teamASide")
    team_b_side: Optional[str] = Field(None, alias="teamBSide")
    team_a_has_case_file: Optional[bool] = Field(None, alias="teamAHasCaseFile")
    team_a_has_opposing_file: Optional[bool] = Field(None, alias="teamAHasOpposingFile")
    team_b_has_case_file: Optional[bool] = Field(None, alias="teamBHasCaseFile")
    team_b_has_opposing_file: Optional[bool] = Field(None, alias="teamBHasOpposingFile")
    stages_json: Optional[Dict[str, Any]] = Field(None, alias="stages")
    resource_person_name: Optional[str] = Field(None, alias="resourcePersonName")
    resource_person_notes: Optional[str] = Field(None, alias="resourcePersonNotes")
    resource_person_questions_json: Optional[List[Dict[str, Any]]] = Field(None, alias="resourcePersonQuestions")
    is_questioning_complete: Optional[bool] = Field(None, alias="isQuestioningComplete")


class Round4PairResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    pair_number: int = Field(..., alias="pairNumber", serialization_alias="pairNumber")
    team_a_id: Optional[str] = Field(None, alias="teamAId", serialization_alias="teamAId")
    team_a_name: Optional[str] = Field(None, alias="teamAName", serialization_alias="teamAName")
    team_b_id: Optional[str] = Field(None, alias="teamBId", serialization_alias="teamBId")
    team_b_name: Optional[str] = Field(None, alias="teamBName", serialization_alias="teamBName")
    is_confirmed: bool = Field(False, alias="isConfirmed", serialization_alias="isConfirmed")
    confirmed_at: Optional[datetime] = Field(None, alias="confirmedAt", serialization_alias="confirmedAt")
    confirmed_by: Optional[str] = Field(None, alias="confirmedBy", serialization_alias="confirmedBy")
    case_id: Optional[str] = Field(None, alias="caseId", serialization_alias="caseId")
    case_name: Optional[str] = Field(None, alias="caseName", serialization_alias="caseName")
    case_details: Optional[str] = Field(None, alias="caseDetails", serialization_alias="caseDetails")
    team_a_side: str = Field("Prosecution / Plaintiff", alias="teamASide", serialization_alias="teamASide")
    team_b_side: str = Field("Defense / Respondent", alias="teamBSide", serialization_alias="teamBSide")
    team_a_has_case_file: bool = Field(False, alias="teamAHasCaseFile", serialization_alias="teamAHasCaseFile")
    team_a_case_file_at: Optional[datetime] = Field(None, alias="teamACaseFileAt", serialization_alias="teamACaseFileAt")
    team_a_has_opposing_file: bool = Field(False, alias="teamAHasOpposingFile", serialization_alias="teamAHasOpposingFile")
    team_a_opposing_file_at: Optional[datetime] = Field(None, alias="teamAOpposingFileAt", serialization_alias="teamAOpposingFileAt")
    team_b_has_case_file: bool = Field(False, alias="teamBHasCaseFile", serialization_alias="teamBHasCaseFile")
    team_b_case_file_at: Optional[datetime] = Field(None, alias="teamBCaseFileAt", serialization_alias="teamBCaseFileAt")
    team_b_has_opposing_file: bool = Field(False, alias="teamBHasOpposingFile", serialization_alias="teamBHasOpposingFile")
    team_b_opposing_file_at: Optional[datetime] = Field(None, alias="teamBOpposingFileAt", serialization_alias="teamBOpposingFileAt")
    stages: Dict[str, Any] = Field(default_factory=dict, alias="stages_json", serialization_alias="stages")
    resource_person_name: Optional[str] = Field(None, alias="resourcePersonName", serialization_alias="resourcePersonName")
    resource_person_notes: Optional[str] = Field(None, alias="resourcePersonNotes", serialization_alias="resourcePersonNotes")
    resource_person_questions: List[Dict[str, Any]] = Field(default_factory=list, alias="resource_person_questions_json", serialization_alias="resourcePersonQuestions")
    is_questioning_complete: bool = Field(False, alias="isQuestioningComplete", serialization_alias="isQuestioningComplete")
    updated_at: datetime = Field(..., alias="updatedAt", serialization_alias="updatedAt")


class Round4JudgeScoreSubmit(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    judge_id: str = Field(..., alias="judgeId")
    judge_name: str = Field(..., alias="judgeName")
    team_id: str = Field(..., alias="teamId")
    scores: Dict[str, float] = Field(..., alias="scores")
    comments: Optional[str] = None


class Round4JudgeScoreResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    judge_id: str = Field(..., alias="judgeId", serialization_alias="judgeId")
    judge_name: str = Field(..., alias="judgeName", serialization_alias="judgeName")
    team_id: str = Field(..., alias="teamId", serialization_alias="teamId")
    scores: Dict[str, float] = Field(..., alias="scores_json", serialization_alias="scores")
    total_score: float = Field(..., alias="totalScore", serialization_alias="totalScore")
    comments: Optional[str] = None
    submitted_at: datetime = Field(..., alias="submittedAt", serialization_alias="submittedAt")
    is_submitted: bool = Field(True, alias="isSubmitted", serialization_alias="isSubmitted")


class Round4AgentGuessSubmit(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    team_id: str = Field(..., alias="teamId")
    outcome: str = "none"  # correct, incorrect, pending, none
    points_awarded: Optional[float] = Field(None, alias="pointsAwarded")
    notes: Optional[str] = None


class Round4AgentGuessResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    team_id: str = Field(..., alias="teamId", serialization_alias="teamId")
    outcome: str
    points_awarded: Optional[float] = Field(None, alias="pointsAwarded", serialization_alias="pointsAwarded")
    is_verified: bool = Field(False, alias="isVerified", serialization_alias="isVerified")
    verified_by: Optional[str] = Field(None, alias="verifiedBy", serialization_alias="verifiedBy")
    verified_at: Optional[datetime] = Field(None, alias="verifiedAt", serialization_alias="verifiedAt")
    notes: Optional[str] = None


class Round4TeamSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    team_id: str = Field(..., alias="teamId", serialization_alias="teamId")
    team_name: str = Field(..., alias="teamName", serialization_alias="teamName")
    team_identifier: str = Field(..., alias="teamIdentifier", serialization_alias="teamIdentifier")
    pair_number: Optional[int] = Field(None, alias="pairNumber", serialization_alias="pairNumber")
    opponent_team_id: Optional[str] = Field(None, alias="opponentTeamId", serialization_alias="opponentTeamId")
    opponent_team_name: Optional[str] = Field(None, alias="opponentTeamName", serialization_alias="opponentTeamName")
    side: Optional[str] = None
    jury_score: float = Field(0.0, alias="juryScore", serialization_alias="juryScore")
    agent_guess_points: float = Field(0.0, alias="agentGuessPoints", serialization_alias="agentGuessPoints")
    total_score: float = Field(0.0, alias="totalScore", serialization_alias="totalScore")
    rank: Optional[int] = None
    qualification_status: str = Field("Pending", alias="qualificationStatus", serialization_alias="qualificationStatus")


# =========================================================================
# Grand Finale (Round 5) Schemas
# =========================================================================

class FinaleScorecardSubmit(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    team_id: str = Field(..., alias="teamId")
    judge_name: str = Field("Grand Jury Panel", alias="judgeName")
    scores: Dict[str, float] = Field(..., alias="scores")
    comments: Optional[str] = None


class FinaleScorecardResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    team_id: str = Field(..., alias="teamId", serialization_alias="teamId")
    judge_name: str = Field(..., alias="judgeName", serialization_alias="judgeName")
    scores: Dict[str, float] = Field(..., alias="scores_json", serialization_alias="scores")
    total_score: Optional[float] = Field(None, alias="totalScore", serialization_alias="totalScore")
    is_complete: bool = Field(False, alias="isComplete", serialization_alias="isComplete")
    submitted_at: Optional[datetime] = Field(None, alias="submittedAt", serialization_alias="submittedAt")
    comments: Optional[str] = None
    last_edited_by: Optional[str] = Field(None, alias="lastEditedBy", serialization_alias="lastEditedBy")
    last_edited_at: Optional[datetime] = Field(None, alias="lastEditedAt", serialization_alias="lastEditedAt")


class FinaleAgentVerdictSubmit(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    team_id: str = Field(..., alias="teamId")
    suspected_agent: Optional[str] = Field(None, alias="suspectedAgent")
    actual_agent: Optional[str] = Field(None, alias="actualAgent")
    is_correct: Optional[bool] = Field(None, alias="isCorrect")
    bonus_points: Optional[float] = Field(None, alias="bonusPoints")
    penalty_points: Optional[float] = Field(None, alias="penaltyPoints")
    notes: Optional[str] = None


class FinaleAgentVerdictResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    team_id: str = Field(..., alias="teamId", serialization_alias="teamId")
    suspected_agent: Optional[str] = Field(None, alias="suspectedAgent", serialization_alias="suspectedAgent")
    actual_agent: Optional[str] = Field(None, alias="actualAgent", serialization_alias="actualAgent")
    is_correct: Optional[bool] = Field(None, alias="isCorrect", serialization_alias="isCorrect")
    bonus_points: Optional[float] = Field(None, alias="bonusPoints", serialization_alias="bonusPoints")
    penalty_points: Optional[float] = Field(None, alias="penaltyPoints", serialization_alias="penaltyPoints")
    is_verified: bool = Field(False, alias="isVerified", serialization_alias="isVerified")
    verified_by: Optional[str] = Field(None, alias="verifiedBy", serialization_alias="verifiedBy")
    verified_at: Optional[datetime] = Field(None, alias="verifiedAt", serialization_alias="verifiedAt")
    notes: Optional[str] = None


class FinaleTeamSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    team_id: str = Field(..., alias="teamId", serialization_alias="teamId")
    team_name: str = Field(..., alias="teamName", serialization_alias="teamName")
    team_identifier: str = Field(..., alias="teamIdentifier", serialization_alias="teamIdentifier")
    carryover_score: float = Field(0.0, alias="carryoverScore", serialization_alias="carryoverScore")
    jury_score: float = Field(0.0, alias="juryScore", serialization_alias="juryScore")
    agent_verdict_score: float = Field(0.0, alias="agentVerdictScore", serialization_alias="agentVerdictScore")
    grand_total_score: float = Field(0.0, alias="grandTotalScore", serialization_alias="grandTotalScore")
    rank: Optional[int] = None
    podium_title: Optional[str] = Field(None, alias="podiumTitle", serialization_alias="podiumTitle")
