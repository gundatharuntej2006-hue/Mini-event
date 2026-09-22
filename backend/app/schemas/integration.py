from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ExternalParticipantInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    usn: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    role: Optional[str] = Field("Member", max_length=20)

    @field_validator("usn", mode="after")
    @classmethod
    def normalize_usn(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("name", mode="after")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return v.strip()


class ExternalRegistrationInput(BaseModel):
    submission_id: Optional[str] = None
    team_name: str = Field(..., min_length=1, max_length=255)
    leader: Optional[ExternalParticipantInput] = None
    members: Optional[List[ExternalParticipantInput]] = None
    consent_given: bool = True
    source: Optional[str] = "google_forms"

    @field_validator("team_name", mode="after")
    @classmethod
    def normalize_team_name(cls, v: str) -> str:
        return v.strip()


class SubmissionResponse(BaseModel):
    id: str
    source: str
    external_submission_id: str
    team_name: str
    leader_name: str
    leader_usn: str
    leader_email: str
    leader_phone: Optional[str] = None
    members_count: int
    consent_given: bool
    status: str
    error_message: Optional[str] = None
    created_team_id: Optional[str] = None
    raw_payload: Dict[str, Any]
    auto_approved: bool
    submitted_at: str
    processed_at: Optional[str] = None
    reviewed_by: Optional[str] = None

    model_config = {"from_attributes": True}


class SubmissionMetricsResponse(BaseModel):
    total_submissions: int
    accepted_count: int
    pending_count: int
    rejected_count: int
    last_submission_at: Optional[str] = None
    last_sync_at: Optional[str] = None


class IntegrationSettingsResponse(BaseModel):
    webhook_url: str
    webhook_secret: str
    registration_auto_approve: bool
    public_registration_open: bool
    metrics: SubmissionMetricsResponse


class IntegrationSettingsUpdate(BaseModel):
    registration_auto_approve: Optional[bool] = None
    public_registration_open: Optional[bool] = None
    regenerate_secret: Optional[bool] = None


class SubmissionActionInput(BaseModel):
    action: str = Field(..., description="'approve', 'reject', or 'retry'")
    reason: Optional[str] = None
