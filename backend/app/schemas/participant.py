from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.participant import ParticipantRole


class ParticipantBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    usn: str = Field(..., min_length=5, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=50)
    role: ParticipantRole = ParticipantRole.MEMBER
    checked_in: bool = Field(default=False, serialization_alias="checkedIn", alias="checkedIn")
    team_id: Optional[str] = Field(default=None, serialization_alias="teamId", alias="teamId")

    @field_validator("usn")
    @classmethod
    def normalize_usn(cls, v: str) -> str:
        return v.strip().upper()

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class ParticipantCreate(ParticipantBase):
    pass


class ParticipantUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    usn: Optional[str] = Field(default=None, min_length=5, max_length=50)
    phone: Optional[str] = None
    role: Optional[ParticipantRole] = None
    checked_in: Optional[bool] = Field(default=None, alias="checkedIn")
    team_id: Optional[str] = Field(default=None, alias="teamId")

    @field_validator("usn")
    @classmethod
    def normalize_usn(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip().upper()
        return v

    model_config = {
        "populate_by_name": True,
    }


class ParticipantTransferRequest(BaseModel):
    target_team_id: Optional[str] = Field(default=None, alias="targetTeamId")

    model_config = {
        "populate_by_name": True,
    }


class ParticipantCheckInToggle(BaseModel):
    checked_in: bool = Field(..., alias="checkedIn")

    model_config = {
        "populate_by_name": True,
    }


class ParticipantResponse(BaseModel):
    """Full participant model returned only to authenticated staff."""
    id: str
    name: str
    email: Optional[str] = None
    usn: Optional[str] = None
    phone: Optional[str] = None
    role: ParticipantRole
    checked_in: bool = Field(serialization_alias="checkedIn")
    checked_in_at: Optional[datetime] = Field(default=None, serialization_alias="checkedInAt")
    team_id: Optional[str] = Field(default=None, serialization_alias="teamId")
    team_name: Optional[str] = Field(default=None, serialization_alias="teamName")
    created_at: datetime = Field(serialization_alias="createdAt")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class ParticipantPublicResponse(BaseModel):
    """Sanitized public projection model with PII stripped."""
    id: str
    name: str
    role: ParticipantRole
    checked_in: bool = Field(serialization_alias="checkedIn")
    team_id: Optional[str] = Field(default=None, serialization_alias="teamId")
    team_name: Optional[str] = Field(default=None, serialization_alias="teamName")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }