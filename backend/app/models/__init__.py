from app.models.user import User, UserRole
from app.models.team import Team, TeamStatus
from app.models.participant import Participant, ParticipantRole
from app.models.event_settings import EventSettings
from app.models.registration_submission import RegistrationSubmission, SubmissionStatus
from app.models.round_models import (
    RoundState,
    Round1Record,
    Round2Placement,
    Round3Transaction,
    Round3CodeRecord,
    Round4Pair,
    Round4JudgeScore,
    Round4AgentGuess,
    FinaleScorecard,
    FinaleAgentVerdict,
)
from app.models.round1 import Round1ConfigModel, MiniRoundTimingModel
from app.models.round2 import CaboConfigModel, CaboGameModel, CaboPlacementModel, default_cabo_point_table
from app.models.round3 import (
    BlackMarketConfigModel,
    BlackMarketTransactionModel,
    BlackMarketCodeFragmentModel,
    TeamCodeVerificationModel,
)
from app.models.round4 import (
    Round4ConfigModel,
    Round4PairModel,
    Round4StageTimingModel,
    Round4JudgeScoreModel,
    Round4AgentGuessModel,
)
from app.models.finale import (
    FinaleConfigModel,
    FinaleScorecardModel,
    FinaleAgentVerdictModel,
    FinaleTeamGuessSubmissionModel,
    FinaleAgentGuessModel,
    FinaleTeamGuessSubmission,
    FinaleAgentGuess,
    FinaleChampionshipStandingModel,
    FinaleChampionshipStanding,
    default_finale_criteria,
)
from app.models.progression import RoundQualification, TieReview, AuditLog
from app.models.core import seed_default_teams

# Official Tournament Models (Step 8)
from app.models.wallet import TeamWallet, WalletTransaction, TransactionType
from app.models.cabo import CaboTableAssignment, CaboPlayerScorecard
from app.models.agent import (
    SecretAgentDossier,
    SecretAgentTask,
    AgentDossierStatus,
    AgentTaskStatus,
)
from app.models.code_hunt import FinalCodeRecord, FragmentStatus
from app.models.black_market import (
    BlackMarketPurchase,
    BlackMarketAssetType,
    PurchaseStatus,
    BlackMarketAuction,
    BlackMarketBid,
    AuctionStatus,
    BidStatus,
)

__all__ = [
    # Core Tharun models
    "User",
    "UserRole",
    "Team",
    "TeamStatus",
    "Participant",
    "ParticipantRole",
    "EventSettings",
    "RegistrationSubmission",
    "SubmissionStatus",
    "RoundState",
    "Round1Record",
    "Round2Placement",
    "Round3Transaction",
    "Round3CodeRecord",
    "Round4Pair",
    "Round4JudgeScore",
    "Round4AgentGuess",
    "FinaleScorecard",
    "FinaleAgentVerdict",
    # Modular Round & Progression models
    "Round1ConfigModel",
    "MiniRoundTimingModel",
    "CaboConfigModel",
    "CaboGameModel",
    "CaboPlacementModel",
    "default_cabo_point_table",
    "BlackMarketConfigModel",
    "BlackMarketTransactionModel",
    "BlackMarketCodeFragmentModel",
    "TeamCodeVerificationModel",
    "Round4ConfigModel",
    "Round4PairModel",
    "Round4StageTimingModel",
    "Round4JudgeScoreModel",
    "Round4AgentGuessModel",
    "FinaleConfigModel",
    "FinaleScorecardModel",
    "FinaleAgentVerdictModel",
    "FinaleTeamGuessSubmissionModel",
    "FinaleAgentGuessModel",
    "FinaleTeamGuessSubmission",
    "FinaleAgentGuess",
    "FinaleChampionshipStandingModel",
    "FinaleChampionshipStanding",
    "default_finale_criteria",
    "RoundQualification",
    "TieReview",
    "AuditLog",
    "seed_default_teams",
    # Official Tournament Models (Step 8)
    "TeamWallet",
    "WalletTransaction",
    "TransactionType",
    "CaboTableAssignment",
    "CaboPlayerScorecard",
    "SecretAgentDossier",
    "SecretAgentTask",
    "AgentDossierStatus",
    "AgentTaskStatus",
    "FinalCodeRecord",
    "FragmentStatus",
    "BlackMarketPurchase",
    "BlackMarketAssetType",
    "PurchaseStatus",
    "BlackMarketAuction",
    "BlackMarketBid",
    "AuctionStatus",
    "BidStatus",
]