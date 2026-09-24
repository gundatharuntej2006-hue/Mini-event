"""
Round 3 â€” The Black Market & Qualification Engine Service for EVENT HQ.
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Manages:
- Configurable Black Market Catalog with suggested default prices
- Direct tactical asset purchases & missing code fragment recovery
- Sealed-bid auction creation, private bidding, and organizer resolution
- Mandatory Final Code qualification gate (checked FIRST before ranking)
- Code-less contingency evaluation (if >4 squads lack verified final code)
- Top 8 advancement engine based on remaining wallet balances
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
from app.models.wallet import TeamWallet, TransactionType
from app.models.code_hunt import FinalCodeRecord, FragmentStatus
from app.services.code_hunt_service import MissingFragmentPurchaseError
from app.models.round3 import BlackMarketConfigModel, default_hidden_code_config
from app.models.round_models import RoundState
from app.models.progression import RoundQualification, TieReview
from app.core.constants import (
    BLACK_MARKET_SUGGESTED_PRICES,
    BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED,
    BLACK_MARKET_PREP_PRICE_SUGGESTED,
    BLACK_MARKET_WITNESS_PRICE_SUGGESTED,
    BLACK_MARKET_AGENT_INTEL_PRICE_SUGGESTED,
    R3_QUALIFIERS,
    R2_QUALIFIERS,
)
from app.services import wallet as wallet_service
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
        "asset_type": "MISSING_CODE_FRAGMENT",
        "name": "Missing Code Fragment Recovery",
        "description": "Recovers 1 missing physical QR code fragment (Fragment 1 or Fragment 2) required for the Final Code gate.",
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
# ASSET PURCHASES
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
    Safely executes a Black Market asset purchase for a qualified squad.
    - If asset_type is MISSING_CODE_FRAGMENT: automatically invokes code_hunt_service.recover_missing_fragment.
    - For other assets: debits points via wallet_service.debit_black_market_purchase, logs purchase, maintains audit trail.
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

    # Route Missing Fragment Recovery to dedicated Code Hunt service
    if clean_asset in ("MISSING_CODE_FRAGMENT", "CODE_FRAGMENT", "FRAGMENT"):
        # Default to whichever fragment the team is actually missing, rather
        # than always fragment 1.
        #
        # Section 6.2 prices this item "400 each", so a team missing both is
        # meant to buy both. Hardcoding 1 meant the second purchase was refused
        # with "Fragment 1 is already owned", the team stayed one fragment
        # short, and the Round 4 gate never opened - so the documented recovery
        # route could not actually recover anyone who had found nothing.
        #
        # Found by scripts/rehearsal.py: buy twice, gate stays False -> False.
        # An explicit fragment_number in details still wins, for an organiser
        # who needs to name one.
        frag_num = None
        if details:
            raw = details.get("fragment_number") or details.get("fragmentNumber")
            frag_num = int(raw) if raw else None

        if frag_num is None:
            record = code_hunt_service.get_or_create_final_code_record(db, team_id)
            owned = (FragmentStatus.RECOVERED, FragmentStatus.PURCHASED)
            if record.fragment_1_status not in owned:
                frag_num = 1
            elif record.fragment_2_status not in owned:
                frag_num = 2
            else:
                raise MissingFragmentPurchaseError(
                    f"Team '{team_id}' already holds both code fragments."
                )

        # Recover fragment (handles wallet debit internally)
        code_hunt_service.recover_missing_fragment(
            db=db,
            team_id=team_id,
            fragment_number=frag_num,
            price=price,
            actor=actor,
            recovered_value=details.get("recovered_value") if details else None
        )

        # Retrieve the created purchase record
        bmp = (
            db.query(BlackMarketPurchase)
            .filter(
                BlackMarketPurchase.team_id == team_id,
                BlackMarketPurchase.asset_type == BlackMarketAssetType.MISSING_CODE_FRAGMENT
            )
            .order_by(BlackMarketPurchase.purchased_at.desc())
            .first()
        )
        return bmp

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
    purchase_ref = f"bmp-{uuid.uuid4().hex[:8]}"

    # Execute atomic wallet debit
    tx = wallet_service.debit_black_market_purchase(
        db=db,
        team_id=team_id,
        amount=total_price,
        purchase_id=purchase_ref,
        asset_description=f"{clean_asset} (x{quantity})",
        created_by=actor,
        notes=f"Purchased {quantity}x {clean_asset} at {unit_price:.1f} pts/unit"
    )

    # Record purchase ledger
    bmp = BlackMarketPurchase(
        id=purchase_ref,
        team_id=team_id,
        asset_type=mapped_asset_type,
        price=total_price,
        quantity=quantity,
        transaction_id=tx.id,
        status=PurchaseStatus.COMPLETED,
        details=details or {},
        purchased_by=actor
    )
    db.add(bmp)

    log_audit_event(
        db=db,
        action="BLACK_MARKET_PURCHASE_COMPLETED",
        entity_type="BlackMarketPurchase",
        entity_id=bmp.id,
        actor_id=actor or "system",
        actor_role="ORGANIZER",
        round_number=3,
        details={"team_id": team_id, "asset_type": clean_asset, "total_price": total_price, "quantity": quantity}
    )

    db.commit()
    db.refresh(bmp)
    return bmp


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
def calculate_round3_standings(db: Session) -> Dict[str, Any]:
    """
    Official Round 3 Standings Calculation & Qualification Gate Engine.
    Rules:
    1. Mandatory Final Code Qualification Gate checked FIRST.
       - Squads without a verified Final Code are marked CODE INVALID and ELIMINATED.
    2. Code-less Contingency:
       - If fewer than 8 squads have verified Final Codes (>4 invalid), flags code_contingency = True.
    3. Ranking:
       - Code-valid squads ranked descending by remaining wallet balance.
       - Secondary tie-breakers: fewer penalties (ASC), higher total earned (DESC).
    4. Top 8 Cutoff Ties:
       - If squads at 8th and 9th rank are tied on balance, flags cutoff_tie = True.
    5. Advancement:
       - Top 8 code-valid squads marked is_advancing = True.
    """
    teams = get_round3_eligible_teams(db)
    cfg = get_or_create_r3_config(db)

    # Gather data for each squad
    squad_data = []
    for team in teams:
        wallet = wallet_service.get_or_create_wallet(db, team.id)
        code_rec = db.query(FinalCodeRecord).filter(FinalCodeRecord.team_id == team.id).first()

        is_verified = bool(code_rec and code_rec.final_code_verified)
        frag1_status = code_rec.fragment_1_status.value if code_rec else FragmentStatus.PENDING.value
        frag2_status = code_rec.fragment_2_status.value if code_rec else FragmentStatus.PENDING.value

        squad_data.append({
            "team": team,
            "wallet": wallet,
            "code_record": code_rec,
            "is_code_verified": is_verified,
            "frag1_status": frag1_status,
            "frag2_status": frag2_status,
            "current_balance": float(wallet.current_balance),
            "total_spent": float(wallet.total_spent),
            "total_earned": float(wallet.total_earned),
            "total_penalties": float(wallet.total_penalties),
        })

    # Separate code-valid vs code-invalid
    code_valid_squads = [s for s in squad_data if s["is_code_verified"]]
    code_invalid_squads = [s for s in squad_data if not s["is_code_verified"]]

    # Sort code-valid squads:
    # 1) current_balance DESC
    # 2) total_penalties ASC
    # 3) total_earned DESC
    code_valid_squads.sort(
        key=lambda s: (s["current_balance"], -s["total_penalties"], s["total_earned"]),
        reverse=True
    )

    # Sort code-invalid squads similarly
    code_invalid_squads.sort(
        key=lambda s: (s["current_balance"], -s["total_penalties"], s["total_earned"]),
        reverse=True
    )

    issues = []
    code_contingency = False
    cutoff_tie = False

    # Check code-less contingency
    if len(code_valid_squads) < R3_QUALIFIERS:
        code_contingency = True
        issues.append(
            f"Code Contingency: Only {len(code_valid_squads)} squads have verified Final Codes (fewer than {R3_QUALIFIERS} required). Organizer intervention required."
        )

    # Check cutoff tie at position 8/9 among code-valid squads
    if len(code_valid_squads) >= 9:
        s8 = code_valid_squads[7]
        s9 = code_valid_squads[8]
        if s8["current_balance"] == s9["current_balance"]:
            cutoff_tie = True
            issues.append(
                f"Cutoff Tie: Teams '{s8['team'].name}' and '{s9['team'].name}' are tied at rank 8/9 with {s8['current_balance']:.1f} pts. Organizer review required."
            )

    standings = []
    advancing_team_ids = []

    # Assign ranks to code-valid squads
    current_rank = 1
    for idx, s in enumerate(code_valid_squads):
        rank = idx + 1
        is_adv = (rank <= R3_QUALIFIERS) and not cutoff_tie and not code_contingency

        is_tied_at_cutoff = False
        if cutoff_tie and rank in (8, 9):
            is_tied_at_cutoff = True

        if is_adv:
            advancing_team_ids.append(s["team"].id)

        standings.append({
            "team_id": s["team"].id,
            "team_number": s["team"].team_number,
            "team_name": s["team"].name,
            "current_balance": s["current_balance"],
            "total_spent": s["total_spent"],
            "final_code_verified": True,
            "fragment_1_status": s["frag1_status"],
            "fragment_2_status": s["frag2_status"],
            "rank": rank,
            "is_advancing": is_adv,
            "elimination_reason": None if is_adv else ("Cutoff by wallet points balance" if rank > R3_QUALIFIERS else None),
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
            "final_code_verified": False,
            "fragment_1_status": s["frag1_status"],
            "fragment_2_status": s["frag2_status"],
            "rank": current_rank,
            "is_advancing": False,
            "elimination_reason": "Final Code not verified (mandatory gate)",
            "is_tied_cutoff": False,
        })
        current_rank += 1

    can_finalize = (len(code_valid_squads) >= R3_QUALIFIERS) and not cutoff_tie and (len(advancing_team_ids) == R3_QUALIFIERS)

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
# ROUND 3 FINALIZATION
# ==============================================================================
def finalize_round3(
    db: Session,
    actor: Any,
    override_discrepancy: bool = False,
    force_advancing_team_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Officially seals Round 3 and qualifies 8 squads for Round 4.
    - Validates Final Code gate & top 8 rankings.
    - Creates RoundQualification records with score_snapshot = current_balance.
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
        # Fallback under override: top 8 by balance
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