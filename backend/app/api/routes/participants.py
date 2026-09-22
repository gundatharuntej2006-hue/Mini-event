from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.common import ApiResponse
from app.schemas.participant import (
    ParticipantCreate,
    ParticipantUpdate,
    ParticipantResponse,
    ParticipantTransferRequest,
    ParticipantCheckInToggle,
)
from app.services.participant_service import (
    get_all_participants,
    get_participant_by_id,
    create_participant,
    update_participant,
    toggle_participant_checkin,
    transfer_participant,
    delete_participant,
)
from app.services.team_service import serialize_participant

router = APIRouter(prefix="/participants", tags=["Participants"])


@router.get("", response_model=ApiResponse[List[ParticipantResponse]])
def list_participants(
    team_id: Optional[str] = Query(None, alias="teamId"),
    search: Optional[str] = Query(None),
    checked_in: Optional[bool] = Query(None, alias="checkedIn"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL, UserRole.JUDGE]))
):
    participants = get_all_participants(
        db,
        team_id=team_id,
        search=search,
        checked_in=checked_in,
        include_private_info=True
    )
    return ApiResponse(
        data=participants,
        message=f"Retrieved {len(participants)} participants"
    )


@router.get("/{participant_id}", response_model=ApiResponse[ParticipantResponse])
def get_participant(
    participant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL, UserRole.JUDGE]))
):
    part = get_participant_by_id(db, participant_id)
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant with ID '{participant_id}' not found"
        )
    return ApiResponse(
        data=serialize_participant(part, include_private_info=True),
        message="Participant details retrieved"
    )


@router.post("", response_model=ApiResponse[ParticipantResponse], status_code=status.HTTP_201_CREATED)
def create_new_participant(
    part_in: ParticipantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL]))
):
    participant = create_participant(db, part_in)
    return ApiResponse(
        data=participant,
        message=f"Participant '{participant.name}' ({participant.usn}) registered successfully"
    )


@router.put("/{participant_id}", response_model=ApiResponse[ParticipantResponse])
def update_existing_participant(
    participant_id: str,
    part_in: ParticipantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL]))
):
    part = get_participant_by_id(db, participant_id)
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant with ID '{participant_id}' not found"
        )
    updated = update_participant(db, part, part_in)
    return ApiResponse(
        data=updated,
        message=f"Participant '{updated.name}' updated successfully"
    )


@router.patch("/{participant_id}/check-in", response_model=ApiResponse[ParticipantResponse])
def toggle_check_in(
    participant_id: str,
    body: ParticipantCheckInToggle,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL]))
):
    part = get_participant_by_id(db, participant_id)
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant with ID '{participant_id}' not found"
        )
    updated = toggle_participant_checkin(db, part, body.checked_in)
    action_text = "checked in" if body.checked_in else "check-in cleared"
    return ApiResponse(
        data=updated,
        message=f"Participant '{updated.name}' {action_text}"
    )


@router.post("/{participant_id}/transfer", response_model=ApiResponse[ParticipantResponse])
def transfer_team_assignment(
    participant_id: str,
    transfer_in: ParticipantTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL]))
):
    part = get_participant_by_id(db, participant_id)
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant with ID '{participant_id}' not found"
        )
    transferred = transfer_participant(db, part, transfer_in.target_team_id)
    dest_name = transferred.team_name or "Unassigned Pool"
    return ApiResponse(
        data=transferred,
        message=f"Participant '{transferred.name}' moved to '{dest_name}'"
    )


@router.delete("/{participant_id}", response_model=ApiResponse[dict])
def delete_existing_participant(
    participant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER]))
):
    part = get_participant_by_id(db, participant_id)
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant with ID '{participant_id}' not found"
        )
    name = part.name
    delete_participant(db, part)
    return ApiResponse(
        data={"id": participant_id, "name": name},
        message=f"Participant '{name}' deleted successfully"
    )