"""Audited, super-admin-only roster corrections for the live event."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.routes.r1_event import current_account, require_roles
from app.core.security import verify_password
from app.db.session import get_db
from app.models.event_account import EventAccount, EventRole, Round1Override
from app.models.participant import Participant
from app.models.round1 import Round1RouteAllocationModel
from app.models.team import Team


router = APIRouter(prefix="/r1/control", tags=["Round 1 Roster Control"])


class RosterMemberRename(BaseModel):
    participant_id: str = Field(min_length=3, max_length=50)
    name: str = Field(min_length=2, max_length=255)


class TeamRosterCorrectionInput(BaseModel):
    current_super_password: str = Field(min_length=1, max_length=128)
    team_identifier: str = Field(min_length=4, max_length=40)
    team_name: str = Field(min_length=2, max_length=255)
    members: list[RosterMemberRename] = Field(min_length=5, max_length=5)
    reason: str = Field(min_length=3, max_length=500)


def normalise_identifier(value: str) -> str:
    """Accept either 1017 or TEAM1017, but retain the canonical route ID."""
    return value.strip().upper().removeprefix("TEAM")


@router.post("/roster/team")
def correct_team_roster(
    payload: TeamRosterCorrectionInput,
    account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    """Rename one existing team and its five existing roster entries safely."""
    if not verify_password(payload.current_super_password, account.password_hash):
        raise HTTPException(status_code=401, detail="Super admin password confirmation failed.")

    identifier = normalise_identifier(payload.team_identifier)
    allocation = db.query(Round1RouteAllocationModel).filter(
        Round1RouteAllocationModel.team_identifier == identifier,
    ).first()
    if not allocation or not allocation.team_id:
        raise HTTPException(status_code=404, detail="Team route not found.")

    team = db.query(Team).filter(Team.id == allocation.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team roster record is missing.")

    requested_names = {item.participant_id: item.name.strip() for item in payload.members}
    team_members = db.query(Participant).filter(Participant.team_id == team.id).all()
    existing_ids = {member.id for member in team_members}
    if len(team_members) != 5 or len(requested_names) != 5 or set(requested_names) != existing_ids:
        raise HTTPException(
            status_code=400,
            detail="Supply each of this team's five existing participant IDs exactly once; members cannot be moved by this correction.",
        )

    team_name = payload.team_name.strip()
    duplicate = db.query(Team).filter(Team.name.ilike(team_name), Team.id != team.id).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Another team already uses that name.")

    for member in team_members:
        member.name = requested_names[member.id]
    team.name = team_name
    allocation.team_name = team_name
    db.query(EventAccount).filter(
        EventAccount.role == EventRole.PARTICIPANT,
        EventAccount.team_id == team.id,
    ).update({EventAccount.display_name: team_name}, synchronize_session=False)
    db.add(Round1Override(
        team_identifier=identifier,
        checkpoint_number=0,
        action="ROSTER_UPDATE",
        reason=payload.reason.strip(),
        performed_by=account.id,
    ))
    db.commit()
    return {
        "success": True,
        "data": {
            "team_identifier": identifier,
            "team_name": team_name,
            "members": [
                {"participant_id": member.id, "name": requested_names[member.id]}
                for member in team_members
            ],
        },
        "message": "Team roster updated and recorded in the Round 1 audit log.",
    }
