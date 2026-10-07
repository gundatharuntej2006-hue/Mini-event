"""Small, mobile-first API surface for the live Treasure Hunt."""

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_access_token, verify_password
from app.core.constants import R1_LOCATIONS
from app.db.session import get_db
from app.models.event_account import EventAccount, EventRole, Round1Override
from app.models.round1 import GateCheckinModel, Round1CheckpointAttemptModel, Round1ConfigModel, Round1RouteAllocationModel
from app.services.round1_service import get_or_create_route_allocations

router = APIRouter(prefix="/r1", tags=["Round 1 Live Event"])
bearer = HTTPBearer(auto_error=False)

EXACT_ANSWERS = {1: "ODD", 2: "42", 3: "ODD-42"}


class LoginInput(BaseModel):
    login_id: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=1, max_length=128)


class ScanInput(BaseModel):
    location: int = Field(ge=1, le=8)


class AnswerInput(BaseModel):
    # Intentionally no normalisation: capitals, spaces, and hyphens are exact.
    answer: str = Field(min_length=1, max_length=255)


class OverrideInput(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    team_identifier: str
    action: Literal["UNLOCK", "MARK_CORRECT"]
    reason: str = Field(min_length=3, max_length=500)


def now() -> datetime:
    return datetime.now(timezone.utc)


def current_account(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> EventAccount:
    if not credentials:
        raise HTTPException(status_code=401, detail="Please sign in.")
    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Your session is invalid or expired.")
    account = db.query(EventAccount).filter(EventAccount.id == payload["sub"], EventAccount.is_active == True).first()
    if not account:
        raise HTTPException(status_code=401, detail="Your account is not active.")
    return account


def require_roles(*roles: EventRole):
    def guard(account: EventAccount = Depends(current_account)) -> EventAccount:
        if account.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have access to this screen.")
        return account
    return guard


def allocation_for_account(db: Session, account: EventAccount) -> Round1RouteAllocationModel:
    allocation = db.query(Round1RouteAllocationModel).filter(Round1RouteAllocationModel.team_id == account.team_id).first()
    if not allocation:
        get_or_create_route_allocations(db)
        allocation = db.query(Round1RouteAllocationModel).filter(Round1RouteAllocationModel.team_id == account.team_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="This team does not have a Round 1 route yet.")
    return allocation


def checkpoint_for(allocation: Round1RouteAllocationModel) -> int:
    if not allocation.cp1_completed:
        return 1
    if not allocation.cp2_completed:
        return 2
    if not allocation.cp3_completed:
        return 3
    return 4


def checkpoint_values(allocation: Round1RouteAllocationModel, checkpoint: int) -> tuple[int, str, int, bool]:
    return (
        getattr(allocation, f"cp{checkpoint}_location"),
        getattr(allocation, f"cp{checkpoint}_set"),
        getattr(allocation, f"cp{checkpoint}_attempts"),
        getattr(allocation, f"cp{checkpoint}_completed"),
    )


def has_scanned(db: Session, allocation: Round1RouteAllocationModel, checkpoint: int, location: int) -> bool:
    return db.query(GateCheckinModel).filter(
        GateCheckinModel.team_id == allocation.team_id,
        GateCheckinModel.round_number == checkpoint,
        GateCheckinModel.gate_number == location,
        GateCheckinModel.status == "VERIFIED",
    ).first() is not None


def latest_attempt(db: Session, allocation: Round1RouteAllocationModel, checkpoint: int) -> Round1CheckpointAttemptModel | None:
    """Return the latest submitted value for staff-only operational screens."""
    return db.query(Round1CheckpointAttemptModel).filter(
        Round1CheckpointAttemptModel.team_id == allocation.team_id,
        Round1CheckpointAttemptModel.checkpoint_number == checkpoint,
    ).order_by(
        Round1CheckpointAttemptModel.created_at.desc(),
        Round1CheckpointAttemptModel.attempt_number.desc(),
    ).first()


def event_config(db: Session) -> Round1ConfigModel:
    config = db.query(Round1ConfigModel).filter(Round1ConfigModel.id == 1).first()
    if not config:
        config = Round1ConfigModel(id=1, checkpoint_names=["Treasure Hunt", "Treasure Hunt", "Treasure Hunt"])
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def participant_state(db: Session, account: EventAccount) -> dict:
    allocation = allocation_for_account(db, account)
    checkpoint = checkpoint_for(allocation)
    config = event_config(db)
    if checkpoint == 4:
        return {"complete": True, "checkpoint": 4, "round_started": bool(config.started_at), "instagram": "ASYMPTOTES_BMSIT"}
    location, _set, attempts, _completed = checkpoint_values(allocation, checkpoint)
    return {
        "complete": False,
        "checkpoint": checkpoint,
        "round_started": bool(config.started_at),
        "riddle": R1_LOCATIONS[location]["riddle"],
        "is_scanned": has_scanned(db, allocation, checkpoint, location),
        "attempts_used": attempts,
        "is_locked": attempts >= 3,
        # Location name, question set, target, other teams and future clues are withheld.
    }


@router.post("/login")
def login(payload: LoginInput, db: Session = Depends(get_db)):
    account = db.query(EventAccount).filter(EventAccount.login_id == payload.login_id.strip().upper()).first()
    if not account or not account.is_active or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect ID or password.")
    token = create_access_token(account.id, account.role.value)
    return {"success": True, "data": {"token": token, "role": account.role.value, "display_name": account.display_name}, "message": "Signed in."}


@router.get("/me")
def me(account: EventAccount = Depends(current_account)):
    return {"success": True, "data": {"role": account.role.value, "display_name": account.display_name, "location_number": account.location_number}, "message": "Account loaded."}


@router.get("/participant/state")
def get_participant_state(account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)), db: Session = Depends(get_db)):
    return {"success": True, "data": participant_state(db, account), "message": "Current event state loaded."}


