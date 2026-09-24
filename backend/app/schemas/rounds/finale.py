from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from app.core.constants import (
    AGENT_CORRECT_GUESS,
    AGENT_WRONG_GUESS,
    AGENT_GUESS_MIN,
    AGENT_GUESS_MAX,
    DEFAULT_CARRYOVER_WEIGHT_PERCENT,
    R4_ADVANCING_COUNT,
)


# ==============================================================================
# 1. SECRET AGENT GUESSING INPUT & OUTPUT SCHEMAS (STEP 14)
# ==============================================================================

class AgentGuessItemInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    target_team_id: str = Field(..., alias="targetTeamId", description="Target team whose secret agent is being guessed")
    suspected_participant_id: Optional[str] = Field(None, alias="suspectedParticipantId", description="Suspected participant UUID")
    suspected_agent_name: Optional[str] = Field(None, alias="suspectedAgentName", description="Suspected participant name or codename")
    notes: Optional[str] = Field(None, description="Optional investigative notes")


class SubmitTeamGuessesInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    guessing_team_id: Optional[str] = Field(None, alias="guessingTeamId", description="ID of the guessing squad (auto-resolved from JWT for teams)")
    guesses: List[AgentGuessItemInput] = Field(..., description="Array of 1 to 5 secret agent guesses")
    notes: Optional[str] = Field(None, description="Optional notes on submission")


class AgentGuessItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    guessing_team_id: str = Field(..., alias="guessingTeamId")
    target_team_id: str = Field(..., alias="targetTeamId")
    target_team_name: Optional[str] = Field(None, alias="targetTeamName")
    suspected_participant_id: Optional[str] = Field(None, alias="suspectedParticipantId")
    suspected_agent_name: Optional[str] = Field(None, alias="suspectedAgentName")
    is_resolved: bool = Field(False, alias="isResolved")
    is_correct: Optional[bool] = Field(None, alias="isCorrect")
    points_awarded: Optional[float] = Field(None, alias="pointsAwarded")
    notes: Optional[str] = None
    created_at: Optional[str] = Field(None, alias="createdAt")


class TeamGuessSubmissionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    guessing_team_id: str = Field(..., alias="guessingTeamId")
    guessing_team_name: Optional[str] = Field(None, alias="guessingTeamName")
    total_guesses: int = Field(0, alias="totalGuesses")
    correct_guesses: Optional[int] = Field(None, alias="correctGuesses")
    wrong_guesses: Optional[int] = Field(None, alias="wrongGuesses")
    total_guessing_points: Optional[float] = Field(None, alias="totalGuessingPoints")
    is_submitted: bool = Field(True, alias="isSubmitted")
    submitted_at: Optional[str] = Field(None, alias="submittedAt")
    submitted_by: Optional[str] = Field(None, alias="submittedBy")
    guesses: List[AgentGuessItemResponse] = Field(default_factory=list)


# ==============================================================================
# 2. BEST SECRET AGENT SCHEMAS (STEP 14)
# ==============================================================================

class BestSecretAgentItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    dossier_id: str = Field(..., alias="dossierId")
    team_id: str = Field(..., alias="teamId")
    team_number: int = Field(..., alias="teamNumber")
    team_name: Optional[str] = Field(None, alias="teamName")
    participant_id: str = Field(..., alias="participantId")
    participant_name: Optional[str] = Field(None, alias="participantName")
    codename: Optional[str] = None
    status: str = "ACTIVE"
    verified_tasks_count: int = Field(0, alias="verifiedTasksCount")
    correct_guesses_received: int = Field(0, alias="correctGuessesReceived")
    total_guesses_received: int = Field(0, alias="totalGuessesReceived")
    is_uncompromised: bool = Field(False, alias="isUncompromised")
    rank: int = 1
    tie_requires_review: bool = Field(False, alias="tieRequiresReview")
    tie_reason: Optional[str] = Field(None, alias="tieReason")


class BestSecretAgentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    best_agent: Optional[BestSecretAgentItemResponse] = Field(None, alias="bestAgent")
    rankings: List[BestSecretAgentItemResponse] = Field(default_factory=list)
    tie_requires_review: bool = Field(False, alias="tieRequiresReview")
    tied_candidate_ids: List[str] = Field(default_factory=list, alias="tiedCandidateIds")
    notes: Optional[str] = None


# ==============================================================================
# 3. OVERALL SCORE BREAKDOWN & FINALE OVERVIEW SCHEMAS (STEP 14)
# ==============================================================================

class FinaleOverallScoreBreakdownResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    round4_legal_battle_score: Optional[float] = Field(None, alias="round4LegalBattleScore")
    agent_guessing_points: Optional[float] = Field(None, alias="agentGuessingPoints")
    wallet_balance: float = Field(0.0, alias="walletBalance")
    carryover_percent: float = Field(DEFAULT_CARRYOVER_WEIGHT_PERCENT, alias="carryoverPercent")
    wallet_carryover_points: float = Field(0.0, alias="walletCarryoverPoints")
    total_final_score: Optional[float] = Field(None, alias="totalFinalScore")


class FinaleTeamGuessRecordResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    team_id: str = Field(..., alias="teamId")
    team_number: int = Field(..., alias="teamNumber")
    team_name: str = Field(..., alias="teamName")
    submission: Optional[TeamGuessSubmissionResponse] = None
    score_breakdown: FinaleOverallScoreBreakdownResponse = Field(..., alias="scoreBreakdown")
    placement: Optional[int] = None
    placement_title: Optional[str] = Field(None, alias="placementTitle")
    tie_requires_review: bool = Field(False, alias="tieRequiresReview")
    tie_reason: Optional[str] = Field(None, alias="tieReason")
    review_status: str = Field("Pending", alias="reviewStatus")


class FinaleGuessingOverviewResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    config: Dict[str, Any]
    records: List[FinaleTeamGuessRecordResponse] = Field(default_factory=list)
    can_finalize: bool = Field(False, alias="canFinalize")
    issues: List[Any] = Field(default_factory=list)
    checklist: List[Any] = Field(default_factory=list)
    ties_affecting_placement: bool = Field(False, alias="tiesAffectingPlacement")
    is_revealed: bool = Field(False, alias="isRevealed")
    champion_team_id: Optional[str] = Field(None, alias="championTeamId")
    runner_up1_team_id: Optional[str] = Field(None, alias="runnerUp1TeamId")
    runner_up2_team_id: Optional[str] = Field(None, alias="runnerUp2TeamId")


# ==============================================================================
# 4. LEGACY COMPATIBILITY SCHEMAS
# ==============================================================================

class SubmitScorecardInput(BaseModel):
    judge_name: str
    scores: Dict[str, Optional[float]]
    comments: Optional[str] = None


class SubmitAgentVerdictInput(BaseModel):
    suspected_agent: Optional[str] = None
    actual_agent: Optional[str] = None
    is_correct: Optional[bool] = None
    bonus_points: Optional[float] = None
    penalty_points: Optional[float] = None
    notes: Optional[str] = None


class FinaleConfigSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    is_scoring_rules_confirmed: bool = Field(False, alias="isScoringRulesConfirmed")
    confirmed_at: Optional[str] = Field(None, alias="confirmedAt")
    confirmed_by: Optional[str] = Field(None, alias="confirmedBy")
    criteria: List[Dict[str, Any]] = Field(default_factory=list)
    round4_score_carried_over: bool = Field(True, alias="round4ScoreCarriedOver")
    round4_score_weight: float = Field(1.0, alias="round4ScoreWeight")
    finale_activity_weight: float = Field(1.0, alias="finaleActivityWeight")
    advancing_teams_count: Optional[int] = Field(R4_ADVANCING_COUNT, alias="advancingTeamsCount")
    min_guesses: int = Field(AGENT_GUESS_MIN, alias="minGuesses")
    max_guesses: int = Field(AGENT_GUESS_MAX, alias="maxGuesses")
    correct_guess_points: float = Field(AGENT_CORRECT_GUESS, alias="correctGuessPoints")
    wrong_guess_points: float = Field(AGENT_WRONG_GUESS, alias="wrongGuessPoints")
    carryover_wallet_percent: float = Field(DEFAULT_CARRYOVER_WEIGHT_PERCENT, alias="carryoverWalletPercent")
    is_guessing_open: bool = Field(True, alias="isGuessingOpen")
    scoring_direction: str = Field("higher_wins", alias="scoringDirection")
    is_finalized: bool = Field(False, alias="isFinalized")
    finalized_at: Optional[str] = Field(None, alias="finalizedAt")
    finalized_by: Optional[str] = Field(None, alias="finalizedBy")
    is_revealed: bool = Field(False, alias="isRevealed")
    revealed_at: Optional[str] = Field(None, alias="revealedAt")
    revealed_by: Optional[str] = Field(None, alias="revealedBy")


class UpdateFinaleConfigInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    is_scoring_rules_confirmed: Optional[bool] = Field(None, alias="isScoringRulesConfirmed")
    criteria: Optional[List[Dict[str, Any]]] = None
    round4_score_carried_over: Optional[bool] = Field(None, alias="round4ScoreCarriedOver")
    round4_score_weight: Optional[float] = Field(None, alias="round4ScoreWeight")
    finale_activity_weight: Optional[float] = Field(None, alias="finaleActivityWeight")
    advancing_teams_count: Optional[int] = Field(None, alias="advancingTeamsCount")
    min_guesses: Optional[int] = Field(None, alias="minGuesses")
    max_guesses: Optional[int] = Field(None, alias="maxGuesses")
    correct_guess_points: Optional[float] = Field(None, alias="correctGuessPoints")
    wrong_guess_points: Optional[float] = Field(None, alias="wrongGuessPoints")
    carryover_wallet_percent: Optional[float] = Field(None, alias="carryoverWalletPercent")
    is_guessing_open: Optional[bool] = Field(None, alias="isGuessingOpen")
    scoring_direction: Optional[str] = Field(None, alias="scoringDirection")


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
    round4_weight: float = 1.0
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


# ==============================================================================
# 5. STEP 15 CHAMPIONSHIP SCORING & PODIUM SCHEMAS
# ==============================================================================

class FinalChampionshipScoreResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    team_id: Optional[str] = Field(None, alias="teamId")
    legal_battle_score: Optional[float] = Field(None, alias="legalBattleScore")
    agent_guessing_points: float = Field(0.0, alias="agentGuessingPoints")
    remaining_black_market_points: float = Field(0.0, alias="remainingBlackMarketPoints")
    carryover_weight: float = Field(0.10, alias="carryoverWeight")
    legal_battle_component: Optional[float] = Field(None, alias="legalBattleComponent")
    agent_guessing_component: float = Field(0.0, alias="agentGuessingComponent")
    black_market_component: float = Field(0.0, alias="blackMarketComponent")
    final_score: Optional[float] = Field(None, alias="finalScore")


class ChampionshipStandingItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    team_id: str = Field(..., alias="teamId")
    team_number: int = Field(..., alias="teamNumber")
    team_name: str = Field(..., alias="teamName")
    legal_battle_score: Optional[float] = Field(None, alias="legalBattleScore")
    agent_guessing_points: Optional[float] = Field(None, alias="agentGuessingPoints")
    remaining_black_market_points: float = Field(0.0, alias="remainingBlackMarketPoints")
    black_market_carryover_points: float = Field(0.0, alias="blackMarketCarryoverPoints")
    final_score: Optional[float] = Field(None, alias="finalScore")
    rank: int = 1
    is_top_four: bool = Field(False, alias="isTopFour")
    podium_position: Optional[int] = Field(None, alias="podiumPosition")
    placement_title: Optional[str] = Field(None, alias="placementTitle")
    tie_requires_review: bool = Field(False, alias="tieRequiresReview")
    tie_reason: Optional[str] = Field(None, alias="tieReason")
    is_tie_resolved: bool = Field(True, alias="isTieResolved")


class TopFourResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    is_revealed: bool = Field(False, alias="isRevealed")
    top_four: List[ChampionshipStandingItemResponse] = Field(default_factory=list, alias="topFour")
    tie_requires_review: bool = Field(False, alias="tieRequiresReview")
    tied_teams: List[str] = Field(default_factory=list, alias="tiedTeams")
    message: Optional[str] = None


class PodiumResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    is_revealed: bool = Field(False, alias="isRevealed")
    podium: List[ChampionshipStandingItemResponse] = Field(default_factory=list)
    champion: Optional[ChampionshipStandingItemResponse] = None
    runner_up1: Optional[ChampionshipStandingItemResponse] = Field(None, alias="runnerUp1")
    runner_up2: Optional[ChampionshipStandingItemResponse] = Field(None, alias="runnerUp2")
    tie_requires_review: bool = Field(False, alias="tieRequiresReview")
    tied_teams: List[str] = Field(default_factory=list, alias="tiedTeams")
    message: Optional[str] = None


class ResolveTieInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tie_type: str = Field("podium", alias="tieType", description="Type of tie: 'podium', 'top_four', 'best_agent'")
    decisions: Dict[str, Any] = Field(default_factory=dict, description="Custom ranking assignments or overrides")
    notes: Optional[str] = Field(None, description="Organizer justification and resolution notes")


class RevealStageInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    stage: str = Field("all", description="Stage to reveal: 'top_four', 'podium', 'secret_agents', 'all'")
