from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.team import Team, TeamStatus
from app.models.participant import Participant, ParticipantRole
from app.schemas.team import TeamCreate, TeamUpdate, TeamResponse
from app.schemas.participant import ParticipantResponse


def serialize_participant(part: Participant, include_private_info: bool = True) -> ParticipantResponse:
    return ParticipantResponse(
        id=part.id,
        name=part.name,
        email=part.email if include_private_info else None,
        usn=part.usn if include_private_info else None,
        phone=part.phone if include_private_info else None,
        role=part.role,
        checked_in=part.checked_in,
        checked_in_at=part.checked_in_at,
        team_id=part.team_id,
        team_name=part.team.name if part.team else None,
        created_at=part.created_at,
    )


def serialize_team(team: Team, include_private_info: bool = True) -> TeamResponse:
    leader = next((m for m in team.members if m.role == ParticipantRole.LEADER), None)
    if not leader and team.members:
        leader_name = team.members[0].name
    elif leader:
        leader_name = leader.name
    else:
        leader_name = "Unassigned"

    serialized_members = [serialize_participant(m, include_private_info=include_private_info) for m in team.members]

    return TeamResponse(
        id=team.id,
        team_number=team.team_number,
        name=team.name,
        leader_name=leader_name,
        members_count=len(team.members),
        members=serialized_members,
        status=team.status,
        current_round=team.current_round,
        is_qualified_for_next_round=team.is_qualified_for_next_round,
        total_score=team.total_score,
        assigned_table=team.assigned_table,
        created_at=team.created_at,
    )


def get_all_teams(db: Session, include_private_info: bool = True) -> List[TeamResponse]:
    teams = db.query(Team).order_by(Team.team_number.asc()).all()
    return [serialize_team(t, include_private_info=include_private_info) for t in teams]


def get_team_by_id(db: Session, team_id: str) -> Optional[Team]:
    return db.query(Team).filter(Team.id == team_id).first()


def get_team_by_number(db: Session, team_number: int) -> Optional[Team]:
    return db.query(Team).filter(Team.team_number == team_number).first()


def get_next_team_number(db: Session) -> int:
    max_num = db.query(func.max(Team.team_number)).scalar()
    return (max_num or 0) + 1


def create_team(db: Session, team_in: TeamCreate) -> TeamResponse:
    # 1. Enforce 32-team tournament capacity limit
    current_team_count = db.query(func.count(Team.id)).scalar() or 0
    if current_team_count >= 32:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tournament capacity reached. Maximum of 32 squads can be registered."
        )

    # 2. Check team name uniqueness
    existing_name = db.query(Team).filter(Team.name.ilike(team_in.name.strip())).first()
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A team with the name '{team_in.name}' already exists."
        )

    # 3. Validate member roster if provided
    if team_in.members is not None:
        if len(team_in.members) != 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A squad must be registered with exactly 5 participants (received {len(team_in.members)})."
            )

        leaders = [m for m in team_in.members if m.role == ParticipantRole.LEADER]
        if len(leaders) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A squad must have exactly one leader (found {len(leaders)})."
            )

        # Validate required fields on each member
        for i, m in enumerate(team_in.members, 1):
            if not m.name or not m.name.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Member {i} full name is required."
                )
            if not m.usn or not m.usn.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Member {i} USN is required."
                )
            if not m.email or not str(m.email).strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Member {i} institutional email is required."
                )

        # Intra-form uniqueness
        submitted_usns = [m.usn.strip().upper() for m in team_in.members]
        if len(submitted_usns) != len(set(submitted_usns)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate USN detected within the submitted squad members."
            )

        submitted_emails = [str(m.email).strip().lower() for m in team_in.members]
        if len(submitted_emails) != len(set(submitted_emails)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate email detected within the submitted squad members."
            )

        # Database uniqueness
        for m in team_in.members:
            norm_usn = m.usn.strip().upper()
            existing_p_usn = db.query(Participant).filter(Participant.usn == norm_usn).first()
            if existing_p_usn:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Participant with USN '{norm_usn}' is already registered."
                )
            norm_email = str(m.email).strip().lower()
            existing_p_email = db.query(Participant).filter(Participant.email.ilike(norm_email)).first()
            if existing_p_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Participant with email '{norm_email}' is already registered."
                )

    # 4. Atomic transaction: create team and all participants together
    try:
        next_num = get_next_team_number(db)
        table_val = team_in.assigned_table.strip() if team_in.assigned_table else f"Table {next_num}"
        team = Team(
            team_number=next_num,
            name=team_in.name.strip(),
            assigned_table=table_val,
            status=TeamStatus.REGISTERED,
            current_round=1,
            is_qualified_for_next_round=False,
            total_score=0.0,
        )
        db.add(team)
        db.flush()

        if team_in.members:
            for m in team_in.members:
                part = Participant(
                    name=m.name.strip(),
                    email=str(m.email).strip().lower(),
                    usn=m.usn.strip().upper(),
                    phone=m.phone.strip() if m.phone else None,
                    role=m.role,
                    checked_in=False,
                    team_id=team.id,
                )
                db.add(part)

        db.commit()
        db.refresh(team)
        return serialize_team(team, include_private_info=True)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register squad: {str(e)}"
        )


def update_team(db: Session, team: Team, team_in: TeamUpdate) -> TeamResponse:
    if team_in.name is not None:
        new_name = team_in.name.strip()
        existing = db.query(Team).filter(Team.name.ilike(new_name), Team.id != team.id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A team with the name '{new_name}' already exists."
            )
        team.name = new_name
    
    if team_in.assigned_table is not None:
        team.assigned_table = team_in.assigned_table.strip() if team_in.assigned_table else None
        
    if team_in.status is not None:
        team.status = team_in.status

    db.commit()
    db.refresh(team)
    return serialize_team(team, include_private_info=True)


def delete_team(db: Session, team: Team) -> None:
    # Unassign all members safely
    for member in list(team.members):
        member.team_id = None
        member.role = ParticipantRole.MEMBER
    team.members.clear()
    db.flush()
    db.delete(team)
    db.commit()