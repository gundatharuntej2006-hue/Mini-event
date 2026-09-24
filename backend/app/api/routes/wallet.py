"""
Tournament Wallet & Points Economy API Endpoints.
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Security Policy:
- Read endpoints are available to authenticated users/teams.
- Balance mutations (adjustments, penalties) are STRICTLY restricted to ORGANIZER roles.
- No public or unauthenticated mutations are permitted.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_role, get_optional_user
from app.models.user import User, UserRole
from app.schemas.common import ApiResponse
from app.schemas.tournament_extensions import (
    TeamWalletResponse,
    WalletTransactionResponse,
    WalletAdjustmentCreate,
    WalletPenaltyCreate,
)
from app.services import wallet as wallet_service
from app.services.wallet import (
    WalletNotFoundError,
    InsufficientFundsError,
    InvalidAmountError,
    InvalidPenaltyError,
    InvalidAdjustmentError,
    TransactionReversalError,
)

router = APIRouter(prefix="/teams/{team_id}/wallet", tags=["Wallet"])


@router.get("", response_model=ApiResponse[TeamWalletResponse])
def get_team_wallet(
    team_id: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """
    Retrieve or initialize the tournament wallet for a team.
    Defaults to canonical STARTING_WALLET_BALANCE (1000 points).
    """
    try:
        wallet = wallet_service.get_or_create_wallet(
            db=db,
            team_id=team_id,
            created_by=user.email if user else None,
        )
        return ApiResponse(
            data=TeamWalletResponse.model_validate(wallet),
            message="Team tournament wallet retrieved successfully"
        )
    except WalletNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/transactions", response_model=ApiResponse[List[WalletTransactionResponse]])
def get_team_wallet_transactions(
    team_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    """
    Retrieve immutable audit ledger transactions for a team wallet.
    Chronologically ordered (newest first).
    """
    wallet = wallet_service.get_wallet(db=db, team_id=team_id)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet for team '{team_id}' not found."
        )

    txs = wallet_service.get_wallet_transactions(db=db, team_id=team_id, limit=limit, offset=offset)
    return ApiResponse(
        data=[WalletTransactionResponse.model_validate(tx) for tx in txs],
        message=f"Retrieved {len(txs)} ledger transactions"
    )


@router.post("/adjust", response_model=ApiResponse[WalletTransactionResponse])
def adjust_team_balance(
    team_id: str,
    payload: WalletAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER])),
):
    """
    Organizer-only manual balance adjustment with mandatory audit justification.
    Never bypasses the ledger.
    """
    try:
        tx = wallet_service.manual_adjustment(
            db=db,
            team_id=team_id,
            amount=payload.amount,
            reason=payload.reason,
            created_by=current_user.email,
            allow_negative_balance=payload.allow_negative_balance,
        )
        return ApiResponse(
            data=WalletTransactionResponse.model_validate(tx),
            message="Manual balance adjustment recorded successfully"
        )
    except WalletNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientFundsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except (InvalidAmountError, InvalidAdjustmentError) as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/penalty", response_model=ApiResponse[WalletTransactionResponse])
def apply_team_penalty(
    team_id: str,
    payload: WalletPenaltyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER])),
):
    """
    Organizer-only disciplinary infraction penalty deduction.
    Enforces documented penalty range [-200, -50].
    """
    try:
        tx = wallet_service.apply_penalty(
            db=db,
            team_id=team_id,
            penalty_amount=payload.amount,
            reason=payload.reason,
            created_by=current_user.email,
        )
        return ApiResponse(
            data=WalletTransactionResponse.model_validate(tx),
            message="Organizer disciplinary penalty applied successfully"
        )
    except WalletNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InsufficientFundsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InvalidPenaltyError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
