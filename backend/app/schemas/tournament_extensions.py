"""
Pydantic Request & Response Schemas for Official Tournament Models (Step 8).
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Security Policy:
- Secret Agent dossiers and undercover identities MUST NEVER be serialized via public schemas.
- SecretAgentDossierResponse is restricted strictly to ORGANIZER / MARSHAL endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.wallet import TransactionType
from app.models.agent import AgentDossierStatus, AgentTaskStatus
from app.models.code_hunt import FragmentStatus
from app.models.black_market import BlackMarketAssetType, PurchaseStatus, AuctionStatus, BidStatus


# ==============================================================================
# 1. WALLET SCHEMAS
# ==============================================================================
class TeamWalletResponse(BaseModel):
    id: str
    team_id: str = Field(..., serialization_alias="teamId")
    current_balance: float = Field(..., serialization_alias="currentBalance")
    total_earned: float = Field(default=0.0, serialization_alias="totalEarned")
    total_spent: float = Field(default=0.0, serialization_alias="totalSpent")
    total_penalties: float = Field(default=0.0, serialization_alias="totalPenalties")
    created_at: datetime = Field(..., serialization_alias="createdAt")
    updated_at: datetime = Field(..., serialization_alias="updatedAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class WalletTransactionResponse(BaseModel):
    id: str
    wallet_id: str = Field(..., serialization_alias="walletId")
    team_id: str = Field(..., serialization_alias="teamId")
    transaction_type: TransactionType = Field(..., serialization_alias="transactionType")
    amount: float
    balance_before: float = Field(..., serialization_alias="balanceBefore")
    balance_after: float = Field(..., serialization_alias="balanceAfter")
    reference_type: Optional[str] = Field(default=None, serialization_alias="referenceType")
    reference_id: Optional[str] = Field(default=None, serialization_alias="referenceId")
    description: str
    is_reversed: bool = Field(default=False, serialization_alias="isReversed")
    created_at: datetime = Field(..., serialization_alias="createdAt")
    created_by: Optional[str] = Field(default=None, serialization_alias="createdBy")

    model_config = {"populate_by_name": True, "from_attributes": True}


class WalletAdjustmentCreate(BaseModel):
    amount: float = Field(..., description="Positive or negative point adjustment amount")
    reason: str = Field(..., min_length=3, max_length=255, description="Audit reason for manual balance change")
    allow_negative_balance: bool = Field(default=False, alias="allowNegativeBalance")


class WalletPenaltyCreate(BaseModel):
    amount: float = Field(..., description="Penalty deduction (e.g., -50 to -200 or 50 to 200)")
    reason: str = Field(..., min_length=3, max_length=255, description="Infraction reason for disciplinary penalty")


# ==============================================================================
# 2. CABO TABLE ASSIGNMENT & SCORECARD SCHEMAS
# ==============================================================================
class CaboTableAssignmentCreate(BaseModel):
    game_number: int = Field(..., ge=1, le=3, serialization_alias="gameNumber", alias="gameNumber")
    table_number: int = Field(..., ge=1, le=24, serialization_alias="tableNumber", alias="tableNumber")
    participant_id: str = Field(..., serialization_alias="participantId", alias="participantId")
    team_id: str = Field(..., serialization_alias="teamId", alias="teamId")
    seat_position: int = Field(..., ge=1, le=5, serialization_alias="seatPosition", alias="seatPosition")

    model_config = {"populate_by_name": True, "from_attributes": True}


class CaboTableAssignmentResponse(BaseModel):
    id: str
    game_number: int = Field(..., serialization_alias="gameNumber")
    table_number: int = Field(..., serialization_alias="tableNumber")
    participant_id: str = Field(..., serialization_alias="participantId")
    team_id: str = Field(..., serialization_alias="teamId")
    seat_position: int = Field(..., serialization_alias="seatPosition")
    created_at: datetime = Field(..., serialization_alias="createdAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class CaboPlayerScorecardCreate(BaseModel):
    game_number: int = Field(..., ge=1, le=3, serialization_alias="gameNumber", alias="gameNumber")
    participant_id: str = Field(..., serialization_alias="participantId", alias="participantId")
    team_id: str = Field(..., serialization_alias="teamId", alias="teamId")
    table_assignment_id: Optional[str] = Field(default=None, serialization_alias="tableAssignmentId", alias="tableAssignmentId")
    placement: int = Field(..., ge=1, le=5)
    final_card_hand_total: Optional[int] = Field(default=None, serialization_alias="finalCardHandTotal", alias="finalCardHandTotal")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "from_attributes": True}


class CaboPlayerScorecardResponse(BaseModel):
    id: str
    game_number: int = Field(..., serialization_alias="gameNumber")
    participant_id: str = Field(..., serialization_alias="participantId")
    team_id: str = Field(..., serialization_alias="teamId")
    table_assignment_id: Optional[str] = Field(default=None, serialization_alias="tableAssignmentId")
    placement: int
    placement_points: float = Field(..., serialization_alias="placementPoints")
    final_card_hand_total: Optional[int] = Field(default=None, serialization_alias="finalCardHandTotal")
    notes: Optional[str] = None
    created_at: datetime = Field(..., serialization_alias="createdAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class CaboGenerateTablesRequest(BaseModel):
    seed: Optional[int] = Field(default=None, description="Optional randomization seed for deterministic scheduling")
    force_regenerate: bool = Field(default=False, alias="forceRegenerate", description="Force overwrite unfinalized table assignments")


class CaboTablePlayerInfo(BaseModel):
    seat_position: int = Field(..., serialization_alias="seatPosition")
    participant_id: str = Field(..., serialization_alias="participantId")
    participant_name: str = Field(..., serialization_alias="participantName")
    participant_usn: Optional[str] = Field(default=None, serialization_alias="participantUsn")
    team_id: str = Field(..., serialization_alias="teamId")
    team_name: str = Field(..., serialization_alias="teamName")
    placement: Optional[int] = None
    placement_points: Optional[float] = Field(default=None, serialization_alias="placementPoints")
    final_card_hand_total: Optional[int] = Field(default=None, serialization_alias="finalCardHandTotal")
    is_verified: bool = Field(default=False, serialization_alias="isVerified")
    verified_by: Optional[str] = Field(default=None, serialization_alias="verifiedBy")
    verified_at: Optional[str] = Field(default=None, serialization_alias="verifiedAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class CaboTableDetailResponse(BaseModel):
    game_number: int = Field(..., serialization_alias="gameNumber")
    table_number: int = Field(..., serialization_alias="tableNumber")
    is_completed: bool = Field(default=False, serialization_alias="isCompleted")
    is_verified: bool = Field(default=False, serialization_alias="isVerified")
    players: List[CaboTablePlayerInfo]

    model_config = {"populate_by_name": True, "from_attributes": True}


class CaboRecordTableScoresRequest(BaseModel):
    table_number: int = Field(..., ge=1, le=24, alias="tableNumber")
    scores: List[CaboPlayerScorecardCreate]


class CaboTeamStandingResponse(BaseModel):
    team_id: str = Field(..., serialization_alias="teamId")
    team_name: str = Field(..., serialization_alias="teamName")
    team_number: int = Field(..., serialization_alias="teamNumber")
    cabo_score: float = Field(..., serialization_alias="caboScore")
    game1_score: Optional[float] = Field(default=None, serialization_alias="game1Score")
    game2_score: Optional[float] = Field(default=None, serialization_alias="game2Score")
    game3_score: Optional[float] = Field(default=None, serialization_alias="game3Score")
    combined_card_total: int = Field(..., serialization_alias="combinedCardTotal")
    first_place_count: int = Field(..., serialization_alias="firstPlaceCount")
    echo_status: str = Field(default="PENDING", serialization_alias="echoStatus")
    echo_e_verified: bool = Field(default=False, serialization_alias="echoEVerified")
    echo_c_verified: bool = Field(default=False, serialization_alias="echoCVerified")
    echo_ho_verified: bool = Field(default=False, serialization_alias="echoHoVerified")
    prime_status: str = Field(default="PENDING", serialization_alias="primeStatus")
    prime_sequence_verified: bool = Field(default=False, serialization_alias="primeSequenceVerified")
    rank: int
    is_qualified: bool = Field(..., serialization_alias="isQualified")
    is_tied_unresolved: bool = Field(default=False, serialization_alias="isTiedUnresolved")
    tie_reason: Optional[str] = Field(default=None, serialization_alias="tieReason")

    model_config = {"populate_by_name": True, "from_attributes": True}


class CaboFinalizationResponse(BaseModel):
    is_finalized: bool = Field(..., serialization_alias="isFinalized")
    finalized_at: str = Field(..., serialization_alias="finalizedAt")
    finalized_by: str = Field(..., serialization_alias="finalizedBy")
    qualified_teams_count: int = Field(..., serialization_alias="qualifiedTeamsCount")
    qualified_team_ids: List[str] = Field(..., serialization_alias="qualifiedTeamIds")
    standings: List[CaboTeamStandingResponse]

    model_config = {"populate_by_name": True, "from_attributes": True}


class CaboEchoVerifyRequest(BaseModel):
    game_1_e: bool = Field(default=False, alias="game1E")
    game_2_c: bool = Field(default=False, alias="game2C")
    game_3_ho: bool = Field(default=False, alias="game3Ho")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True}


class CaboPrimeVerifyRequest(BaseModel):
    sequence: Optional[List[int]] = None
    is_verified: bool = Field(default=True, alias="isVerified")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True}


class CaboSwapSeatsRequest(BaseModel):
    game_number: int = Field(..., ge=1, le=3, alias="gameNumber")
    assignment_id_1: str = Field(..., alias="assignmentId1")
    assignment_id_2: str = Field(..., alias="assignmentId2")

    model_config = {"populate_by_name": True}


class CaboSummaryResponse(BaseModel):
    total_tables_per_game: int = Field(default=16, serialization_alias="totalTablesPerGame")
    expected_total_tables: int = Field(default=48, serialization_alias="expectedTotalTables")
    expected_total_scorecards: int = Field(default=240, serialization_alias="expectedTotalScorecards")
    game1_completed_tables: int = Field(default=0, serialization_alias="game1CompletedTables")
    game2_completed_tables: int = Field(default=0, serialization_alias="game2CompletedTables")
    game3_completed_tables: int = Field(default=0, serialization_alias="game3CompletedTables")
    total_completed_tables: int = Field(default=0, serialization_alias="totalCompletedTables")
    total_scorecards: int = Field(default=0, serialization_alias="totalScorecards")
    is_finalized: bool = Field(default=False, serialization_alias="isFinalized")
    is_tables_confirmed: bool = Field(default=False, serialization_alias="isTablesConfirmed")
    tables_confirmed_at: Optional[str] = Field(default=None, serialization_alias="tablesConfirmedAt")
    tables_confirmed_by: Optional[str] = Field(default=None, serialization_alias="tablesConfirmedBy")
    has_cutoff_tie: bool = Field(default=False, serialization_alias="hasCutoffTie")
    can_finalize: bool = Field(default=False, serialization_alias="canFinalize")
    incomplete_reasons: List[str] = Field(default_factory=list, serialization_alias="incompleteReasons")

    model_config = {"populate_by_name": True}


class CaboTableValidationResponse(BaseModel):
    is_valid: bool = Field(..., serialization_alias="isValid")
    is_confirmed: bool = Field(default=False, serialization_alias="isConfirmed")
    confirmed_at: Optional[str] = Field(default=None, serialization_alias="confirmedAt")
    confirmed_by: Optional[str] = Field(default=None, serialization_alias="confirmedBy")
    total_teams: int = Field(..., serialization_alias="totalTeams")
    total_players: int = Field(..., serialization_alias="totalPlayers")
    total_tables: int = Field(..., serialization_alias="totalTables")
    constraints: Dict[str, bool]
    errors: List[str]

    model_config = {"populate_by_name": True}


class CaboConfirmTablesResponse(BaseModel):
    is_confirmed: bool = Field(..., serialization_alias="isConfirmed")
    confirmed_at: str = Field(..., serialization_alias="confirmedAt")
    confirmed_by: str = Field(..., serialization_alias="confirmedBy")
    message: str

    model_config = {"populate_by_name": True}


class CaboPlayerGameDetail(BaseModel):
    game_number: int = Field(..., serialization_alias="gameNumber")
    table_number: int = Field(..., serialization_alias="tableNumber")
    seat_position: int = Field(..., serialization_alias="seatPosition")
    placement: Optional[int] = None
    placement_points: Optional[float] = Field(default=None, serialization_alias="placementPoints")
    final_card_hand_total: Optional[int] = Field(default=None, serialization_alias="finalCardHandTotal")
    is_verified: bool = Field(default=False, serialization_alias="isVerified")

    model_config = {"populate_by_name": True}


class CaboPlayerDetailResponse(BaseModel):
    participant_id: str = Field(..., serialization_alias="participantId")
    participant_name: str = Field(..., serialization_alias="participantName")
    participant_usn: Optional[str] = Field(default=None, serialization_alias="participantUsn")
    team_id: str = Field(..., serialization_alias="teamId")
    team_name: str = Field(..., serialization_alias="teamName")
    team_number: Optional[int] = Field(default=None, serialization_alias="teamNumber")
    games: List[CaboPlayerGameDetail]
    total_points: float = Field(default=0.0, serialization_alias="totalPoints")
    first_places_count: int = Field(default=0, serialization_alias="firstPlacesCount")

    model_config = {"populate_by_name": True}


class CaboTeamMemberPerformance(BaseModel):
    participant_id: str = Field(..., serialization_alias="participantId")
    participant_name: str = Field(..., serialization_alias="participantName")
    participant_usn: Optional[str] = Field(default=None, serialization_alias="participantUsn")
    role: str
    game1_table: Optional[int] = Field(default=None, serialization_alias="game1Table")
    game1_placement: Optional[int] = Field(default=None, serialization_alias="game1Placement")
    game1_points: Optional[float] = Field(default=None, serialization_alias="game1Points")
    game2_table: Optional[int] = Field(default=None, serialization_alias="game2Table")
    game2_placement: Optional[int] = Field(default=None, serialization_alias="game2Placement")
    game2_points: Optional[float] = Field(default=None, serialization_alias="game2Points")
    game3_table: Optional[int] = Field(default=None, serialization_alias="game3Table")
    game3_placement: Optional[int] = Field(default=None, serialization_alias="game3Placement")
    game3_points: Optional[float] = Field(default=None, serialization_alias="game3Points")
    total_individual_points: float = Field(default=0.0, serialization_alias="totalIndividualPoints")

    model_config = {"populate_by_name": True}


class CaboTeamDetailResponse(BaseModel):
    team_id: str = Field(..., serialization_alias="teamId")
    team_name: str = Field(..., serialization_alias="teamName")
    team_number: int = Field(..., serialization_alias="teamNumber")
    members: List[CaboTeamMemberPerformance]
    game1_total: float = Field(default=0.0, serialization_alias="game1Total")
    game2_total: float = Field(default=0.0, serialization_alias="game2Total")
    game3_total: float = Field(default=0.0, serialization_alias="game3Total")
    cabo_squad_total: float = Field(default=0.0, serialization_alias="caboSquadTotal")
    rank: Optional[int] = None
    is_qualified: bool = Field(default=False, serialization_alias="isQualified")

    model_config = {"populate_by_name": True}


class CaboScoreCorrectionRequest(BaseModel):
    participant_id: str = Field(..., serialization_alias="participantId", alias="participantId")
    new_placement: int = Field(..., ge=1, le=5, serialization_alias="newPlacement", alias="newPlacement")
    reason: str = Field(..., min_length=3, max_length=500, description="Mandatory audit reason for organizer correction")
    new_card_total: Optional[int] = Field(default=None, alias="newCardTotal")

    model_config = {"populate_by_name": True}


class CaboPrintableTablePlayer(BaseModel):
    seat_position: int = Field(..., serialization_alias="seatPosition")
    participant_name: str = Field(..., serialization_alias="participantName")
    participant_usn: Optional[str] = Field(default=None, serialization_alias="participantUsn")
    team_name: str = Field(..., serialization_alias="teamName")
    team_number: Optional[int] = Field(default=None, serialization_alias="teamNumber")

    model_config = {"populate_by_name": True}


class CaboPrintableTableSheet(BaseModel):
    table_number: int = Field(..., serialization_alias="tableNumber")
    game_number: int = Field(..., serialization_alias="gameNumber")
    players: List[CaboPrintableTablePlayer]

    model_config = {"populate_by_name": True}


class CaboPrintableSheetResponse(BaseModel):
    game_number: int = Field(..., serialization_alias="gameNumber")
    tables: List[CaboPrintableTableSheet]

    model_config = {"populate_by_name": True}


# ==============================================================================
# 3. SECRET AGENT SCHEMAS (CONFIDENTIAL / ORGANIZER ONLY)
# ==============================================================================
class SecretAgentDossierResponse(BaseModel):
    """CONFIDENTIAL: Accessible strictly by organizers and assigned lead marshals."""
    id: str
    team_id: str = Field(..., serialization_alias="teamId")
    participant_id: str = Field(..., serialization_alias="participantId")
    codename: Optional[str] = None
    status: AgentDossierStatus
    assigned_at: datetime = Field(..., serialization_alias="assignedAt")
    created_at: datetime = Field(..., serialization_alias="createdAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class SecretAgentTaskCreate(BaseModel):
    task_description: str = Field(..., min_length=5, serialization_alias="taskDescription", alias="taskDescription")
    reward_points: float = Field(default=50.0, serialization_alias="rewardPoints", alias="rewardPoints")

    model_config = {"populate_by_name": True, "from_attributes": True}


class SecretAgentTaskResponse(BaseModel):
    id: str
    dossier_id: str = Field(..., serialization_alias="dossierId")
    task_description: str = Field(..., serialization_alias="taskDescription")
    status: AgentTaskStatus
    assigned_at: datetime = Field(..., serialization_alias="assignedAt")
    submitted_at: Optional[datetime] = Field(default=None, serialization_alias="submittedAt")
    verified_at: Optional[datetime] = Field(default=None, serialization_alias="verifiedAt")
    evidence_reference: Optional[str] = Field(default=None, serialization_alias="evidenceReference")
    reward_points: float = Field(..., serialization_alias="rewardPoints")
    rejection_reason: Optional[str] = Field(default=None, serialization_alias="rejectionReason")
    created_at: datetime = Field(..., serialization_alias="createdAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


# ==============================================================================
# 4. FINAL CODE GATE SCHEMAS
# ==============================================================================
class FinalCodeRecordResponse(BaseModel):
    id: str
    team_id: str = Field(..., serialization_alias="teamId")
    fragment_1_status: FragmentStatus = Field(..., serialization_alias="fragment1Status")
    fragment_1_discovered_at: Optional[datetime] = Field(default=None, serialization_alias="fragment1DiscoveredAt")
    fragment_2_status: FragmentStatus = Field(..., serialization_alias="fragment2Status")
    fragment_2_discovered_at: Optional[datetime] = Field(default=None, serialization_alias="fragment2DiscoveredAt")
    fragment_3_status: FragmentStatus = Field(default=FragmentStatus.PENDING, serialization_alias="fragment3Status")
    fragment_3_discovered_at: Optional[datetime] = Field(default=None, serialization_alias="fragment3DiscoveredAt")
    fragment_4_status: FragmentStatus = Field(default=FragmentStatus.PENDING, serialization_alias="fragment4Status")
    fragment_4_discovered_at: Optional[datetime] = Field(default=None, serialization_alias="fragment4DiscoveredAt")
    gate_3_confirmed: bool = Field(default=False, serialization_alias="gate3Confirmed")
    gate_3_confirmed_at: Optional[datetime] = Field(default=None, serialization_alias="gate3ConfirmedAt")
    gate_3_confirmed_by: Optional[str] = Field(default=None, serialization_alias="gate3ConfirmedBy")
    final_code_verified: bool = Field(..., serialization_alias="finalCodeVerified")
    verified_at: Optional[datetime] = Field(default=None, serialization_alias="verifiedAt")
    verified_by: Optional[str] = Field(default=None, serialization_alias="verifiedBy")
    verification_notes: Optional[str] = Field(default=None, serialization_alias="verificationNotes")
    updated_at: datetime = Field(..., serialization_alias="updatedAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


# ==============================================================================
# 5. BLACK MARKET & ROUND 3 SCHEMAS
# ==============================================================================
class BlackMarketCatalogItem(BaseModel):
    asset_type: str = Field(..., serialization_alias="assetType", alias="assetType")
    name: str
    description: str
    suggested_price: float = Field(..., serialization_alias="suggestedPrice", alias="suggestedPrice")
    category: str = "TACTICAL_ADVANTAGE"
    requires_details: bool = Field(default=False, serialization_alias="requiresDetails", alias="requiresDetails")

    model_config = {"populate_by_name": True, "from_attributes": True}


class BlackMarketCatalogResponse(BaseModel):
    catalog: List[BlackMarketCatalogItem]
    round3_active: bool = Field(default=True, serialization_alias="round3Active")
    total_items: int = Field(default=4, serialization_alias="totalItems")

    model_config = {"populate_by_name": True, "from_attributes": True}


class BlackMarketAssetPurchaseRequest(BaseModel):
    team_id: str = Field(..., serialization_alias="teamId", alias="teamId")
    asset_type: str = Field(..., serialization_alias="assetType", alias="assetType")
    price: Optional[float] = None
    quantity: int = Field(default=1, ge=1)
    details: Optional[Dict[str, Any]] = None

    model_config = {"populate_by_name": True, "from_attributes": True}


class BlackMarketPurchaseCreate(BaseModel):
    asset_type: BlackMarketAssetType = Field(..., serialization_alias="assetType", alias="assetType")
    price: float
    quantity: int = 1
    details: Optional[Dict[str, Any]] = None

    model_config = {"populate_by_name": True, "from_attributes": True}


class BlackMarketApproveRequest(BaseModel):
    second_organizer_id: Optional[str] = Field(default=None, alias="secondOrganizerId", serialization_alias="secondOrganizerId")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True}


class BlackMarketPurchaseResponse(BaseModel):
    id: str
    team_id: str = Field(..., serialization_alias="teamId")
    asset_type: BlackMarketAssetType = Field(..., serialization_alias="assetType")
    price: float
    quantity: int
    transaction_id: Optional[str] = Field(default=None, serialization_alias="transactionId")
    status: PurchaseStatus
    approval_status: str = Field(default="APPROVED", serialization_alias="approvalStatus")
    first_approved_by: Optional[str] = Field(default=None, serialization_alias="firstApprovedBy")
    first_approved_at: Optional[datetime] = Field(default=None, serialization_alias="firstApprovedAt")
    second_approved_by: Optional[str] = Field(default=None, serialization_alias="secondApprovedBy")
    second_approved_at: Optional[datetime] = Field(default=None, serialization_alias="secondApprovedAt")
    details: Optional[Dict[str, Any]] = None
    purchased_at: datetime = Field(..., serialization_alias="purchasedAt")
    purchased_by: Optional[str] = Field(default=None, serialization_alias="purchasedBy")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "from_attributes": True}


class BlackMarketAuctionCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    item_type: str = Field(default="CUSTOM", serialization_alias="itemType", alias="itemType")
    starting_bid: float = Field(default=0.0, ge=0.0, serialization_alias="startingBid", alias="startingBid")
    reserve_price: Optional[float] = Field(default=None, ge=0.0, serialization_alias="reservePrice", alias="reservePrice")
    details: Optional[Dict[str, Any]] = None

    model_config = {"populate_by_name": True, "from_attributes": True}


class BlackMarketBidCreateRequest(BaseModel):
    team_id: str = Field(..., serialization_alias="teamId", alias="teamId")
    bid_amount: float = Field(..., gt=0, serialization_alias="bidAmount", alias="bidAmount")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "from_attributes": True}


class BlackMarketBidResponse(BaseModel):
    id: str
    auction_id: str = Field(..., serialization_alias="auctionId")
    team_id: str = Field(..., serialization_alias="teamId")
    bid_amount: Optional[float] = Field(default=None, serialization_alias="bidAmount")
    status: BidStatus
    submitted_at: datetime = Field(..., serialization_alias="submittedAt")
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "from_attributes": True}


class BlackMarketAuctionResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    item_type: str = Field(..., serialization_alias="itemType")
    starting_bid: float = Field(..., serialization_alias="startingBid")
    reserve_price: Optional[float] = Field(default=None, serialization_alias="reservePrice")
    status: AuctionStatus
    winning_bid_id: Optional[str] = Field(default=None, serialization_alias="winningBidId")
    winning_team_id: Optional[str] = Field(default=None, serialization_alias="winningTeamId")
    winning_amount: Optional[float] = Field(default=None, serialization_alias="winningAmount")
    details: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(..., serialization_alias="createdAt")
    closed_at: Optional[datetime] = Field(default=None, serialization_alias="closedAt")
    resolved_at: Optional[datetime] = Field(default=None, serialization_alias="resolvedAt")
    created_by: Optional[str] = Field(default=None, serialization_alias="createdBy")
    total_bids: int = Field(default=0, serialization_alias="totalBids")
    bids: Optional[List[BlackMarketBidResponse]] = None

    model_config = {"populate_by_name": True, "from_attributes": True}


class Round3TeamStanding(BaseModel):
    team_id: str = Field(..., serialization_alias="teamId")
    team_number: int = Field(..., serialization_alias="teamNumber")
    team_name: str = Field(..., serialization_alias="teamName")
    current_balance: float = Field(..., serialization_alias="currentBalance")
    total_spent: float = Field(default=0.0, serialization_alias="totalSpent")
    starting_balance: float = Field(default=1000.0, serialization_alias="startingBalance")
    base_balance: float = Field(default=1000.0, serialization_alias="baseBalance")
    r1_rank_points: float = Field(default=0.0, serialization_alias="r1RankPoints")
    r2_cabo_score: float = Field(default=0.0, serialization_alias="r2CaboScore")
    agent_task_bonus: float = Field(default=0.0, serialization_alias="agentTaskBonus")
    final_code_verified: bool = Field(..., serialization_alias="finalCodeVerified")
    fragment_1_status: str = Field(..., serialization_alias="fragment1Status")
    fragment_2_status: str = Field(..., serialization_alias="fragment2Status")
    fragment_3_status: str = Field(default="PENDING", serialization_alias="fragment3Status")
    fragment_4_status: str = Field(default="PENDING", serialization_alias="fragment4Status")
    verified_fragment_count: int = Field(default=0, serialization_alias="verifiedFragmentCount")
    missing_fragment_count: int = Field(default=0, serialization_alias="missingFragmentCount")
    missing_fragment_penalty: float = Field(default=0.0, serialization_alias="missingFragmentPenalty")
    effective_balance: float = Field(..., serialization_alias="effectiveBalance")
    rank: int
    is_advancing: bool = Field(..., serialization_alias="isAdvancing")
    elimination_reason: Optional[str] = Field(default=None, serialization_alias="eliminationReason")
    is_tied_cutoff: bool = Field(default=False, serialization_alias="isTiedCutoff")

    model_config = {"populate_by_name": True, "from_attributes": True}


class Round3StandingsResponse(BaseModel):
    standings: List[Round3TeamStanding]
    can_finalize: bool = Field(..., serialization_alias="canFinalize")
    code_contingency: bool = Field(default=False, serialization_alias="codeContingency")
    cutoff_tie: bool = Field(default=False, serialization_alias="cutoffTie")
    issues: List[str] = Field(default_factory=list)
    advancing_team_ids: List[str] = Field(default_factory=list, serialization_alias="advancingTeamIds")

    model_config = {"populate_by_name": True, "from_attributes": True}


class Round3FinalizationResponse(BaseModel):
    success: bool
    is_finalized: bool = Field(..., serialization_alias="isFinalized")
    finalized_at: str = Field(..., serialization_alias="finalizedAt")
    finalized_by: str = Field(..., serialization_alias="finalizedBy")
    qualified_teams_count: int = Field(..., serialization_alias="qualifiedTeamsCount")
    qualified_team_ids: List[str] = Field(..., serialization_alias="qualifiedTeamIds")
    message: str

    model_config = {"populate_by_name": True, "from_attributes": True}


# ==============================================================================
# 6. CODE HUNT & SECRET AGENT WORKFLOW SCHEMAS (STEP 11)
# ==============================================================================
class RecordFragmentRequest(BaseModel):
    fragment_value: str = Field(..., min_length=1, max_length=255, serialization_alias="fragmentValue", alias="fragmentValue")
    overwrite: bool = Field(default=False, description="Explicit authorization to overwrite previously recorded fragment")

    model_config = {"populate_by_name": True, "from_attributes": True}


class VerifyFinalCodeRequest(BaseModel):
    supplied_code: str = Field(..., min_length=1, max_length=255, serialization_alias="suppliedCode", alias="suppliedCode")
    notes: Optional[str] = Field(default=None, description="Optional organizer notes on verification")

    model_config = {"populate_by_name": True, "from_attributes": True}


class RecoverMissingFragmentRequest(BaseModel):
    fragment_number: int = Field(..., ge=1, le=2, serialization_alias="fragmentNumber", alias="fragmentNumber")
    price: Optional[float] = Field(default=None, description="Configurable purchase price in Black Market points (defaults to 400.0)")
    recovered_value: Optional[str] = Field(default=None, serialization_alias="recoveredValue", alias="recoveredValue")

    model_config = {"populate_by_name": True, "from_attributes": True}


class Round4EligibilityResponse(BaseModel):
    team_id: str = Field(..., serialization_alias="teamId")
    is_eligible: bool = Field(..., serialization_alias="isEligible")
    final_code_verified: bool = Field(..., serialization_alias="finalCodeVerified")
    message: str

    model_config = {"populate_by_name": True, "from_attributes": True}


class CodeHuntStatusResponse(BaseModel):
    team_id: str = Field(..., serialization_alias="teamId")
    fragment_1_status: FragmentStatus = Field(..., serialization_alias="fragment1Status")
    fragment_1_discovered_at: Optional[datetime] = Field(default=None, serialization_alias="fragment1DiscoveredAt")
    fragment_2_status: FragmentStatus = Field(..., serialization_alias="fragment2Status")
    fragment_2_discovered_at: Optional[datetime] = Field(default=None, serialization_alias="fragment2DiscoveredAt")
    fragment_3_status: FragmentStatus = Field(default=FragmentStatus.PENDING, serialization_alias="fragment3Status")
    fragment_3_discovered_at: Optional[datetime] = Field(default=None, serialization_alias="fragment3DiscoveredAt")
    fragment_4_status: FragmentStatus = Field(default=FragmentStatus.PENDING, serialization_alias="fragment4Status")
    fragment_4_discovered_at: Optional[datetime] = Field(default=None, serialization_alias="fragment4DiscoveredAt")
    gate_3_confirmed: bool = Field(default=False, serialization_alias="gate3Confirmed")
    gate_3_confirmed_at: Optional[datetime] = Field(default=None, serialization_alias="gate3ConfirmedAt")
    gate_3_confirmed_by: Optional[str] = Field(default=None, serialization_alias="gate3ConfirmedBy")
    final_code_verified: bool = Field(..., serialization_alias="finalCodeVerified")
    is_complete: bool = Field(..., serialization_alias="isComplete")
    verified_at: Optional[datetime] = Field(default=None, serialization_alias="verifiedAt")
    verified_by: Optional[str] = Field(default=None, serialization_alias="verifiedBy")
    fragment_1_value: Optional[str] = Field(default=None, serialization_alias="fragment1Value")
    fragment_2_value: Optional[str] = Field(default=None, serialization_alias="fragment2Value")
    fragment_3_value: Optional[str] = Field(default=None, serialization_alias="fragment3Value")
    fragment_4_value: Optional[str] = Field(default=None, serialization_alias="fragment4Value")
    final_code_assembled: Optional[str] = Field(default=None, serialization_alias="finalCodeAssembled")

    model_config = {"populate_by_name": True, "from_attributes": True}


class SecretAgentAssignRequest(BaseModel):
    participant_id: str = Field(..., serialization_alias="participantId", alias="participantId")
    codename: Optional[str] = Field(default=None, max_length=100)

    model_config = {"populate_by_name": True, "from_attributes": True}


class SecretAgentTaskSubmitRequest(BaseModel):
    evidence_reference: str = Field(..., min_length=1, serialization_alias="evidenceReference", alias="evidenceReference")

    model_config = {"populate_by_name": True, "from_attributes": True}


class SecretAgentTaskVerifyRequest(BaseModel):
    notes: Optional[str] = None

    model_config = {"populate_by_name": True, "from_attributes": True}


class SecretAgentTaskRejectRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=1, serialization_alias="rejectionReason", alias="rejectionReason")

    model_config = {"populate_by_name": True, "from_attributes": True}