"""
Code Hunt & Final Code Gate API Endpoints for EVENT HQ.
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Endpoints:
- POST /code-hunt/{team_id}/fragment/1
- POST /code-hunt/{team_id}/fragment/2
- POST /code-hunt/{team_id}/verify
- GET /code-hunt/{team_id}/status
- POST /code-hunt/{team_id}/recover-missing-fragment
- GET /code-hunt/eligibility/r4/{team_id}
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import require_role, get_optional_user
from app.models.user import User, UserRole
from app.schemas.common import ApiResponse
from app.schemas.tournament_extensions import (
    FinalCodeRecordResponse,
    CodeHuntStatusResponse,
    RecordFragmentRequest,
    VerifyFinalCodeRequest,
    RecoverMissingFragmentRequest,
    Round4EligibilityResponse,
)
from app.services import code_hunt_service
from app.services.code_hunt_service import (
    CodeHuntError,
    CodeHuntNotFoundError,
    FragmentAlreadyRecordedError,
    FinalCodeVerificationError,
    MissingFragmentPurchaseError,
)
from app.services.wallet import InsufficientFundsError

router = APIRouter(prefix="/code-hunt", tags=["Code Hunt & Final Code Gate"])


def is_organizer_or_marshal(user: Optional[User]) -> bool:
    return user is not None and user.role in (UserRole.ORGANIZER, UserRole.MARSHAL)


@router.post("/{team_id}/fragment/{fragment_number}", response_model=ApiResponse[FinalCodeRecordResponse])
def record_code_fragment(
    team_id: str,
    fragment_number: int,
    payload: RecordFragmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    """
    Record one Final Code fragment for a squad.

    The ODDyssey plan has four - ODD and 42 from Round 1, ECHO and PRIME from
    Round 2 - so this is one endpoint taking the fragment number rather than a
    hardcoded route per fragment. /fragment/1 and /fragment/2 keep working
    unchanged; /fragment/3 and /fragment/4 now exist.

    Restricted to organizers and marshals.
    """
    try:
        record = code_hunt_service.record_fragment(
            db=db,
            team_id=team_id,
            fragment_number=fragment_number,
            fragment_value=payload.fragment_value,
            actor=current_user.email,
            overwrite=payload.overwrite,
        )
        return ApiResponse(
            data=record,
            message=f"Fragment {fragment_number} recorded successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FragmentAlreadyRecordedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except CodeHuntNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CodeHuntError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{team_id}/verify", response_model=ApiResponse[FinalCodeRecordResponse])
def verify_team_final_code(
    team_id: str,
    payload: VerifyFinalCodeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    """
    Verifies the squad's assembled Final Code against both stored fragments.
    On success, unlocks Round 4 qualification.
    """
    try:
        code_hunt_service.verify_final_code(
            db=db,
            team_id=team_id,
            supplied_code=payload.supplied_code,
            actor=current_user.email,
            notes=payload.notes,
        )
        record = code_hunt_service.get_or_create_final_code_record(db, team_id)
        return ApiResponse(
            data=record,
            message="Final Code verified successfully. Squad is eligible for Round 4."
        )
    except FinalCodeVerificationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except CodeHuntNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{team_id}/status", response_model=ApiResponse[CodeHuntStatusResponse])
def get_team_code_hunt_status(
    team_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Retrieves squad code hunt status.
    Confidentiality: Secret fragment strings are hidden from public callers.
    """
    is_org = is_organizer_or_marshal(current_user)
    status_data = code_hunt_service.get_code_hunt_status(db, team_id, is_organizer=is_org)
    return ApiResponse(
        data=status_data,
        message="Code hunt status retrieved"
    )


@router.post("/{team_id}/recover-missing-fragment", response_model=ApiResponse[FinalCodeRecordResponse])
def purchase_missing_fragment(
    team_id: str,
    payload: RecoverMissingFragmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    """
    Purchases a missing code fragment using tournament wallet points via the Black Market.
    Restricted to organizers/marshals executing squad purchase requests.
    """
    try:
        record = code_hunt_service.recover_missing_fragment(
            db=db,
            team_id=team_id,
            fragment_number=payload.fragment_number,
            price=payload.price,
            actor=current_user.email,
            recovered_value=payload.recovered_value,
        )
        return ApiResponse(
            data=record,
            message=f"Missing Fragment #{payload.fragment_number} recovered via Black Market"
        )
    except MissingFragmentPurchaseError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InsufficientFundsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except CodeHuntNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/eligibility/r4/{team_id}", response_model=ApiResponse[Round4EligibilityResponse])
def check_r4_eligibility(
    team_id: str,
    db: Session = Depends(get_db),
):
    """
    Checks if a squad meets the mandatory Final Code gate for Round 4.
    """
    can_enter = code_hunt_service.can_enter_round4(db, team_id)
    msg = (
        "Team has verified their Final Code and is eligible for Round 4."
        if can_enter
        else "Team has NOT verified their Final Code and cannot enter Round 4."
    )
    return ApiResponse(
        data=Round4EligibilityResponse(
            team_id=team_id,
            is_eligible=can_enter,
            final_code_verified=can_enter,
            message=msg,
        ),
        message=msg
    )
