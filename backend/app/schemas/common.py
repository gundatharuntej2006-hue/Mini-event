from datetime import datetime, timezone
from typing import Generic, Optional, TypeVar, List, Any
from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")


def utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: Optional[str] = None
    isMockData: bool = Field(default=False, serialization_alias="isMockData")
    timestamp: str = Field(default_factory=utc_iso_now)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }


class PaginatedData(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    pageSize: int = Field(serialization_alias="pageSize")
    totalPages: int = Field(serialization_alias="totalPages")

    model_config = {
        "populate_by_name": True,
    }


# =========================================================================
# Tournament Progression & Finalization Schemas
# =========================================================================

class FinalizationIssue(BaseModel):
    code: str
    message: str


class FinalizationResponse(BaseModel):
    can_finalize: bool = True
    issues: List[FinalizationIssue] = []
    finalized: bool = False
    advancing_team_ids: List[str] = Field(default_factory=list)
    champion_team_id: Optional[str] = None
    message: Optional[str] = None

    # Compatibility fields for legacy FinalizeRoundResponse
    success: bool = True
    round_number: Optional[int] = None
    roundNumber: Optional[int] = None
    qualified_team_ids: List[str] = Field(default_factory=list)
    qualifiedTeamIds: List[str] = Field(default_factory=list)
    total_eligible: int = 0
    totalEligible: int = 0

    @model_validator(mode="before")
    @classmethod
    def populate_compat_fields(cls, data: Any):
        if isinstance(data, dict):
            adv = data.get("advancing_team_ids") or data.get("qualified_team_ids") or data.get("qualifiedTeamIds") or []
            data["advancing_team_ids"] = adv
            data["qualified_team_ids"] = adv
            data["qualifiedTeamIds"] = adv
            r_num = data.get("round_number") or data.get("roundNumber")
            data["round_number"] = r_num
            data["roundNumber"] = r_num
            tot = data.get("total_eligible") or data.get("totalEligible") or len(adv)
            data["total_eligible"] = tot
            data["totalEligible"] = tot
        return data

    model_config = {
        "populate_by_name": True,
    }


class TieReviewResponse(BaseModel):
    id: str
    round_number: int
    teams_involved: List[Any]
    ranking_metric: str
    cutoff_position: int
    tie_breaker_status: str
    review_status: str
    organizer_decision: Optional[str] = None
    advancing_team_ids: Optional[List[str]] = None
    eliminated_team_ids: Optional[List[str]] = None
    decision_timestamp: Optional[str] = None
    decided_by: Optional[str] = None
    notes: Optional[str] = None


class ResolveTieRequest(BaseModel):
    decision: str  # e.g. "MANUAL_ORDER", "SPECIAL_REMATCH"
    advancing_team_ids: List[str]
    eliminated_team_ids: List[str]
    notes: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: int
    action: str
    round_number: Optional[int] = None
    entity_type: str
    entity_id: str
    actor_id: str
    actor_role: str
    details: Optional[Any] = None
    timestamp: str