@router.post("/participant/scan")
def scan(payload: ScanInput, account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)), db: Session = Depends(get_db)):
    config = event_config(db)
    if not config.started_at:
        raise HTTPException(status_code=409, detail="The round has not started yet.")
    allocation = allocation_for_account(db, account)
    checkpoint = checkpoint_for(allocation)
    if checkpoint == 4:
        raise HTTPException(status_code=409, detail="Your team has already completed Round 1.")
    location, _set, attempts, _completed = checkpoint_values(allocation, checkpoint)
    if attempts >= 3:
        raise HTTPException(status_code=409, detail="This checkpoint is locked. Please contact a super admin.")
    if payload.location != location:
        raise HTTPException(status_code=403, detail="This is not your active location.")
    if not has_scanned(db, allocation, checkpoint, location):
        db.add(GateCheckinModel(
            id=f"chk-{uuid.uuid4().hex[:18]}", team_id=allocation.team_id, team_name=allocation.team_name or account.display_name,
            round_number=checkpoint, gate_number=location, scanned_at=now(), status="VERIFIED",
        ))
        db.commit()
    return {"success": True, "data": participant_state(db, account), "message": "Location verified. Enter the envelope answer exactly."}


@router.post("/participant/answer")
def answer(payload: AnswerInput, account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)), db: Session = Depends(get_db)):
    config = event_config(db)
    if not config.started_at:
        raise HTTPException(status_code=409, detail="The round has not started yet.")
    allocation = allocation_for_account(db, account)
    checkpoint = checkpoint_for(allocation)
    if checkpoint == 4:
        raise HTTPException(status_code=409, detail="Your team has already completed Round 1.")
    location, question_set, attempts, _completed = checkpoint_values(allocation, checkpoint)
    if attempts >= 3:
        raise HTTPException(status_code=409, detail="This checkpoint is locked. Please contact a super admin.")
    if not has_scanned(db, allocation, checkpoint, location):
        raise HTTPException(status_code=403, detail="Scan your active location QR before entering an answer.")

    exact = payload.answer == EXACT_ANSWERS[checkpoint]
    new_attempts = attempts + 1
    db.add(Round1CheckpointAttemptModel(
        id=f"att-{uuid.uuid4().hex[:18]}", team_identifier=allocation.team_identifier, team_id=allocation.team_id,
        checkpoint_number=checkpoint, location_number=location, question_set=question_set,
        attempt_number=new_attempts, submitted_answer=payload.answer, is_correct=exact, created_at=now(),
    ))
    setattr(allocation, f"cp{checkpoint}_attempts", new_attempts)
    if exact:
        setattr(allocation, f"cp{checkpoint}_completed", True)
        setattr(allocation, f"cp{checkpoint}_completed_at", now())
    db.commit()
    state = participant_state(db, account)
    message = "Correct. Your next clue is now available." if exact and checkpoint < 3 else "Your time has been recorded. Please check Instagram for results." if exact else "That exact answer was not accepted. Check capitals, spaces, and hyphens."
    return {"success": True, "data": {"correct": exact, "state": state}, "message": message}


