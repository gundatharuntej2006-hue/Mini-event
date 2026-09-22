import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now


class SubmissionStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class RegistrationSubmission(Base):
    __tablename__ = "registration_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String(50), default="google_forms", nullable=False)  # google_forms, public_web
    external_submission_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    team_name: Mapped[str] = mapped_column(String(255), nullable=False)
    leader_name: Mapped[str] = mapped_column(String(255), nullable=False)
    leader_usn: Mapped[str] = mapped_column(String(100), nullable=False)
    leader_email: Mapped[str] = mapped_column(String(255), nullable=False)
    leader_phone: Mapped[str] = mapped_column(String(50), nullable=True)
    members_count: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=SubmissionStatus.PENDING.value, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    auto_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(255), nullable=True)

    # Optional relationship
    created_team = relationship("Team", foreign_keys=[created_team_id], lazy="joined")
