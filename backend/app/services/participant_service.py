from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.participant import Participant, ParticipantRole
from app.models.team import Team
from app.schemas.participant import (
    ParticipantCreate,
    ParticipantUpdate,
    ParticipantResponse,
)
from app.services.team_service import serialize_participant

MAX_MEMBERS_PER_TEAM = 5


def get_all_participants(
    db: Session,
    team_id: Optional[str] = None,
    search: Optional[str] = None,
    checked_in: Optional[bool] = None,
    include_private_info: bool = True,
) -> List[ParticipantResponse]:
    query = db.query(Participant)
    if team_id:
        query = query.filter(Participant.team_id == team_id)
    if checked_in is not None:
        query = query.filter(Participant.checked_in == checked_in)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            (Participant.name.ilike(search_pattern)) |
            (Participant.usn.ilike(search_pattern)) |
            (Participant.email.ilike(search_pattern))
        )
    participants = query.order_by(Participant.name.asc()).all()
    return [serialize_participant(p, include_private_info=include_private_info) for p in participants]


def get_participant_by_id(db: Session, participant_id: str) -> Optional[Participant]:
    return db.query(Participant).filter(Participant.id == participant_id).first()


def get_participant_by_usn(db: Session, usn: str) -> Optional[Participant]:
    return db.query(Participant).filter(Participant.usn == usn.strip().upper()).first()


def check_and_lock_team_capacity(
    db: Session,
    team_id: str,
    source_team_id: Optional[str] = None,
    current_participant_id: Optional[str] = None
) -> Team:
    """
    Verifies team existence and locks target team row for atomic capacity validation.
    When moving from a source team, locks both teams in deterministic sorted ID order
    to prevent deadlock cycles across concurrent cross-transfers in PostgreSQL.
    """
    teams_to_lock = [team_id]
    if source_team_id and source_team_id != team_id:
        teams_to_lock.append(source_team_id)
    teams_to_lock.sort()

    for tid in teams_to_lock:
        q = db.query(Team).filter(Team.id == tid)
        if db.bind and db.bind.dialect.name == "postgresql":
            q.with_for_update().first()
        else:
            q.first()

    target_team = db.query(Team).filter(Team.id == team_id).first()
    if not target_team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target team with id '{team_id}' does not exist."
        )

    count_query = db.query(func.count(Participant.id)).filter(Participant.team_id == team_id)
    if current_participant_id:
        count_query = count_query.filter(Participant.id != current_participant_id)
    
    current_count = count_query.scalar() or 0
    if current_count >= MAX_MEMBERS_PER_TEAM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team '{target_team.name}' has reached the maximum squad limit of {MAX_MEMBERS_PER_TEAM} members."
        )
    return target_team


def create_participant(db: Session, part_in: ParticipantCreate) -> ParticipantResponse:
    normalized_usn = part_in.usn.strip().upper()
    existing_usn = get_participant_by_usn(db, normalized_usn)
    if existing_usn:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A participant with USN '{normalized_usn}' is already registered."
        )

    normalized_email = part_in.email.strip().lower()
    existing_email = db.query(Participant).filter(Participant.email.ilike(normalized_email)).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A participant with email '{normalized_email}' is already registered."
        )

    if part_in.team_id:
        check_and_lock_team_capacity(db, part_in.team_id)

    check_in_time = datetime.now(timezone.utc) if part_in.checked_in else None

    try:
        participant = Participant(
            name=part_in.name.strip(),
            email=part_in.email.strip().lower(),
            usn=normalized_usn,
            phone=part_in.phone.strip() if part_in.phone else None,
            role=part_in.role,
            checked_in=part_in.checked_in,
            checked_in_at=check_in_time,
            team_id=part_in.team_id,
        )
        db.add(participant)
        db.commit()
        db.refresh(participant)
        return serialize_participant(participant, include_private_info=True)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise e


def update_participant(
    db: Session,
    participant: Participant,
    part_in: ParticipantUpdate
) -> ParticipantResponse:
    if part_in.usn is not None:
        normalized_usn = part_in.usn.strip().upper()
        existing = db.query(Participant).filter(
            Participant.usn == normalized_usn,
            Participant.id != participant.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A participant with USN '{normalized_usn}' is already registered."
            )
        participant.usn = normalized_usn

    if part_in.team_id is not None and part_in.team_id != participant.team_id:
        if part_in.team_id != "":
            check_and_lock_team_capacity(
                db,
                part_in.team_id,
                source_team_id=participant.team_id,
                current_participant_id=participant.id
            )
            participant.team_id = part_in.team_id
        else:
            participant.team_id = None

    if part_in.name is not None:
        participant.name = part_in.name.strip()
    if part_in.email is not None:
        participant.email = part_in.email.strip().lower()
    if part_in.phone is not None:
        participant.phone = part_in.phone.strip() if part_in.phone else None
    if part_in.role is not None:
        participant.role = part_in.role
    if part_in.checked_in is not None:
        if part_in.checked_in != participant.checked_in:
            participant.checked_in = part_in.checked_in
            participant.checked_in_at = datetime.now(timezone.utc) if part_in.checked_in else None

    try:
        db.commit()
        db.refresh(participant)
        return serialize_participant(participant, include_private_info=True)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise e


def toggle_participant_checkin(
    db: Session,
    participant: Participant,
    checked_in: bool
) -> ParticipantResponse:
    participant.checked_in = checked_in
    participant.checked_in_at = datetime.now(timezone.utc) if checked_in else None
    try:
        db.commit()
        db.refresh(participant)
        return serialize_participant(participant, include_private_info=True)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise e


def transfer_participant(
    db: Session,
    participant: Participant,
    target_team_id: Optional[str]
) -> ParticipantResponse:
    if target_team_id:
        if participant.team_id == target_team_id:
            return serialize_participant(participant, include_private_info=True)
        check_and_lock_team_capacity(
            db,
            target_team_id,
            source_team_id=participant.team_id,
            current_participant_id=participant.id
        )
        participant.team_id = target_team_id
    else:
        participant.team_id = None
        participant.role = ParticipantRole.MEMBER

    try:
        db.commit()
        db.refresh(participant)
        return serialize_participant(participant, include_private_info=True)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise e


def delete_participant(db: Session, participant: Participant) -> None:
    try:
        db.delete(participant)
        db.commit()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise e