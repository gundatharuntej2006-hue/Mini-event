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
    team_id: str = Field(..., serialization_alias="teamId")
    team_name: str = Field(..., serialization_alias="teamName")
    placement: Optional[int] = None
    placement_points: Optional[float] = Field(default=None, serialization_alias="placementPoints")
    final_card_hand_total: Optional[int] = Field(default=None, serialization_alias="finalCardHandTotal")

    model_config = {"populate_by_name": True, "from_attributes": True}


class CaboTableDetailResponse(BaseModel):
    game_number: int = Field(..., serialization_alias="gameNumber")
    table_number: int = Field(..., serialization_alias="tableNumber")
    is_completed: bool = Field(default=False, serialization_alias="isCompleted")
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
    combined_card_total: int = Field(..., serialization_alias="combinedCardTotal")
    first_place_count: int = Field(..., serialization_alias="firstPlaceCount")
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


class BlackMarketPurchaseResponse(BaseModel):
    id: str
    team_id: str = Field(..., serialization_alias="teamId")
    asset_type: BlackMarketAssetType = Field(..., serialization_alias="assetType")
    price: float
    quantity: int
    transaction_id: Optional[str] = Field(default=None, serialization_alias="transactionId")
    status: PurchaseStatus
    details: Optional[Dict[str, Any]] = None
    purchased_at: datetime = Field(..., serialization_alias="purchasedAt")
    purchased_by: Optional[str] = Field(default=None, serialization_alias="purchasedBy")

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
    final_code_verified: bool = Field(..., serialization_alias="finalCodeVerified")
    fragment_1_status: str = Field(..., serialization_alias="fragment1Status")
    fragment_2_status: str = Field(..., serialization_alias="fragment2Status")
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
    final_code_verified: bool = Field(..., serialization_alias="finalCodeVerified")
    is_complete: bool = Field(..., serialization_alias="isComplete")
    verified_at: Optional[datetime] = Field(default=None, serialization_alias="verifiedAt")
    verified_by: Optional[str] = Field(default=None, serialization_alias="verifiedBy")
    fragment_1_value: Optional[str] = Field(default=None, serialization_alias="fragment1Value")
    fragment_2_value: Optional[str] = Field(default=None, serialization_alias="fragment2Value")
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