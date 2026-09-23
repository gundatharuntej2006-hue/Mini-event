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
from app.services import round3_service

router = APIRouter(prefix="/rounds/3", tags=["Round 3 — The Black Market"])

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
