import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Text, ForeignKey
from datetime import datetime, timezone
from app.core.database import Base
from app.core.constants import (
    STARTING_WALLET_BALANCE,
    STARTING_WALLET_BALANCE,
    CODE_FRAGMENT_COUNT,
    FINAL_CODE_REQUIRED_FOR_R4,
)

def default_hidden_code_config():
    """
    Initial configuration state for Round 3 hidden code gate.
    Under official rules (FINAL_CODE_REQUIRED_FOR_R4), exactly 2 fragments (CODE_FRAGMENT_COUNT)
    are mandatory for Round 4 gate. Set to False initially until confirmed by organizers.
    """
    return {
        "isRequiredForQualification": False,
        "requiredFragmentCount": CODE_FRAGMENT_COUNT,
        "isConfigured": False,
        "instructionsNote": "Official fragment requirements: 2 fragments required for Round 4 gate."
    }

class BlackMarketConfigModel(Base):
    __tablename__ = "round3_config"

    id = Column(Integer, primary_key=True, default=1)
    # Note: Authoritative tournament wallet starting balance is STARTING_WALLET_BALANCE (1000.0).
    # Default is set to DEPRECATED_R3_STARTING_BALANCE (100.0) for backward compatibility with legacy tests.
    starting_balance = Column(Float, default=STARTING_WALLET_BALANCE, nullable=False)
    allow_negative_balance = Column(Boolean, default=False, nullable=False)
    ranking_metric = Column(String(50), default="current_balance", nullable=False)
    scoring_direction = Column(String(50), default="higher_is_better", nullable=False)
    is_scoring_configured = Column(Boolean, default=False, nullable=False)
    hidden_code_config = Column(JSON, default=default_hidden_code_config, nullable=False)
    is_finalized = Column(Boolean, default=False, nullable=False)
    finalized_at = Column(DateTime, nullable=True)
    finalized_by = Column(String(100), nullable=True)

from app.models.round_models import Round3Transaction
BlackMarketTransactionModel = Round3Transaction

class BlackMarketCodeFragmentModel(Base):
    __tablename__ = "round3_code_fragments"

    id = Column(String(100), primary_key=True)
    team_id = Column(String(50), ForeignKey("teams.id"), nullable=False, index=True)
    fragment_index = Column(Integer, nullable=False)
    recovered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    recovered_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

class TeamCodeVerificationModel(Base):
    __tablename__ = "round3_code_verifications"

    team_id = Column(String(50), ForeignKey("teams.id"), primary_key=True)
    is_complete = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String(100), nullable=True)
