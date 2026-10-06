from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class CreateTransactionInput(BaseModel):
    amount: float = Field(..., gt=0)
    type: str = Field(..., pattern="^(earn|spend|adjustment)$", description="earn | spend | adjustment")
    reason: str = Field(..., min_length=1)
    notes: Optional[str] = None

class ReverseTransactionInput(BaseModel):
    reason: Optional[str] = "Organizer reversal"

class AddFragmentInput(BaseModel):
    fragment_index: int = Field(..., ge=1)
    notes: Optional[str] = None

class VerifyCodeInput(BaseModel):
    is_complete: bool = True

class BlackMarketConfigSchema(BaseModel):
    starting_balance: float = 1000.0  # Section 3.3
    allow_negative_balance: bool = False
    ranking_metric: str = "current_balance"
    scoring_direction: str = "higher_is_better"
    is_scoring_configured: bool = False
    hidden_code_config: Dict[str, Any] = {}
    is_finalized: bool = False
    finalized_at: Optional[str] = None
    finalized_by: Optional[str] = None

class UpdateBlackMarketConfigInput(BaseModel):
    starting_balance: Optional[float] = None
    allow_negative_balance: Optional[bool] = None
    ranking_metric: Optional[str] = None
    scoring_direction: Optional[str] = None
    is_scoring_configured: Optional[bool] = None
    hidden_code_config: Optional[Dict[str, Any]] = None

class TransactionResponse(BaseModel):
    id: str
    team_id: str
    amount: float
    type: str
    reason: str
    organizer_ref: Optional[str] = None
    timestamp: str
    is_reversed: bool = False
    reversal_transaction_id: Optional[str] = None
    reversed_transaction_id: Optional[str] = None
    notes: Optional[str] = None

class LedgerResponse(BaseModel):
    team_id: str
    opening_balance: float
    total_earned: float
    total_spent: float
    net_adjustments: float
    current_balance: float
    active_transaction_count: int
    reversal_count: int
    transactions: List[TransactionResponse] = []

class TeamCodeRecordResponse(BaseModel):
    team_id: str
    fragments: List[int] = []
    is_complete: bool = False
    verified_at: Optional[str] = None
    verified_by: Optional[str] = None

class TeamRound3RecordResponse(BaseModel):
    team_id: str
    team_number: int
    team_name: str
    round2_qualified: bool
    ledger: LedgerResponse
    code_record: TeamCodeRecordResponse
    rank: Optional[int] = None
    tie_requires_review: bool = False
    tie_reason: Optional[str] = None
    qualification_status: str

class Round3OverviewResponse(BaseModel):
    config: BlackMarketConfigSchema
    records: List[TeamRound3RecordResponse]
    can_finalize: bool
    issues: List[Any] = []
    ties_affecting_cutoff: bool = False
    total_volume: float = 0.0
    total_transactions: int = 0
