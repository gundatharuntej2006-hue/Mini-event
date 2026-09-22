import secrets
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, utc_now


def generate_webhook_secret() -> str:
    return f"whsec_{secrets.token_hex(24)}"


class EventSettings(Base):
    __tablename__ = "event_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    event_name: Mapped[str] = mapped_column(String(255), default="EVENT HQ · BMSIT 2026", nullable=False)
    current_round_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_round_name: Mapped[str] = mapped_column(String(255), default="Round 1: Clue Hunt", nullable=False)
    current_round_status: Mapped[str] = mapped_column(String(50), default="In Progress", nullable=False)
    table_count: Mapped[int] = mapped_column(Integer, default=32, nullable=False)
    is_mock_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    registration_auto_approve: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    webhook_secret: Mapped[str] = mapped_column(String(255), default=generate_webhook_secret, nullable=False)
    public_registration_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
