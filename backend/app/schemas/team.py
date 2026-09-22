from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.team import TeamStatus
from app.models.participant import ParticipantRole
from app.schemas.participant import ParticipantResponse


class TeamMemberInput(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    usn: str = Field(..., min_length=5, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=50)
    role: ParticipantRole = ParticipantRole.MEMBER

    @field_validator("usn")
    @classmethod
    def normalize_usn(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: EmailStr) -> str:
        return str(v).strip().lower()

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class TeamBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    assigned_table: Optional[str] = Field(default=None, serialization_alias="assignedTable", alias="assignedTable")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class TeamCreate(TeamBase):
    members: Optional[List[TeamMemberInput]] = Field(default=None)


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    assigned_table: Optional[str] = Field(default=None, alias="assignedTable")
    status: Optional[TeamStatus] = None

    model_config = {
        "populate_by_name": True,
    }


class TeamResponse(BaseModel):
    id: str
    team_number: int = Field(serialization_alias="teamNumber")
    name: str
    leader_name: str = Field(default="Unassigned", serialization_alias="leaderName")
    members_count: int = Field(default=0, serialization_alias="membersCount")
    members: List[ParticipantResponse] = Field(default_factory=list)
    status: TeamStatus
    current_round: int = Field(default=1, serialization_alias="currentRound")
    is_qualified_for_next_round: bool = Field(default=False, serialization_alias="isQualifiedForNextRound")
    total_score: float = Field(default=0.0, serialization_alias="totalScore")
    assigned_table: Optional[str] = Field(default=None, serialization_alias="assignedTable")
    created_at: datetime = Field(serialization_alias="createdAt")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }
