from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.common import ApiResponse, FinalizationResponse
from app.schemas.rounds.round3 import (
    Round3OverviewResponse, BlackMarketConfigSchema, UpdateBlackMarketConfigInput,
    CreateTransactionInput, ReverseTransactionInput, AddFragmentInput, VerifyCodeInput,
    TransactionResponse, LedgerResponse, TeamCodeRecordResponse, TeamRound3RecordResponse
)
from app.schemas.tournament_extensions import (
    BlackMarketCatalogResponse,
    BlackMarketCatalogItem,
    BlackMarketAssetPurchaseRequest,
    BlackMarketPurchaseResponse,
    BlackMarketAuctionCreateRequest,
    BlackMarketAuctionResponse,
    BlackMarketBidCreateRequest,
    BlackMarketBidResponse,
    Round3StandingsResponse,
    Round3FinalizationResponse,
)
from app.services import round3_service
from app.services import black_market_service
from app.services.black_market_service import (
    BlackMarketError, MarketClosedError, TeamNotEligibleError,
    InvalidAssetError, AuctionNotFoundError, AuctionClosedError,
    InvalidBidError, FinalCodeGateError, RoundFinalizationError
)

router = APIRouter(prefix="/rounds/3", tags=["Round 3 — The Black Market"])


# ==============================================================================
# 1. CATALOG & ASSET PURCHASES
# ==============================================================================
@router.get("/catalog", response_model=ApiResponse[BlackMarketCatalogResponse])
@router.get("/market/catalog", response_model=ApiResponse[BlackMarketCatalogResponse])
def get_catalog(db: Session = Depends(get_db)):
    """Get complete Black Market catalog with suggested asset prices."""
    items = black_market_service.get_market_catalog(db)
    cfg = black_market_service.get_or_create_r3_config(db)
    res = BlackMarketCatalogResponse(
        catalog=[BlackMarketCatalogItem(**item) for item in items],
        round3_active=not cfg.is_finalized,
        total_items=len(items)
    )
    return ApiResponse(data=res, message="Black Market catalog loaded successfully")


@router.post("/purchase", response_model=ApiResponse[BlackMarketPurchaseResponse])
@router.post("/market/purchase", response_model=ApiResponse[BlackMarketPurchaseResponse])
def purchase_asset_api(
    payload: BlackMarketAssetPurchaseRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user)
):
    """
    Purchase a Black Market asset (missing code fragment, prep time, intel, etc.).
    Debits team tournament wallet atomically and maintains audit trail.
    """
    try:
        bmp = black_market_service.purchase_market_asset(
            db=db,
            team_id=payload.team_id,
            asset_type=payload.asset_type,
            quantity=payload.quantity,
            price=payload.price,
            details=payload.details,
            actor=actor.id
        )
        return ApiResponse(data=bmp, message="Black Market asset purchase completed successfully")
    except (MarketClosedError, TeamNotEligibleError, InvalidAssetError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        if "Insufficient funds" in str(e):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/purchases/{team_id}", response_model=ApiResponse[List[BlackMarketPurchaseResponse]])
@router.get("/market/purchases/{team_id}", response_model=ApiResponse[List[BlackMarketPurchaseResponse]])
def get_team_purchases(team_id: str, db: Session = Depends(get_db)):
    """Get all Black Market purchases for a specific squad."""
    purchases = black_market_service.get_team_market_purchases(db, team_id)
    return ApiResponse(data=purchases, message=f"Purchases for team '{team_id}' retrieved")


# ==============================================================================
# 2. SEALED-BID AUCTIONS
# ==============================================================================
@router.post("/auction", response_model=ApiResponse[BlackMarketAuctionResponse])
@router.post("/market/auction", response_model=ApiResponse[BlackMarketAuctionResponse])
def create_auction_api(
    payload: BlackMarketAuctionCreateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Create a new sealed-bid auction (Organizers only)."""
    try:
        auction = black_market_service.create_auction(
            db=db,
            title=payload.title,
            description=payload.description,
            item_type=payload.item_type,
            starting_bid=payload.starting_bid,
            reserve_price=payload.reserve_price,
            details=payload.details,
            created_by=actor.id
        )
        data = black_market_service.get_auction(db, auction.id, is_organizer=True)
        return ApiResponse(data=data, message="Auction created successfully")
    except InvalidBidError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/auctions", response_model=ApiResponse[List[BlackMarketAuctionResponse]])
@router.get("/market/auctions", response_model=ApiResponse[List[BlackMarketAuctionResponse]])
def list_auctions_api(
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user)
):
    """List all Black Market auctions."""
    is_organizer = actor.role.value in ("ORGANIZER", "ADMIN") if hasattr(actor.role, "value") else str(actor.role).upper() in ("ORGANIZER", "ADMIN")
    auctions = black_market_service.list_auctions(db)
    res = [
        black_market_service.get_auction(
            db,
            a.id,
            is_organizer=is_organizer,
            viewing_team_id=getattr(actor, "team_id", None)
        )
        for a in auctions
    ]
    return ApiResponse(data=res, message="Auctions retrieved")


@router.get("/auction/{auction_id}", response_model=ApiResponse[BlackMarketAuctionResponse])
@router.get("/market/auction/{auction_id}", response_model=ApiResponse[BlackMarketAuctionResponse])
def get_auction_api(
    auction_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user)
):
    """Get auction details. Bid amounts from other teams are masked for squads."""
    is_organizer = actor.role.value in ("ORGANIZER", "ADMIN") if hasattr(actor.role, "value") else str(actor.role).upper() in ("ORGANIZER", "ADMIN")
    try:
        data = black_market_service.get_auction(
            db=db,
            auction_id=auction_id,
            is_organizer=is_organizer,
            viewing_team_id=getattr(actor, "team_id", None)
        )
        return ApiResponse(data=data, message="Auction retrieved")
    except AuctionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/auction/{auction_id}/bid", response_model=ApiResponse[BlackMarketBidResponse])
@router.post("/market/auction/{auction_id}/bid", response_model=ApiResponse[BlackMarketBidResponse])
def submit_bid_api(
    auction_id: str,
    payload: BlackMarketBidCreateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user)
):
    """Submit a private sealed bid for an auction. Cannot exceed current wallet balance."""
    try:
        bid = black_market_service.submit_bid(
            db=db,
            auction_id=auction_id,
            team_id=payload.team_id,
            bid_amount=payload.bid_amount,
            notes=payload.notes
        )
        return ApiResponse(data=bid, message="Sealed bid submitted successfully")
    except AuctionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (AuctionClosedError, InvalidBidError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/auction/{auction_id}/resolve", response_model=ApiResponse[Dict[str, Any]])
@router.post("/market/auction/{auction_id}/resolve", response_model=ApiResponse[Dict[str, Any]])
def resolve_auction_api(
    auction_id: str,
    force_winner_bid_id: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Resolve an auction, award item to highest bidder, and debit wallet (Organizers only)."""
    try:
        res = black_market_service.resolve_auction(
            db=db,
            auction_id=auction_id,
            actor=actor.id,
            force_winner_bid_id=force_winner_bid_id
        )
        return ApiResponse(data=res, message="Auction resolved")
    except AuctionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (AuctionClosedError, InvalidBidError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==============================================================================
# 3. STANDINGS & QUALIFICATION GATE
# ==============================================================================
@router.get("/market/standings", response_model=ApiResponse[Round3StandingsResponse])
def get_market_standings_api(db: Session = Depends(get_db)):
    """
    Get Round 3 standings with mandatory Final Code gate evaluated FIRST.
    Code-valid squads are ranked descending by remaining wallet points.
    """
    standings_data = black_market_service.calculate_round3_standings(db)
    res = Round3StandingsResponse(
        standings=standings_data["standings"],
        can_finalize=standings_data["can_finalize"],
        code_contingency=standings_data["code_contingency"],
        cutoff_tie=standings_data["cutoff_tie"],
        issues=standings_data["issues"],
        advancing_team_ids=standings_data["advancing_team_ids"]
    )
    return ApiResponse(data=res, message="Round 3 standings loaded")


@router.post("/market/finalize", response_model=ApiResponse[Round3FinalizationResponse])
def finalize_market_api(
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """
    Officially seal Round 3 results, advance top 8 code-valid squads to Round 4,
    and preserve remaining wallet balances for the Grand Finale 10% carryover.
    """
    override = bool(payload and (payload.get("overrideDiscrepancy") or payload.get("override_discrepancy")))
    force_advancing = payload.get("force_advancing_team_ids") if payload else None
    try:
        res = black_market_service.finalize_round3(
            db=db,
            actor=actor,
            override_discrepancy=override,
            force_advancing_team_ids=force_advancing
        )
        return ApiResponse(data=res, message=res.get("message"))
    except RoundFinalizationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==============================================================================
# 4. OVERVIEW, CONFIG & COMPATIBILITY ENDPOINTS
# ==============================================================================
@router.get("", response_model=ApiResponse[Round3OverviewResponse])
def get_round3(db: Session = Depends(get_db)):
    """Get complete Round 3 overview, economy ledger balances, code status, and standings."""
    data = round3_service.get_round3_overview(db)
    return ApiResponse(data=data, message="Round 3 Black Market overview loaded")


@router.get("/config", response_model=ApiResponse[BlackMarketConfigSchema])
def get_config(db: Session = Depends(get_db)):
    """Get Round 3 economic configuration and rule confirmation status."""
    cfg = round3_service.get_or_create_black_market_config(db)
    res = BlackMarketConfigSchema(
        starting_balance=cfg.starting_balance,
        allow_negative_balance=cfg.allow_negative_balance,
        ranking_metric=cfg.ranking_metric,
        scoring_direction=cfg.scoring_direction,
        is_scoring_configured=cfg.is_scoring_configured,
        hidden_code_config=cfg.hidden_code_config or {},
        is_finalized=cfg.is_finalized,
        finalized_at=cfg.finalized_at.isoformat() if cfg.finalized_at else None,
        finalized_by=cfg.finalized_by
    )
    return ApiResponse(data=res)


@router.put("/config", response_model=ApiResponse[BlackMarketConfigSchema])
def update_config(
    payload: UpdateBlackMarketConfigInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Update Black Market parameters or officially confirm scoring rules (Organizers only)."""
    cfg = round3_service.update_black_market_config(db, payload.model_dump(exclude_unset=True), actor)
    res = BlackMarketConfigSchema(
        starting_balance=cfg.starting_balance,
        allow_negative_balance=cfg.allow_negative_balance,
        ranking_metric=cfg.ranking_metric,
        scoring_direction=cfg.scoring_direction,
        is_scoring_configured=cfg.is_scoring_configured,
        hidden_code_config=cfg.hidden_code_config or {},
        is_finalized=cfg.is_finalized,
        finalized_at=cfg.finalized_at.isoformat() if cfg.finalized_at else None,
        finalized_by=cfg.finalized_by
    )
    return ApiResponse(data=res, message="Round 3 configuration updated")


@router.get("/teams", response_model=ApiResponse[List[TeamRound3RecordResponse]])
def get_teams(db: Session = Depends(get_db)):
    """Get all 12 qualified squads for Round 3."""
    overview = round3_service.get_round3_overview(db)
    return ApiResponse(data=overview["records"])


@router.get("/leaderboard", response_model=ApiResponse[List[TeamRound3RecordResponse]])
def get_leaderboard(db: Session = Depends(get_db)):
    """Get server-side calculated leaderboard based on configured ranking metric."""
    overview = round3_service.get_round3_overview(db)
    return ApiResponse(data=overview["records"])


@router.get("/teams/{team_id}/ledger", response_model=ApiResponse[LedgerResponse])
def get_team_ledger_api(team_id: str, db: Session = Depends(get_db)):
    """Get complete transaction history and derived ledger for a squad."""
    overview = round3_service.get_round3_overview(db)
    team_rec = next((r for r in overview["records"] if r["team_id"] == team_id), None)
    if not team_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team '{team_id}' not found in Round 3.")
    return ApiResponse(data=team_rec["ledger"])


@router.post("/teams/{team_id}/transactions", response_model=ApiResponse[TransactionResponse])
def record_transaction(
    team_id: str,
    payload: CreateTransactionInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "marshal", "scorekeeper", "admin"]))
):
    """Post an earn, spend, or adjustment transaction. Balance is derived dynamically."""
    tx = round3_service.create_transaction(
        db=db,
        team_id=team_id,
        amount=payload.amount,
        tx_type=payload.type,
        reason=payload.reason,
        notes=payload.notes,
        actor=actor
    )
    res = TransactionResponse(
        id=tx.id,
        team_id=tx.team_id,
        amount=tx.amount,
        type=tx.type,
        reason=tx.reason,
        organizer_ref=tx.organizer_ref,
        timestamp=tx.timestamp.isoformat(),
        is_reversed=tx.is_reversed,
        notes=tx.notes
    )
    return ApiResponse(data=res, message="Transaction recorded successfully")


@router.post("/transactions/{transaction_id}/reverse", response_model=ApiResponse[TransactionResponse])
def reverse_transaction_api(
    transaction_id: str,
    payload: Optional[ReverseTransactionInput] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Reverse a transaction with audit compensation. Preserves original record."""
    reason = payload.reason if payload and payload.reason else "Organizer reversal"
    rev = round3_service.reverse_transaction(db, transaction_id, reason, actor)
    res = TransactionResponse(
        id=rev.id,
        team_id=rev.team_id,
        amount=rev.amount,
        type=rev.type,
        reason=rev.reason,
        organizer_ref=rev.organizer_ref,
        timestamp=rev.timestamp.isoformat(),
        is_reversed=rev.is_reversed,
        reversed_transaction_id=rev.reversed_transaction_id,
        notes=rev.notes
    )
    return ApiResponse(data=res, message="Transaction reversed with audit compensation")


@router.get("/teams/{team_id}/code", response_model=ApiResponse[TeamCodeRecordResponse])
def get_team_code(team_id: str, db: Session = Depends(get_db)):
    """Get recovered QR code fragments and completion verification for a squad."""
    overview = round3_service.get_round3_overview(db)
    team_rec = next((r for r in overview["records"] if r["team_id"] == team_id), None)
    if not team_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team '{team_id}' not found in Round 3.")
    return ApiResponse(data=team_rec["code_record"])


@router.post("/teams/{team_id}/code/fragments", response_model=ApiResponse[Dict[str, Any]])
def add_code_fragment_api(
    team_id: str,
    payload: AddFragmentInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "marshal", "admin"]))
):
    """Log a discovered QR code fragment for a squad."""
    round3_service.add_code_fragment(db, team_id, payload.fragment_index, payload.notes, actor)
    return ApiResponse(data={"team_id": team_id, "fragment_index": payload.fragment_index}, message="Fragment logged")


@router.post("/teams/{team_id}/code/verify", response_model=ApiResponse[Dict[str, Any]])
def verify_code_api(
    team_id: str,
    payload: VerifyCodeInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Officially verify or override hidden code status for a squad."""
    round3_service.verify_code_status(db, team_id, payload.is_complete, actor)
    return ApiResponse(data={"team_id": team_id, "is_complete": payload.is_complete}, message="Code status verified")


@router.get("/qualification", response_model=ApiResponse[Dict[str, Any]])
def get_qualification(db: Session = Depends(get_db)):
    """Check Round 3 qualification readiness, top 8 cutoff, and tie flags."""
    overview = round3_service.get_round3_overview(db)
    return ApiResponse(data={
        "can_finalize": overview["can_finalize"],
        "issues": overview["issues"],
        "ties_affecting_cutoff": overview["ties_affecting_cutoff"],
        "total_volume": overview["total_volume"],
        "total_transactions": overview["total_transactions"]
    })


@router.post("/finalize", response_model=ApiResponse[FinalizationResponse])
def finalize_round3(
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Officially seal Round 3 results and advance 8 squads to Round 4: The Legal Battle."""
    res = round3_service.finalize_round3(db, actor, payload)
    return ApiResponse(data=res, message=res.get("message"))
