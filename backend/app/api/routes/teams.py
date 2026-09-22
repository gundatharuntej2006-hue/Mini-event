from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_role, get_optional_user
from app.models.user import User, UserRole
from app.schemas.common import ApiResponse
from app.schemas.team import TeamCreate, TeamUpdate, TeamResponse
from app.services.team_service import (
    get_all_teams,
    get_team_by_id,
    create_team,
    update_team,
    delete_team,
    serialize_team,
)

router = APIRouter(prefix="/teams", tags=["Teams"])


def is_staff_user(user: Optional[User]) -> bool:
    return user is not None and user.role in [UserRole.ORGANIZER, UserRole.MARSHAL, UserRole.JUDGE]


@router.get("", response_model=ApiResponse[List[TeamResponse]])
def list_teams(
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    include_private = is_staff_user(user)
    teams = get_all_teams(db, include_private_info=include_private)
    return ApiResponse(
        data=teams,
        message=f"Retrieved {len(teams)} teams"
    )


@router.get("/{team_id}", response_model=ApiResponse[TeamResponse])
def get_team(
    team_id: str,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user)
):
    team = get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID '{team_id}' not found"
        )
    include_private = is_staff_user(user)
    return ApiResponse(
        data=serialize_team(team, include_private_info=include_private),
        message="Team details retrieved"
    )


@router.post("", response_model=ApiResponse[TeamResponse], status_code=status.HTTP_201_CREATED)
def create_new_team(
    team_in: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL]))
):
    team = create_team(db, team_in)
    return ApiResponse(
        data=team,
        message=f"Team '{team.name}' registered successfully"
    )


@router.put("/{team_id}", response_model=ApiResponse[TeamResponse])
def update_existing_team(
    team_id: str,
    team_in: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL]))
):
    team = get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID '{team_id}' not found"
        )
    updated = update_team(db, team, team_in)
    return ApiResponse(
        data=updated,
        message=f"Team '{updated.name}' updated successfully"
    )


@router.delete("/{team_id}", response_model=ApiResponse[dict])
def delete_existing_team(
    team_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER]))
):
    team = get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID '{team_id}' not found"
        )
    team_name = team.name
    delete_team(db, team)
    return ApiResponse(
        data={"id": team_id, "name": team_name},
        message=f"Team '{team_name}' and member associations removed safely"
    )