@router.get("/admin/station")
def station(account: EventAccount = Depends(require_roles(EventRole.ADMIN)), db: Session = Depends(get_db)):
    if not account.location_number:
        raise HTTPException(status_code=409, detail="This admin is not assigned to a location.")
    get_or_create_route_allocations(db)
    teams = []
    for allocation in db.query(Round1RouteAllocationModel).order_by(Round1RouteAllocationModel.team_identifier).all():
        active_checkpoint = checkpoint_for(allocation)
        for checkpoint in (1, 2, 3):
            location, question_set, attempts, complete = checkpoint_values(allocation, checkpoint)
            if location == account.location_number:
                attempt = latest_attempt(db, allocation, checkpoint)
                teams.append({"team_identifier": allocation.team_identifier, "team_name": allocation.team_name, "checkpoint": checkpoint, "set": question_set, "complete": complete, "attempts": attempts, "is_current": active_checkpoint == checkpoint and not complete, "scanned": has_scanned(db, allocation, checkpoint, location), "last_answer": attempt.submitted_answer if attempt else None, "last_answer_correct": attempt.is_correct if attempt else None})
    return {"success": True, "data": {"location": account.location_number, "location_name": R1_LOCATIONS[account.location_number]["name"], "teams": teams}, "message": "Station loaded."}


@router.get("/control/overview")
def overview(account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    get_or_create_route_allocations(db)
    config = event_config(db)
    teams = []
    for allocation in db.query(Round1RouteAllocationModel).order_by(Round1RouteAllocationModel.team_identifier).all():
        checkpoint = checkpoint_for(allocation)
        display_checkpoint = 3 if checkpoint == 4 else checkpoint
        attempt = latest_attempt(db, allocation, display_checkpoint)
        teams.append({"team_identifier": allocation.team_identifier, "team_name": allocation.team_name, "checkpoint": checkpoint, "complete": checkpoint == 4, "attempts": getattr(allocation, f"cp{display_checkpoint}_attempts", 0), "location": getattr(allocation, f"cp{checkpoint}_location", None) if checkpoint < 4 else None, "set": getattr(allocation, f"cp{display_checkpoint}_set"), "last_answer": attempt.submitted_answer if attempt else None, "last_answer_correct": attempt.is_correct if attempt else None})
    return {"success": True, "data": {"started": bool(config.started_at), "teams": teams, "instagram": "ASYMPTOTES_BMSIT"}, "message": "Control room loaded."}


@router.post("/control/start")
def start(account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    config = event_config(db)
    if not config.started_at:
        config.started_at = now()
        config.started_by = account.login_id
        db.commit()
    return {"success": True, "data": {"started": True}, "message": "Round 1 is live."}


@router.post("/control/override")
def override(payload: OverrideInput, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    if not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Super admin password confirmation failed.")
    allocation = db.query(Round1RouteAllocationModel).filter(Round1RouteAllocationModel.team_identifier == payload.team_identifier).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Team route not found.")
    checkpoint = checkpoint_for(allocation)
    if checkpoint == 4:
        raise HTTPException(status_code=409, detail="This team already completed Round 1.")
    if payload.action == "UNLOCK":
        setattr(allocation, f"cp{checkpoint}_attempts", 0)
    else:
        setattr(allocation, f"cp{checkpoint}_completed", True)
        setattr(allocation, f"cp{checkpoint}_completed_at", now())
    db.add(Round1Override(team_identifier=allocation.team_identifier, checkpoint_number=checkpoint, action=payload.action, reason=payload.reason, performed_by=account.id))
    db.commit()
    return {"success": True, "data": {"team_identifier": allocation.team_identifier, "action": payload.action}, "message": "Override recorded."}
