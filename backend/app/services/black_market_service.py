"""
Round 3 — The Black Market & Qualification Engine Service for EVENT HQ.
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Manages:
- Configurable Black Market Catalog with suggested default prices
- Direct tactical asset purchases & missing code fragment recovery
- Sealed-bid auction creation, private bidding, and organizer resolution
- Mandatory Final Code qualification gate (checked FIRST before ranking)
- Code-less contingency evaluation (if >4 squads lack verified final code)
- Top 6 advancement engine based on remaining wallet balances
- Wallet balance preservation for Grand Finale 10% carryover
- Complete audit logging and tie-break review integration
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.black_market import (
    BlackMarketPurchase,
    BlackMarketAssetType,
    PurchaseStatus,
    BlackMarketAuction,
    BlackMarketBid,
    AuctionStatus,
    BidStatus,
)
from app.models.team import Team, TeamStatus
from app.models.wallet import TeamWallet, WalletTransaction, TransactionType
from app.models.code_hunt import FinalCodeRecord, FragmentStatus
from app.models.agent import SecretAgentDossier, SecretAgentTask, AgentTaskStatus
from app.models.cabo import CaboPlayerScorecard
from app.models.round3 import BlackMarketConfigModel, default_hidden_code_config
from app.models.round_models import RoundState
from app.models.progression import RoundQualification, TieReview
from app.core.constants import (
    BLACK_MARKET_SUGGESTED_PRICES,
    BLACK_MARKET_SECRET_CODE_1_PRICE_SUGGESTED,
    BLACK_MARKET_SECRET_CODE_2_PRICE_SUGGESTED,
    BLACK_MARKET_POWERUP_1_PRICE_SUGGESTED,
    BLACK_MARKET_POWERUP_2_PRICE_SUGGESTED,
    BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED,
    BLACK_MARKET_PREP_PRICE_SUGGESTED,
    BLACK_MARKET_WITNESS_PRICE_SUGGESTED,
    BLACK_MARKET_AGENT_INTEL_PRICE_SUGGESTED,
    R3_QUALIFIERS,
    R2_QUALIFIERS,
    R1_RANK_POINTS_MAP,
    AGENT_TASK_REWARD,
    STARTING_WALLET_BALANCE,
    MISSING_FRAGMENT_PENALTY,
)
from app.services import wallet as wallet_service
from app.services.wallet import InsufficientFundsError
from app.services import code_hunt_service
from app.services.audit_service import log_audit_event
from app.services.progression_service import is_round_finalized, get_eligible_team_ids, record_round_finalization
from app.services.tie_review_service import get_or_create_tie_review


# ==============================================================================
# DOMAIN EXCEPTIONS
# ==============================================================================
class BlackMarketError(Exception):
    """Base domain exception for Black Market operations."""
    pass


class MarketClosedError(BlackMarketError):
    """Raised when an action is attempted while the Black Market is closed or finalized."""
    pass


class TeamNotEligibleError(BlackMarketError):
    """Raised when a team is not qualified for Round 3."""
    pass


class InvalidAssetError(BlackMarketError):
    """Raised when an invalid asset type or pricing is requested."""
    pass


class AuctionNotFoundError(BlackMarketError):
    """Raised when an auction is not found."""
    pass


class AuctionClosedError(BlackMarketError):
    """Raised when attempting to bid on a non-open auction."""
    pass


class InvalidBidError(BlackMarketError):
    """Raised when a bid is invalid (e.g. exceeds wallet balance or below start price)."""
    pass


class FinalCodeGateError(BlackMarketError):
    """Raised when a team fails the mandatory Final Code gate."""
    pass


class RoundFinalizationError(BlackMarketError):
    """Raised when Round 3 finalization conditions are not met."""
    pass


# ==============================================================================
# CATALOG & CONFIGURATION
# ==============================================================================
DEFAULT_CATALOG = [
    {
        "asset_type": "SECRET_CODE_ITEM_1",
        "name": "Secret Code Item 1",
        "description": "First half of the qualification code. Must be combined with Secret Code Item 2 to form the required key for Round 4 qualification.",
        "suggested_price": BLACK_MARKET_SECRET_CODE_1_PRICE_SUGGESTED,
        "category": "GATE_REQUIREMENT",
        "requires_details": False,
    },
    {
        "asset_type": "SECRET_CODE_ITEM_2",
        "name": "Secret Code Item 2",
        "description": "Second half of the qualification code. Must be combined with Secret Code Item 1 to form the required key for Round 4 qualification.",
        "suggested_price": BLACK_MARKET_SECRET_CODE_2_PRICE_SUGGESTED,
        "category": "GATE_REQUIREMENT",
        "requires_details": False,
    },
    {
        "asset_type": "POWERUP_1_R4",
        "name": "Powerup 1 for Round 4",
        "description": "Strategic courtroom advantage carried forward into Round 4: The Legal Battle (grants bonus preparation time / priority evidence filing).",
        "suggested_price": BLACK_MARKET_POWERUP_1_PRICE_SUGGESTED,
        "category": "TACTICAL_ADVANTAGE",
        "requires_details": False,
    },
    {
        "asset_type": "POWERUP_2_R4",
        "name": "Powerup 2 for Round 4",
        "description": "Tactical courtroom advantage carried forward into Round 4: The Legal Battle (grants additional cross-examination question / rebuttal right).",
        "suggested_price": BLACK_MARKET_POWERUP_2_PRICE_SUGGESTED,
        "category": "TACTICAL_ADVANTAGE",
        "requires_details": False,
    },
    # Backward compatibility aliases
    {
        "asset_type": "MISSING_CODE_FRAGMENT",
        "name": "Missing Code Fragment Recovery",
        "description": "Recovers 1 missing physical QR code fragment required for the Final Code gate.",
        "suggested_price": BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED,
        "category": "GATE_REQUIREMENT",
        "requires_details": True,
    },
    {
        "asset_type": "EXTRA_PREP_TIME",
        "name": "Extra Trial Preparation Time",
        "description": "Grants additional strategic consultation time prior to Round 4: The Legal Battle.",
        "suggested_price": BLACK_MARKET_PREP_PRICE_SUGGESTED,
        "category": "TACTICAL_ADVANTAGE",
        "requires_details": False,
    },
    {
        "asset_type": "EXTRA_WITNESS_QUESTION",
        "name": "Additional Witness Questioning Right",
        "description": "Allows an additional cross-examination question during Round 4 witness testimonies.",
        "suggested_price": BLACK_MARKET_WITNESS_PRICE_SUGGESTED,
        "category": "TACTICAL_ADVANTAGE",
        "requires_details": False,
    },
    {
        "asset_type": "AGENT_INTEL",
        "name": "Classified Agent Intelligence Dossier",
        "description": "Confidential tactical intelligence regarding agent activity and opponent patterns.",
        "suggested_price": BLACK_MARKET_AGENT_INTEL_PRICE_SUGGESTED,
        "category": "TACTICAL_ADVANTAGE",
        "requires_details": False,
    },
]


def get_market_catalog(db: Session) -> List[Dict[str, Any]]:
    """
    Returns the complete list of available Black Market items with suggested default prices.
    """
    return [dict(item) for item in DEFAULT_CATALOG]


def get_or_create_r3_config(db: Session) -> BlackMarketConfigModel:
    """Retrieves or creates Round 3 configuration record."""
    cfg = db.query(BlackMarketConfigModel).filter(BlackMarketConfigModel.id == 1).first()
    if not cfg:
        cfg = BlackMarketConfigModel(
            id=1,
            starting_balance=100.0,
            allow_negative_balance=False,
            ranking_metric="current_balance",
            scoring_direction="higher_is_better",
            is_scoring_configured=False,
            hidden_code_config=default_hidden_code_config(),
            is_finalized=False
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def get_round3_eligible_teams(db: Session) -> List[Team]:
    """
    Returns the 12 qualified teams participating in Round 3.
    """
    eligible_ids = get_eligible_team_ids(db, 3)
    if eligible_ids:
        return db.query(Team).filter(Team.id.in_(eligible_ids)).all()

    # Fallback if Round 2 is in testing mode / not finalized
    return db.query(Team).filter(Team.status != TeamStatus.DISQUALIFIED).limit(R2_QUALIFIERS).all()


# ==============================================================================
# STARTING BALANCE BREAKDOWN & SYNC
# ==============================================================================
def calculate_team_starting_balance(db: Session, team_id: str) -> Dict[str, Any]:
    """
    Official Round 3 Starting Balance calculation for a qualified squad:
      Starting Balance = 1000 + R1 rank points + R2 Cabo score + (verified Secret Agent tasks * 50)
    CRITICAL: R2 Cabo score is used DIRECTLY (0 to 75 points raw). DO NOT multiply by 10.
    """
    base_balance = float(STARTING_WALLET_BALANCE)  # 1000.0

    # 1. R1 rank points (1st=16, 2nd=15 ... 16th=1, 17th+=0)
    r1_qual = (
        db.query(RoundQualification)
        .filter(RoundQualification.round_number == 1, RoundQualification.team_id == team_id)
        .first()
    )
    r1_rank = r1_qual.rank if r1_qual else None
    if r1_rank is None:
        from app.services.round1_service import get_round1_overview
        r1_overview = get_round1_overview(db)
        team_rec = next((r for r in r1_overview.get("records", []) if r.get("team_id") == team_id), None)
        if team_rec:
            r1_rank = team_rec.get("rank")

    r1_rank_points = float(R1_RANK_POINTS_MAP.get(r1_rank, 0)) if r1_rank else 0.0

    # 2. R2 Cabo score (0 to 75 points raw, NEVER multiplied by 10)
    scorecards = (
        db.query(CaboPlayerScorecard)
        .filter(CaboPlayerScorecard.team_id == team_id)
        .all()
    )
    r2_cabo_score = float(sum(sc.placement_points for sc in scorecards))

    # 3. Verified Secret Agent tasks (+50 per verified task)
    dossier = (
        db.query(SecretAgentDossier)
        .filter(SecretAgentDossier.team_id == team_id)
        .first()
    )
    verified_agent_tasks = 0
    if dossier:
        verified_agent_tasks = (
            db.query(SecretAgentTask)
            .filter(
                SecretAgentTask.dossier_id == dossier.id,
                SecretAgentTask.status == AgentTaskStatus.VERIFIED
            )
            .count()
        )
    agent_task_bonus = float(verified_agent_tasks * AGENT_TASK_REWARD)

    total_starting_balance = base_balance + r1_rank_points + r2_cabo_score + agent_task_bonus

    return {
        "team_id": team_id,
        "base_balance": base_balance,
        "r1_rank": r1_rank,
        "r1_rank_points": r1_rank_points,
        "r2_cabo_score": r2_cabo_score,
        "verified_agent_tasks": verified_agent_tasks,
        "agent_task_bonus": agent_task_bonus,
        "total_starting_balance": total_starting_balance,
    }


def sync_round3_starting_balances(db: Session, actor: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Synchronizes the official Starting Balance for all Round 3 participating squads.
    Ensures wallet ledger transactions reflect:
      - Canonical Base Balance (1000.0)
      - Round 1 Rank Points
      - Round 2 Cabo Score (raw score, not multiplied)
      - Verified Secret Agent tasks (+50 each)
    """
    teams = get_round3_eligible_teams(db)
    synced = []

    for team in teams:
        breakdown = calculate_team_starting_balance(db, team.id)
        wallet = wallet_service.get_or_create_wallet(db, team.id)

        # Check existing transaction types
        txs = db.query(WalletTransaction).filter(WalletTransaction.team_id == team.id).all()
        has_r1_tx = any(t.transaction_type == TransactionType.ROUND1_REWARD for t in txs)
        has_r2_tx = any(t.transaction_type == TransactionType.ROUND2_REWARD for t in txs)
        has_agent_tx = any(t.transaction_type == TransactionType.AGENT_TASK_REWARD for t in txs)

        now = datetime.now(timezone.utc)

        # Add R1 rank reward if not present and > 0
        if not has_r1_tx and breakdown["r1_rank_points"] > 0:
            bal_before = float(wallet.current_balance)
            bal_after = bal_before + breakdown["r1_rank_points"]
            wallet.current_balance = bal_after
            wallet.total_earned = float(wallet.total_earned) + breakdown["r1_rank_points"]
            tx_r1 = WalletTransaction(
                wallet_id=wallet.id,
                team_id=team.id,
                transaction_type=TransactionType.ROUND1_REWARD,
                amount=breakdown["r1_rank_points"],
                balance_before=bal_before,
                balance_after=bal_after,
                reference_type="ROUND_1",
                reference_id=f"r1-{team.id}",
                description=f"Round 1 Rank Points (Rank #{breakdown['r1_rank']}: +{breakdown['r1_rank_points']:.0f} pts)",
                created_by=actor or "system",
                created_at=now,
            )
            db.add(tx_r1)

        # Add R2 Cabo reward if not present and > 0
        if not has_r2_tx and breakdown["r2_cabo_score"] > 0:
            bal_before = float(wallet.current_balance)
            bal_after = bal_before + breakdown["r2_cabo_score"]
            wallet.current_balance = bal_after
            wallet.total_earned = float(wallet.total_earned) + breakdown["r2_cabo_score"]
            tx_r2 = WalletTransaction(
                wallet_id=wallet.id,
                team_id=team.id,
                transaction_type=TransactionType.ROUND2_REWARD,
                amount=breakdown["r2_cabo_score"],
                balance_before=bal_before,
                balance_after=bal_after,
                reference_type="ROUND_2",
                reference_id=f"r2-{team.id}",
                description=f"Round 2 Cabo Placement Points (+{breakdown['r2_cabo_score']:.0f} pts)",
                created_by=actor or "system",
                created_at=now,
            )
            db.add(tx_r2)

        # Add Agent task reward if not present and > 0
        if not has_agent_tx and breakdown["agent_task_bonus"] > 0:
            bal_before = float(wallet.current_balance)
            bal_after = bal_before + breakdown["agent_task_bonus"]
            wallet.current_balance = bal_after
            wallet.total_earned = float(wallet.total_earned) + breakdown["agent_task_bonus"]
            tx_ag = WalletTransaction(
                wallet_id=wallet.id,
                team_id=team.id,
                transaction_type=TransactionType.AGENT_TASK_REWARD,
                amount=breakdown["agent_task_bonus"],
                balance_before=bal_before,
                balance_after=bal_after,
                reference_type="AGENT_TASK",
                reference_id=f"agent-{team.id}",
                description=f"Secret Agent Tasks ({breakdown['verified_agent_tasks']} verified: +{breakdown['agent_task_bonus']:.0f} pts)",
                created_by=actor or "system",
                created_at=now,
            )
            db.add(tx_ag)

        synced.append(breakdown)

    db.commit()
    return synced


# ==============================================================================
# ASSET PURCHASES & TWO-ORGANIZER APPROVAL
# ==============================================================================
def purchase_market_asset(
    db: Session,
    team_id: str,
    asset_type: str,
    quantity: int = 1,
    price: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None,
    actor: Optional[str] = None,
) -> BlackMarketPurchase:
    """
    Safely initiates a Black Market asset purchase for a qualified squad.
    Enforces:
    - Team must be eligible and market open.
    - Prevents overdrafts: validates team wallet balance >= total_price.
    - TWO-ORGANIZER APPROVAL: Deductions require two distinct organizer approvals before
      the official wallet deduction takes effect.
    - If details provide dual organizer signatures at submission time, both are recorded
      and the purchase is approved and debited immediately.
    """
    if quantity < 1:
        raise InvalidAssetError("Purchase quantity must be at least 1.")

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise BlackMarketError(f"Team '{team_id}' not found.")

    cfg = get_or_create_r3_config(db)
    if cfg.is_finalized:
        raise MarketClosedError("Round 3 is finalized. Black Market is closed.")

    # Check eligibility if Round 2 finalized
    if is_round_finalized(db, 2):
        eligible = set(get_eligible_team_ids(db, 3))
        if eligible and team_id not in eligible:
            raise TeamNotEligibleError(f"Team '{team_id}' is not qualified for Round 3.")

    clean_asset = asset_type.upper().strip()

    # Map asset type enum
    try:
        mapped_asset_type = BlackMarketAssetType[clean_asset]
    except KeyError:
        mapped_asset_type = BlackMarketAssetType.CUSTOM

    # Determine unit price
    if price is not None:
        unit_price = float(price)
    else:
        suggested_key = clean_asset.lower()
        unit_price = BLACK_MARKET_SUGGESTED_PRICES.get(suggested_key, 200.0)

    total_price = unit_price * quantity

    # Verify wallet has sufficient funds to prevent overdraft
    wallet = wallet_service.get_or_create_wallet(db, team_id)
    if float(wallet.current_balance) < total_price:
        raise InsufficientFundsError(
            float(wallet.current_balance),
            total_price,
            f"Insufficient wallet balance ({wallet.current_balance:.1f} pts) for purchase of {total_price:.1f} pts."
        )

    purchase_ref = f"bmp-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    # Check for immediate dual approval in details
    second_org = details.get("second_organizer") or details.get("second_organizer_id") if details else None
    auto_dual_approved = bool(actor and second_org and actor != second_org)

    if auto_dual_approved:
        # Atomic wallet debit immediately
        tx = wallet_service.debit_black_market_purchase(
            db=db,
            team_id=team_id,
            amount=total_price,
            purchase_id=purchase_ref,
            asset_description=f"{clean_asset} (x{quantity})",
            created_by=second_org,
            notes=f"Dual approved by {actor} and {second_org}"
        )
        bmp = BlackMarketPurchase(
            id=purchase_ref,
            team_id=team_id,
            asset_type=mapped_asset_type,
            price=total_price,
            quantity=quantity,
            transaction_id=tx.id,
            status=PurchaseStatus.COMPLETED,
            approval_status="APPROVED",
            first_approved_by=actor,
            first_approved_at=now,
            second_approved_by=second_org,
            second_approved_at=now,
            details=details or {},
            purchased_by=actor,
            purchased_at=now,
            notes=f"Dual-approved purchase executed by {actor} & {second_org}"
        )
        # If code fragment or secret code item purchase, update fragment in code hunt record
        if mapped_asset_type in (BlackMarketAssetType.MISSING_CODE_FRAGMENT, BlackMarketAssetType.SECRET_CODE_ITEM_1, BlackMarketAssetType.SECRET_CODE_ITEM_2):
            frag_details = dict(details or {})
            if mapped_asset_type == BlackMarketAssetType.SECRET_CODE_ITEM_1:
                frag_details["fragment_number"] = 1
            elif mapped_asset_type == BlackMarketAssetType.SECRET_CODE_ITEM_2:
                frag_details["fragment_number"] = 2
            _apply_purchased_fragment(db, team_id, frag_details)
    else:
        # Created in PENDING_APPROVAL status: awaits two-organizer approval
        bmp = BlackMarketPurchase(
            id=purchase_ref,
            team_id=team_id,
            asset_type=mapped_asset_type,
            price=total_price,
            quantity=quantity,
            transaction_id=None,
            status=PurchaseStatus.PENDING,
            approval_status="PARTIALLY_APPROVED" if actor else "PENDING_APPROVAL",
            first_approved_by=actor,
            first_approved_at=now if actor else None,
            second_approved_by=None,
            second_approved_at=None,
            details=details or {},
            purchased_by=actor,
            purchased_at=now,
            notes="Awaiting second organizer approval signature" if actor else "Awaiting two organizer approval signatures"
        )

    db.add(bmp)
    log_audit_event(
        db=db,
        action="BLACK_MARKET_PURCHASE_INITIATED" if not auto_dual_approved else "BLACK_MARKET_PURCHASE_COMPLETED",
        entity_type="BlackMarketPurchase",
        entity_id=bmp.id,
        actor_id=actor or "system",
        actor_role="ORGANIZER",
        round_number=3,
        details={"team_id": team_id, "asset_type": clean_asset, "total_price": total_price, "approval_status": bmp.approval_status}
    )
    db.commit()
    db.refresh(bmp)
    return bmp


def approve_market_purchase(
    db: Session,
    purchase_id: str,
    actor: str,
    second_organizer_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> BlackMarketPurchase:
    """
    Two-organizer approval signature handler for Black Market deductions.
    - If 1st signature: records first_approved_by.
    - If 2nd signature: enforces distinct organizer from 1st approver.
    - Once both signatures are recorded: debits squad wallet and finalizes purchase.
    """
    bmp = db.query(BlackMarketPurchase).filter(BlackMarketPurchase.id == purchase_id).first()
    if not bmp:
        raise BlackMarketError(f"Purchase '{purchase_id}' not found.")

    if bmp.approval_status == "APPROVED":
        return bmp

    if bmp.approval_status == "REJECTED":
        raise BlackMarketError("Cannot approve a rejected purchase.")

    now = datetime.now(timezone.utc)

    # If second_organizer_id is supplied alongside actor in one call
    if second_organizer_id and second_organizer_id != actor:
        bmp.first_approved_by = actor
        bmp.first_approved_at = now
        bmp.second_approved_by = second_organizer_id
        bmp.second_approved_at = now
        bmp.approval_status = "APPROVED"
    elif not bmp.first_approved_by:
        # First signature
        bmp.first_approved_by = actor
        bmp.first_approved_at = now
        bmp.approval_status = "PARTIALLY_APPROVED"
        if notes:
            bmp.notes = (bmp.notes or "") + f" [1st Approval by {actor}: {notes}]"
        db.commit()
        db.refresh(bmp)
        return bmp
    else:
        # Second signature
        if bmp.first_approved_by == actor:
            raise BlackMarketError(
                f"Organizer '{actor}' has already approved this deduction. A distinct second organizer signature is required."
            )
        bmp.second_approved_by = actor
        bmp.second_approved_at = now
        bmp.approval_status = "APPROVED"
        if notes:
            bmp.notes = (bmp.notes or "") + f" [2nd Approval by {actor}: {notes}]"

    # Both signatures verified: execute wallet debit
    wallet = wallet_service.get_or_create_wallet(db, bmp.team_id)
    if float(wallet.current_balance) < bmp.price:
        raise InsufficientFundsError(
            float(wallet.current_balance),
            bmp.price,
            f"Insufficient wallet balance ({wallet.current_balance:.1f} pts) for approved purchase of {bmp.price:.1f} pts."
        )

    tx = wallet_service.debit_black_market_purchase(
        db=db,
        team_id=bmp.team_id,
        amount=bmp.price,
        purchase_id=bmp.id,
        asset_description=f"{bmp.asset_type.value} (x{bmp.quantity})",
        created_by=bmp.second_approved_by or actor,
        notes=f"Approved by {bmp.first_approved_by} and {bmp.second_approved_by}"
    )
    bmp.transaction_id = tx.id
    bmp.status = PurchaseStatus.COMPLETED

    # If code fragment or secret code item purchase, update fragment in code hunt record
    if bmp.asset_type in (BlackMarketAssetType.MISSING_CODE_FRAGMENT, BlackMarketAssetType.SECRET_CODE_ITEM_1, BlackMarketAssetType.SECRET_CODE_ITEM_2):
        frag_details = dict(bmp.details or {})
        if bmp.asset_type == BlackMarketAssetType.SECRET_CODE_ITEM_1:
            frag_details["fragment_number"] = 1
        elif bmp.asset_type == BlackMarketAssetType.SECRET_CODE_ITEM_2:
            frag_details["fragment_number"] = 2
        _apply_purchased_fragment(db, bmp.team_id, frag_details)

    log_audit_event(
        db=db,
        action="BLACK_MARKET_PURCHASE_APPROVED",
        entity_type="BlackMarketPurchase",
        entity_id=bmp.id,
        actor_id=actor,
        actor_role="ORGANIZER",
        round_number=3,
        details={
            "team_id": bmp.team_id,
            "total_price": bmp.price,
            "first_approved_by": bmp.first_approved_by,
            "second_approved_by": bmp.second_approved_by,
        }
    )

    db.commit()
    db.refresh(bmp)
    return bmp


def reject_market_purchase(
    db: Session,
    purchase_id: str,
    actor: str,
    rejection_reason: Optional[str] = None
) -> BlackMarketPurchase:
    """Rejects a pending Black Market purchase without deducting wallet points."""
    bmp = db.query(BlackMarketPurchase).filter(BlackMarketPurchase.id == purchase_id).first()
    if not bmp:
        raise BlackMarketError(f"Purchase '{purchase_id}' not found.")

    if bmp.approval_status == "APPROVED":
        raise BlackMarketError("Cannot reject an already approved and completed purchase.")

    bmp.approval_status = "REJECTED"
    bmp.status = PurchaseStatus.REFUNDED
    bmp.notes = (bmp.notes or "") + f" [Rejected by {actor}: {rejection_reason or 'No reason provided'}]"

    log_audit_event(
        db=db,
        action="BLACK_MARKET_PURCHASE_REJECTED",
        entity_type="BlackMarketPurchase",
        entity_id=bmp.id,
        actor_id=actor,
        actor_role="ORGANIZER",
        round_number=3,
        details={"team_id": bmp.team_id, "reason": rejection_reason}
    )

    db.commit()
    db.refresh(bmp)
    return bmp


def list_pending_purchases(db: Session) -> List[BlackMarketPurchase]:
    """Returns all purchases awaiting organizer approval signatures."""
    return (
        db.query(BlackMarketPurchase)
        .filter(BlackMarketPurchase.approval_status.in_(["PENDING_APPROVAL", "PARTIALLY_APPROVED"]))
        .order_by(BlackMarketPurchase.purchased_at.asc())
        .all()
    )


def _apply_purchased_fragment(db: Session, team_id: str, details: Optional[Dict[str, Any]]) -> None:
    """Marks a purchased code fragment as PURCHASED in the FinalCodeRecord."""
    frag_num = int(details.get("fragment_number") or details.get("fragmentNumber") or 1) if details else 1
    rec = db.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team_id).first()
    if not rec:
        rec = FinalCodeRecord(team_id=team_id)
        db.add(rec)
        db.flush()

    now = datetime.now(timezone.utc)
    rec_val = details.get("recovered_value") if details else None
    if frag_num == 1:
        rec.fragment_1_status = FragmentStatus.PURCHASED
        rec.fragment_1_value = rec_val or "ODD"
        rec.fragment_1_discovered_at = now
    elif frag_num == 2:
        rec.fragment_2_status = FragmentStatus.PURCHASED
        rec.fragment_2_value = rec_val or "42"
        rec.fragment_2_discovered_at = now
    elif frag_num == 3:
        rec.fragment_3_status = FragmentStatus.PURCHASED
        rec.fragment_3_value = rec_val or "ECHO"
        rec.fragment_3_discovered_at = now
        rec.echo_e_verified = True
        rec.echo_c_verified = True
        rec.echo_ho_verified = True
    elif frag_num == 4:
        rec.fragment_4_status = FragmentStatus.PURCHASED
        rec.fragment_4_value = rec_val or "PRIME"
        rec.fragment_4_discovered_at = now
        rec.prime_sequence_verified = True

    if rec.fragment_1_value and rec.fragment_2_value:
        rec.final_code_assembled = f"{rec.fragment_1_value}{rec.fragment_2_value}"

    # Check if all 4 fragments are now verified
    v1 = rec.fragment_1_status in (FragmentStatus.RECOVERED, FragmentStatus.PURCHASED)
    v2 = rec.fragment_2_status in (FragmentStatus.RECOVERED, FragmentStatus.PURCHASED)
    v3 = rec.fragment_3_status in (FragmentStatus.RECOVERED, FragmentStatus.PURCHASED)
    v4 = rec.fragment_4_status in (FragmentStatus.RECOVERED, FragmentStatus.PURCHASED)
    if v1 and v2 and v3 and v4:
        rec.final_code_verified = True
        rec.verified_at = now
        rec.verification_notes = "All 4 fragments verified (physical hunt + Cabo + Black Market recovery)"


def get_team_market_purchases(db: Session, team_id: str) -> List[BlackMarketPurchase]:
    """Returns all Black Market purchases for a squad."""
    return (
        db.query(BlackMarketPurchase)
        .filter(BlackMarketPurchase.team_id == team_id)
        .order_by(BlackMarketPurchase.purchased_at.desc())
        .all()
    )


# ==============================================================================
# SEALED-BID AUCTIONS
# ==============================================================================
def create_auction(
    db: Session,
    title: str,
    description: Optional[str] = None,
    item_type: str = "CUSTOM",
    starting_bid: float = 0.0,
    reserve_price: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None,
    created_by: Optional[str] = None,
) -> BlackMarketAuction:
    """Creates a new sealed-bid Black Market auction."""
    if starting_bid < 0:
        raise InvalidBidError("Starting bid cannot be negative.")
    if reserve_price is not None and reserve_price < 0:
        raise InvalidBidError("Reserve price cannot be negative.")

    auction = BlackMarketAuction(
        id=f"auc-{uuid.uuid4().hex[:8]}",
        title=title,
        description=description,
        item_type=item_type,
        starting_bid=float(starting_bid),
        reserve_price=float(reserve_price) if reserve_price is not None else None,
        status=AuctionStatus.OPEN,
        details=details or {},
        created_by=created_by,
    )
    db.add(auction)
    db.flush()

    log_audit_event(
        db=db,
        action="AUCTION_CREATED",
        entity_type="BlackMarketAuction",
        entity_id=auction.id,
        actor_id=created_by or "system",
        actor_role="ORGANIZER",
        round_number=3,
        details={"title": title, "starting_bid": starting_bid, "reserve_price": reserve_price}
    )

    db.commit()
    db.refresh(auction)
    return auction


def list_auctions(db: Session) -> List[BlackMarketAuction]:
    """Lists all auctions."""
    return db.query(BlackMarketAuction).order_by(BlackMarketAuction.created_at.desc()).all()


def get_auction(
    db: Session,
    auction_id: str,
    is_organizer: bool = False,
    viewing_team_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieves auction information with sealed-bid privacy enforcement.
    Squad callers CANNOT see other teams' bid amounts while the auction is OPEN.
    """
    auction = db.query(BlackMarketAuction).filter(BlackMarketAuction.id == auction_id).first()
    if not auction:
        raise AuctionNotFoundError(f"Auction '{auction_id}' not found.")

    bids_data = []
    for b in auction.bids:
        # Mask bid amount for non-organizers if not their own team
        is_own_team = viewing_team_id and (b.team_id == viewing_team_id)
        can_view_amount = is_organizer or is_own_team or auction.status == AuctionStatus.RESOLVED

        bids_data.append({
            "id": b.id,
            "auction_id": b.auction_id,
            "team_id": b.team_id,
            "bid_amount": b.bid_amount if can_view_amount else None,
            "status": b.status,
            "submitted_at": b.submitted_at,
            "notes": b.notes if is_organizer else None,
        })

    return {
        "id": auction.id,
        "title": auction.title,
        "description": auction.description,
        "item_type": auction.item_type,
        "starting_bid": auction.starting_bid,
        "reserve_price": auction.reserve_price if is_organizer else None,
        "status": auction.status,
        "winning_bid_id": auction.winning_bid_id,
        "winning_team_id": auction.winning_team_id,
        "winning_amount": auction.winning_amount,
        "details": auction.details,
        "created_at": auction.created_at,
        "closed_at": auction.closed_at,
        "resolved_at": auction.resolved_at,
        "created_by": auction.created_by,
        "total_bids": len(auction.bids),
        "bids": bids_data,
    }


def submit_bid(
    db: Session,
    auction_id: str,
    team_id: str,
    bid_amount: float,
    notes: Optional[str] = None,
) -> BlackMarketBid:
    """
    Submits a private sealed bid for an auction.
    Enforces:
    - Auction must be in OPEN status.
    - Squad wallet balance must be >= bid_amount (cannot bid more than current balance).
    - Bid amount must be >= starting_bid.
    - Replaces previous bid if team already bid on this auction.
    """
    auction = db.query(BlackMarketAuction).filter(BlackMarketAuction.id == auction_id).first()
    if not auction:
        raise AuctionNotFoundError(f"Auction '{auction_id}' not found.")

    if auction.status != AuctionStatus.OPEN:
        raise AuctionClosedError(f"Auction '{auction_id}' is not open (status: {auction.status.value}).")

    bid_amount = float(bid_amount)
    if bid_amount < auction.starting_bid:
        raise InvalidBidError(
            f"Bid amount {bid_amount:.1f} is below minimum starting bid {auction.starting_bid:.1f}."
        )

    # Validate team wallet balance
    wallet = wallet_service.get_or_create_wallet(db, team_id)
    if wallet.current_balance < bid_amount:
        raise InvalidBidError(
            f"Bid amount {bid_amount:.1f} exceeds current wallet balance {wallet.current_balance:.1f}."
        )

    # Check for existing bid by this team
    existing_bid = (
        db.query(BlackMarketBid)
        .filter(BlackMarketBid.auction_id == auction_id, BlackMarketBid.team_id == team_id)
        .first()
    )

    now = datetime.now(timezone.utc)
    if existing_bid:
        existing_bid.bid_amount = bid_amount
        existing_bid.status = BidStatus.SUBMITTED
        existing_bid.submitted_at = now
        existing_bid.notes = notes
        db.commit()
        db.refresh(existing_bid)
        return existing_bid

    new_bid = BlackMarketBid(
        id=f"bid-{uuid.uuid4().hex[:8]}",
        auction_id=auction_id,
        team_id=team_id,
        bid_amount=bid_amount,
        status=BidStatus.SUBMITTED,
        submitted_at=now,
        notes=notes,
    )
    db.add(new_bid)
    db.commit()
    db.refresh(new_bid)
    return new_bid


def resolve_auction(
    db: Session,
    auction_id: str,
    actor: Optional[str] = None,
    force_winner_bid_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Resolves a sealed-bid auction.
    - Determines the highest valid bid.
    - If highest bid is tied, marks auction as REQUIRES_REVIEW and flags organizer review.
    - If highest bid meets reserve price, debits winning squad's wallet via wallet_service.
    - Marks losing bids as LOST without deducting any points from losing squads.
    """
    auction = db.query(BlackMarketAuction).filter(BlackMarketAuction.id == auction_id).first()
    if not auction:
        raise AuctionNotFoundError(f"Auction '{auction_id}' not found.")

    if auction.status not in (AuctionStatus.OPEN, AuctionStatus.CLOSED, AuctionStatus.REQUIRES_REVIEW):
        raise AuctionClosedError(f"Auction '{auction_id}' is already {auction.status.value}.")

    bids = (
        db.query(BlackMarketBid)
        .filter(BlackMarketBid.auction_id == auction_id, BlackMarketBid.status == BidStatus.SUBMITTED)
        .order_by(desc(BlackMarketBid.bid_amount), BlackMarketBid.submitted_at.asc())
        .all()
    )

    now = datetime.now(timezone.utc)

    if not bids:
        auction.status = AuctionStatus.RESOLVED
        auction.resolved_at = now
        auction.notes = "Auction closed with 0 bids."
        db.commit()
        return {"success": True, "auction_id": auction.id, "status": "RESOLVED", "winner": None}

    # If organizer forced a specific winning bid
    if force_winner_bid_id:
        winner_bid = next((b for b in bids if b.id == force_winner_bid_id), None)
        if not winner_bid:
            raise InvalidBidError(f"Specified winning bid '{force_winner_bid_id}' not found among submitted bids.")
    else:
        # Check for tie at rank 1
        if len(bids) > 1 and bids[0].bid_amount == bids[1].bid_amount:
            auction.status = AuctionStatus.REQUIRES_REVIEW
            auction.notes = f"Tie detected between highest bids ({bids[0].bid_amount:.1f} pts). Organizer decision required."
            db.commit()
            return {
                "success": False,
                "requires_review": True,
                "auction_id": auction.id,
                "status": "REQUIRES_REVIEW",
                "tied_bids": [b.id for b in bids if b.bid_amount == bids[0].bid_amount],
                "message": "Tie detected for highest bid. Organizer review required."
            }
        winner_bid = bids[0]

    # Check reserve price
    if auction.reserve_price is not None and winner_bid.bid_amount < auction.reserve_price:
        auction.status = AuctionStatus.RESOLVED
        auction.resolved_at = now
        auction.notes = f"Reserve price of {auction.reserve_price:.1f} not met. Highest bid was {winner_bid.bid_amount:.1f}."
        for b in bids:
            b.status = BidStatus.LOST
        db.commit()
        return {
            "success": True,
            "auction_id": auction.id,
            "status": "RESOLVED",
            "winner": None,
            "message": "Reserve price not met. No winner."
        }

    # Debit winning squad
    tx = wallet_service.debit_black_market_purchase(
        db=db,
        team_id=winner_bid.team_id,
        amount=winner_bid.bid_amount,
        purchase_id=f"auc-win-{auction.id}",
        asset_description=f"Auction Win: {auction.title}",
        created_by=actor,
        notes=f"Winning sealed bid on auction '{auction.title}'"
    )

    # Update winning bid
    winner_bid.status = BidStatus.WON
    winner_bid.transaction_id = tx.id

    # Update losing bids (NO points debited)
    for b in bids:
        if b.id != winner_bid.id:
            b.status = BidStatus.LOST

    # Update auction record
    auction.status = AuctionStatus.RESOLVED
    auction.winning_bid_id = winner_bid.id
    auction.winning_team_id = winner_bid.team_id
    auction.winning_amount = winner_bid.bid_amount
    auction.resolved_at = now

    # Record purchase asset
    bmp = BlackMarketPurchase(
        team_id=winner_bid.team_id,
        asset_type=BlackMarketAssetType.CUSTOM,
        price=winner_bid.bid_amount,
        quantity=1,
        transaction_id=tx.id,
        status=PurchaseStatus.COMPLETED,
        details={"auction_id": auction.id, "auction_title": auction.title},
        purchased_by=actor
    )
    db.add(bmp)

    log_audit_event(
        db=db,
        action="AUCTION_RESOLVED",
        entity_type="BlackMarketAuction",
        entity_id=auction.id,
        actor_id=actor or "system",
        actor_role="ORGANIZER",
        round_number=3,
        details={
            "winning_team_id": winner_bid.team_id,
            "winning_amount": winner_bid.bid_amount,
            "winning_bid_id": winner_bid.id
        }
    )

    db.commit()
    db.refresh(auction)
    return {
        "success": True,
        "auction_id": auction.id,
        "status": "RESOLVED",
        "winner": {
            "team_id": winner_bid.team_id,
            "bid_amount": winner_bid.bid_amount,
            "bid_id": winner_bid.id,
            "transaction_id": tx.id
        }
    }


# ==============================================================================
# STANDINGS & FINAL CODE GATE ENGINE
# ==============================================================================
# ==============================================================================
# STANDINGS & FINAL CODE GATE ENGINE (TOP 6 ADVANCEMENT)
# ==============================================================================
def calculate_round3_standings(db: Session) -> Dict[str, Any]:
    """
    Official Round 3 Standings Calculation & Qualification Gate Engine.
    Rules:
    1. Input: Exactly 12 qualified squads from Round 2.
    2. Starting Balance:
       1000 + R1 rank points + R2 Cabo score (raw, NOT * 10) + (verified Secret Agent tasks * 50).
    3. 4-Fragment System & Missing Fragment Penalty:
       Fragments: R1 (ODD, 42) + R2 (ECHO, PRIME).
       Missing fragment penalty = -350 points each.
       Effective Balance = wallet balance - missing fragment penalties.
       ONLY teams with all 4 verified fragments are eligible to advance.
    4. Top 6 Cutoff & Tie Handling:
       Code-valid squads ranked descending by effective balance.
       Top 6 squads qualify for Round 4 (`R3_QUALIFIERS = 6`).
       If squads at 6th and 7th rank are tied on effective balance, flags cutoff_tie = True.
    5. Finalization Safeguards:
       All 12 teams present, market completed, approvals granted, agent tasks verified,
       4 fragments checked / -350 penalties applied, no 6th/7th cutoff tie.
    """
    teams = get_round3_eligible_teams(db)
    cfg = get_or_create_r3_config(db)

    # Gather data for each squad
    squad_data = []
    for team in teams:
        wallet = wallet_service.get_or_create_wallet(db, team.id)
        breakdown = calculate_team_starting_balance(db, team.id)
        code_rec = db.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team.id).first()

        f1_status = code_rec.fragment_1_status.value if code_rec else FragmentStatus.PENDING.value
        f2_status = code_rec.fragment_2_status.value if code_rec else FragmentStatus.PENDING.value
        f3_status = code_rec.fragment_3_status.value if code_rec else FragmentStatus.PENDING.value
        f4_status = code_rec.fragment_4_status.value if code_rec else FragmentStatus.PENDING.value

        v1 = f1_status in (FragmentStatus.RECOVERED.value, FragmentStatus.PURCHASED.value)
        v2 = f2_status in (FragmentStatus.RECOVERED.value, FragmentStatus.PURCHASED.value)
        v3 = f3_status in (FragmentStatus.RECOVERED.value, FragmentStatus.PURCHASED.value)
        v4 = f4_status in (FragmentStatus.RECOVERED.value, FragmentStatus.PURCHASED.value)

        verified_frag_count = sum([v1, v2, v3, v4])
        missing_frag_count = 4 - verified_frag_count
        missing_penalty = float(missing_frag_count * 350.0)
        has_all_4 = (missing_frag_count == 0)

        # Track ownership of the 4 Black Market items
        purchases = (
            db.query(BlackMarketPurchase)
            .filter(
                BlackMarketPurchase.team_id == team.id,
                BlackMarketPurchase.status == PurchaseStatus.COMPLETED
            )
            .all()
        )
        owned_asset_types = {p.asset_type.value if hasattr(p.asset_type, "value") else str(p.asset_type) for p in purchases}
        has_secret_code_1 = (
            "SECRET_CODE_ITEM_1" in owned_asset_types
            or f1_status in (FragmentStatus.RECOVERED.value, FragmentStatus.PURCHASED.value)
        )
        has_secret_code_2 = (
            "SECRET_CODE_ITEM_2" in owned_asset_types
            or f2_status in (FragmentStatus.RECOVERED.value, FragmentStatus.PURCHASED.value)
        )
        has_powerup_1 = "POWERUP_1_R4" in owned_asset_types or "EXTRA_PREP_TIME" in owned_asset_types
        has_powerup_2 = "POWERUP_2_R4" in owned_asset_types or "EXTRA_WITNESS_QUESTION" in owned_asset_types
        # Key is complete if both secret code items are owned, code is verified, or all 4 fragments recovered
        has_code_items = has_secret_code_1 and has_secret_code_2
        is_verified = (code_rec.final_code_verified if code_rec else False)
        # The three conditions are independent, as the comment above says and as
        # Section 6.2 requires ("buying the Final Code completes the Final Code
        # needed for Round 4"). They were not: has_all_4 IS missing_frag_count
        # == 0, and the other two clauses were each AND-ed with that same
        # condition, so the whole expression collapsed to missing_frag_count ==
        # 0 and the last two could never change the result. A squad that bought
        # both secret code items, and a squad an organiser had explicitly
        # verified, both still counted as having no code - which blocked Round 3
        # finalization with no working way to clear it.
        has_complete_key = has_all_4 or has_code_items or is_verified

        current_balance = float(wallet.current_balance)
        effective_balance = current_balance - missing_penalty

        squad_data.append({
            "team": team,
            "wallet": wallet,
            "breakdown": breakdown,
            "code_record": code_rec,
            "has_all_4_fragments": has_all_4 or has_complete_key,
            "has_secret_code_1": has_secret_code_1,
            "has_secret_code_2": has_secret_code_2,
            "has_powerup_1": has_powerup_1,
            "has_powerup_2": has_powerup_2,
            "has_complete_key": has_complete_key,
            "frag1_status": f1_status,
            "frag2_status": f2_status,
            "frag3_status": f3_status,
            "frag4_status": f4_status,
            "verified_fragment_count": verified_frag_count,
            "missing_fragment_count": missing_frag_count,
            "missing_fragment_penalty": missing_penalty,
            "current_balance": current_balance,
            "effective_balance": effective_balance,
            "total_spent": float(wallet.total_spent),
            "total_earned": float(wallet.total_earned),
            "total_penalties": float(wallet.total_penalties),
        })

    # Separate code-valid (complete key / all fragments) vs code-invalid
    code_valid_squads = [s for s in squad_data if s["has_complete_key"]]
    code_invalid_squads = [s for s in squad_data if not s["has_complete_key"]]

    # Sort code-valid squads:
    # 1) effective_balance DESC
    # 2) total_penalties ASC
    # 3) total_earned DESC
    code_valid_squads.sort(
        key=lambda s: (s["effective_balance"], -s["total_penalties"], s["total_earned"]),
        reverse=True
    )

    # Sort code-invalid squads similarly
    code_invalid_squads.sort(
        key=lambda s: (s["effective_balance"], -s["total_penalties"], s["total_earned"]),
        reverse=True
    )

    issues = []
    code_contingency = False
    cutoff_tie = False

    # Check 1: 12 teams present (or at least R2_QUALIFIERS)
    if len(teams) < R2_QUALIFIERS:
        issues.append(f"Field incomplete: Only {len(teams)} of {R2_QUALIFIERS} qualified squads present in Round 3.")

    # Check 2: Open auctions
    open_auctions = db.query(BlackMarketAuction).filter(BlackMarketAuction.status == AuctionStatus.OPEN).count()
    if open_auctions > 0:
        issues.append(f"Market active: {open_auctions} sealed-bid auction(s) are still OPEN.")

    # Check 3: Pending approvals
    pending_approvals = (
        db.query(BlackMarketPurchase)
        .filter(BlackMarketPurchase.approval_status.in_(["PENDING_APPROVAL", "PARTIALLY_APPROVED"]))
        .count()
    )
    if pending_approvals > 0:
        issues.append(f"Pending approvals: {pending_approvals} purchase(s) require two-organizer approval.")

    # Check 4: Unverified secret agent tasks
    pending_agent_tasks = (
        db.query(SecretAgentTask)
        .filter(SecretAgentTask.status == AgentTaskStatus.SUBMITTED)
        .count()
    )
    if pending_agent_tasks > 0:
        issues.append(f"Secret Agent tasks pending review: {pending_agent_tasks} submitted task(s) require organizer verification.")

    # Check 5: Code contingency (fewer than R3_QUALIFIERS squads have all verified fragments/complete key)
    if len(code_valid_squads) < R3_QUALIFIERS:
        code_contingency = True
        issues.append(
            f"Code Contingency: Only {len(code_valid_squads)} squads have verified qualification code (minimum {R3_QUALIFIERS} required). Missing fragments/code items must be recovered or purchased."
        )

    # Check 6: Cutoff tie at position R3_QUALIFIERS / R3_QUALIFIERS + 1 among code-valid squads
    if len(code_valid_squads) >= R3_QUALIFIERS + 1:
        s_cut = code_valid_squads[R3_QUALIFIERS - 1]
        s_next = code_valid_squads[R3_QUALIFIERS]
        if s_cut["effective_balance"] == s_next["effective_balance"]:
            cutoff_tie = True
            issues.append(
                f"Cutoff Tie: Squads '{s_cut['team'].name}' and '{s_next['team'].name}' are tied at rank {R3_QUALIFIERS}/{R3_QUALIFIERS + 1} with {s_cut['effective_balance']:.1f} pts. Organizer tie review required."
            )

    standings = []
    advancing_team_ids = []

    # Assign ranks to code-valid squads
    current_rank = 1
    for idx, s in enumerate(code_valid_squads):
        rank = idx + 1
        is_adv = (rank <= R3_QUALIFIERS) and not cutoff_tie and not code_contingency

        is_tied_at_cutoff = False
        if cutoff_tie and rank in (R3_QUALIFIERS, R3_QUALIFIERS + 1):
            is_tied_at_cutoff = True

        if is_adv:
            advancing_team_ids.append(s["team"].id)

        standings.append({
            "team_id": s["team"].id,
            "team_number": s["team"].team_number,
            "team_name": s["team"].name,
            "current_balance": s["current_balance"],
            "total_spent": s["total_spent"],
            "starting_balance": s["breakdown"]["total_starting_balance"],
            "base_balance": s["breakdown"]["base_balance"],
            "r1_rank_points": s["breakdown"]["r1_rank_points"],
            "r2_cabo_score": s["breakdown"]["r2_cabo_score"],
            "agent_task_bonus": s["breakdown"]["agent_task_bonus"],
            "has_secret_code_1": s["has_secret_code_1"],
            "has_secret_code_2": s["has_secret_code_2"],
            "has_powerup_1": s["has_powerup_1"],
            "has_powerup_2": s["has_powerup_2"],
            "has_complete_key": s["has_complete_key"],
            "final_code_verified": s["has_complete_key"],
            "fragment_1_status": s["frag1_status"],
            "fragment_2_status": s["frag2_status"],
            "fragment_3_status": s["frag3_status"],
            "fragment_4_status": s["frag4_status"],
            "verified_fragment_count": s["verified_fragment_count"],
            "missing_fragment_count": s["missing_fragment_count"],
            "missing_fragment_penalty": s["missing_fragment_penalty"],
            "effective_balance": s["effective_balance"],
            "rank": rank,
            "is_advancing": is_adv,
            "elimination_reason": None if is_adv else (f"Below Top {R3_QUALIFIERS} qualifying cutoff" if rank > R3_QUALIFIERS else None),
            "is_tied_cutoff": is_tied_at_cutoff,
        })
        current_rank = rank + 1

    # Assign ranks to code-invalid squads
    for s in code_invalid_squads:
        standings.append({
            "team_id": s["team"].id,
            "team_number": s["team"].team_number,
            "team_name": s["team"].name,
            "current_balance": s["current_balance"],
            "total_spent": s["total_spent"],
            "starting_balance": s["breakdown"]["total_starting_balance"],
            "base_balance": s["breakdown"]["base_balance"],
            "r1_rank_points": s["breakdown"]["r1_rank_points"],
            "r2_cabo_score": s["breakdown"]["r2_cabo_score"],
            "agent_task_bonus": s["breakdown"]["agent_task_bonus"],
            "has_secret_code_1": s["has_secret_code_1"],
            "has_secret_code_2": s["has_secret_code_2"],
            "has_powerup_1": s["has_powerup_1"],
            "has_powerup_2": s["has_powerup_2"],
            "has_complete_key": s["has_complete_key"],
            "final_code_verified": False,
            "fragment_1_status": s["frag1_status"],
            "fragment_2_status": s["frag2_status"],
            "fragment_3_status": s["frag3_status"],
            "fragment_4_status": s["frag4_status"],
            "verified_fragment_count": s["verified_fragment_count"],
            "missing_fragment_count": s["missing_fragment_count"],
            "missing_fragment_penalty": s["missing_fragment_penalty"],
            "effective_balance": s["effective_balance"],
            "rank": current_rank,
            "is_advancing": False,
            "elimination_reason": f"Missing qualification key or code fragments. Complete key required to advance.",
            "is_tied_cutoff": False,
        })
        current_rank += 1

    can_finalize = (
        len(teams) >= R3_QUALIFIERS
        and open_auctions == 0
        and pending_approvals == 0
        and pending_agent_tasks == 0
        and len(code_valid_squads) >= R3_QUALIFIERS
        and not cutoff_tie
        and len(advancing_team_ids) == R3_QUALIFIERS
    )

    return {
        "standings": standings,
        "can_finalize": can_finalize,
        "code_contingency": code_contingency,
        "cutoff_tie": cutoff_tie,
        "issues": issues,
        "advancing_team_ids": advancing_team_ids,
        "code_valid_count": len(code_valid_squads),
        "code_invalid_count": len(code_invalid_squads),
    }


# ==============================================================================
# ROUND 3 FINALIZATION (TOP 6 TO ROUND 4)
# ==============================================================================
def finalize_round3(
    db: Session,
    actor: Any,
    override_discrepancy: bool = False,
    force_advancing_team_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Officially seals Round 3 and qualifies TOP 6 squads for Round 4: The Legal Battle.
    - Validates 4-fragment gate & Top 6 rankings.
    - Creates RoundQualification records with score_snapshot = effective_balance.
    - PRESERVES TeamWallet.current_balance for Grand Finale carryover (NO wallet reset).
    - Sets RoundState(id=3) finalized and RoundState(id=4) active.
    """
    cfg = get_or_create_r3_config(db)

    # Idempotent return if already finalized
    if cfg.is_finalized:
        eligible = get_eligible_team_ids(db, 4)
        return {
            "success": True,
            "is_finalized": True,
            "finalized_at": cfg.finalized_at.isoformat() if cfg.finalized_at else datetime.now(timezone.utc).isoformat(),
            "finalized_by": cfg.finalized_by or str(getattr(actor, "id", actor)),
            "qualified_teams_count": len(eligible),
            "qualified_team_ids": eligible,
            "advancing_team_ids": eligible,
            "message": "Round 3 is already finalized."
        }

    # Verify Round 2 is finalized unless overridden
    if not is_round_finalized(db, 2) and not override_discrepancy:
        raise RoundFinalizationError("Cannot finalize Round 3: Round 2 is not finalized yet.")

    standings_calc = calculate_round3_standings(db)

    if not standings_calc["can_finalize"] and not override_discrepancy and not force_advancing_team_ids:
        raise RoundFinalizationError(
            f"Round 3 finalization blocked by validation safeguards: {'; '.join(standings_calc['issues'])}"
        )

    if force_advancing_team_ids:
        advancing_ids = list(force_advancing_team_ids)
    elif standings_calc["advancing_team_ids"]:
        advancing_ids = list(standings_calc["advancing_team_ids"])
    else:
        advancing_ids = [s["team_id"] for s in standings_calc["standings"][:R3_QUALIFIERS]]

    now = datetime.now(timezone.utc)
    actor_id = getattr(actor, "id", str(actor))

    # Record advancement in RoundQualification for all standings
    record_round_finalization(
        db=db,
        round_number=3,
        records=standings_calc["standings"],
        advancing_team_ids=advancing_ids,
        finalized_by=actor_id
    )

    # Update Team models
    for s in standings_calc["standings"]:
        team = db.query(Team).filter(Team.id == s["team_id"]).first()
        if team:
            if s["team_id"] in advancing_ids:
                team.current_round = 4
                team.is_qualified_for_next_round = True
            else:
                team.status = TeamStatus.ELIMINATED
                team.is_qualified_for_next_round = False

    # Mark BlackMarketConfigModel finalized
    cfg.is_finalized = True
    cfg.finalized_at = now
    cfg.finalized_by = actor_id

    # Update RoundState(id=3) and RoundState(id=4)
    from app.services.round_service import ensure_round_states_initialized
    ensure_round_states_initialized(db)

    rs3 = db.query(RoundState).filter(RoundState.id == 3).first()
    if rs3:
        rs3.is_finalized = True
        rs3.status = "Completed"
        rs3.finalized_at = now
        rs3.finalized_by = actor_id

    rs4 = db.query(RoundState).filter(RoundState.id == 4).first()
    if rs4:
        rs4.status = "Active"

    log_audit_event(
        db=db,
        action="ROUND_3_FINALIZED",
        entity_type="BlackMarketConfig",
        entity_id="1",
        actor_id=actor_id,
        actor_role="ORGANIZER",
        round_number=3,
        details={"advancing_team_ids": advancing_ids, "count": len(advancing_ids)}
    )

    db.commit()

    return {
        "success": True,
        "is_finalized": True,
        "finalized_at": now.isoformat(),
        "finalized_by": actor_id,
        "qualified_teams_count": len(advancing_ids),
        "qualified_team_ids": advancing_ids,
        "advancing_team_ids": advancing_ids,
        "message": f"Round 3 successfully finalized. {len(advancing_ids)} squads advance to Round 4: The Legal Battle."
    }


# ==============================================================================
# BINARY CODE CHECKER & SQUAD INVENTORY (PLAYER VIEW)
# ==============================================================================
def check_decoded_key(db: Session, team_id: str, code_input: str) -> Dict[str, Any]:
    """
    Binary Code Checker for squads entering decoded keys.
    Returns strictly:
      {'valid': True, 'message': 'Valid Key'}
    or
      {'valid': False, 'message': 'Invalid Key'}
    Never leaks expected values, intermediate hints, or error forensics.
    """
    if not code_input or not str(code_input).strip():
        return {"valid": False, "message": "Invalid Key"}

    clean_code = str(code_input).strip().upper()

    # 1. Check if matches assemble_final_code or team code record
    expected = code_hunt_service.assemble_final_code(db, team_id)
    if expected and clean_code == expected.upper():
        # Mark verified if not already verified
        rec = db.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team_id).first()
        if rec and not rec.final_code_verified:
            rec.final_code_verified = True
            rec.verified_at = datetime.now(timezone.utc)
            rec.verified_by = "Code-Checker-Self"
            rec.verification_notes = "Verified via decoded key check"
            db.commit()
        return {"valid": True, "message": "Valid Key"}

    # 2. Check canonical tournament code fragments (e.g. ODD42, ECHO, PRIME combinations)
    valid_keys = {"ODD42", "42ODD", "ECHOPRIME", "ODD42ECHOPRIME", "PRIME42"}
    rec = db.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team_id).first()
    if rec:
        f1 = (rec.fragment_1_value or "").strip().upper()
        f2 = (rec.fragment_2_value or "").strip().upper()
        f3 = (rec.fragment_3_value or "").strip().upper()
        f4 = (rec.fragment_4_value or "").strip().upper()
        if f1 and f2:
            valid_keys.add(f"{f1}{f2}")
        if f3 and f4:
            valid_keys.add(f"{f3}{f4}")
        if f1 and f2 and f3 and f4:
            valid_keys.add(f"{f1}{f2}{f3}{f4}")

    if clean_code in valid_keys:
        if rec and not rec.final_code_verified:
            rec.final_code_verified = True
            rec.verified_at = datetime.now(timezone.utc)
            rec.verified_by = "Code-Checker-Self"
            rec.verification_notes = "Verified via decoded key check"
            db.commit()
        return {"valid": True, "message": "Valid Key"}

    return {"valid": False, "message": "Invalid Key"}


def get_team_inventory_status(db: Session, team_id: str) -> Dict[str, Any]:
    """
    Returns private squad view (Team Status) in Round 3:
    - Current wallet balance
    - Starting balance breakdown
    - Owned Secret Code items (Item 1, Item 2)
    - Owned Powerups for Round 4 (Powerup 1, Powerup 2)
    - Complete key status (Yes/No)
    - Full transaction/purchase history for this squad only
    """
    wallet = wallet_service.get_or_create_wallet(db, team_id)
    breakdown = calculate_team_starting_balance(db, team_id)
    purchases = get_team_market_purchases(db, team_id)
    code_rec = db.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team_id).first()

    owned_types = {p.asset_type.value if hasattr(p.asset_type, "value") else str(p.asset_type) for p in purchases if p.status == PurchaseStatus.COMPLETED}

    f1_rec = code_rec and code_rec.fragment_1_status in (FragmentStatus.RECOVERED, FragmentStatus.PURCHASED)
    f2_rec = code_rec and code_rec.fragment_2_status in (FragmentStatus.RECOVERED, FragmentStatus.PURCHASED)

    has_code_item_1 = "SECRET_CODE_ITEM_1" in owned_types or bool(f1_rec)
    has_code_item_2 = "SECRET_CODE_ITEM_2" in owned_types or bool(f2_rec)
    has_powerup_1 = "POWERUP_1_R4" in owned_types or "EXTRA_PREP_TIME" in owned_types
    has_powerup_2 = "POWERUP_2_R4" in owned_types or "EXTRA_WITNESS_QUESTION" in owned_types
    is_key_complete = (has_code_item_1 and has_code_item_2) or (code_rec.final_code_verified if code_rec else False)

    return {
        "team_id": team_id,
        "current_balance": float(wallet.current_balance),
        "total_spent": float(wallet.total_spent),
        "total_earned": float(wallet.total_earned),
        "starting_balance_breakdown": breakdown,
        "items_owned": {
            "secret_code_item_1": has_code_item_1,
            "secret_code_item_2": has_code_item_2,
            "powerup_1_r4": has_powerup_1,
            "powerup_2_r4": has_powerup_2,
        },
        "has_complete_key": is_key_complete,
        "is_code_verified": code_rec.final_code_verified if code_rec else False,
        "purchases": [
            {
                "id": p.id,
                "asset_type": p.asset_type.value if hasattr(p.asset_type, "value") else str(p.asset_type),
                "price": float(p.price),
                "quantity": p.quantity,
                "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                "approval_status": p.approval_status,
                "purchased_at": p.purchased_at.isoformat() if p.purchased_at else None,
            }
            for p in purchases
        ],
    }