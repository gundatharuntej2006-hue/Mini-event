"""Small, mobile-first API surface for the live Treasure Hunt."""

import io
import re
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from time import monotonic
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_access_token, get_password_hash, verify_password
from app.core.constants import R1_LOCATIONS
from app.db.session import get_db
from app.models.event_account import EventAccount, EventRole, Round1FinishOutcome, Round1Override, Round1SecretAgentSelection
from app.models.round1 import GateCheckinModel, Round1CheckpointAttemptModel, Round1ConfigModel, Round1RouteAllocationModel
from app.models.team import Team, TeamStatus
from app.services.round1_service import get_or_create_route_allocations, reset_round1_live_state

router = APIRouter(prefix="/r1", tags=["Round 1 Live Event"])
bearer = HTTPBearer(auto_error=False)

EXACT_ANSWERS = {1: "ODD", 2: "42", 3: "ODD-42 / ODD 42"}
QUALIFIER_LIMIT = 16
BASE_POINTS = 400.0
LOGIN_WINDOW_SECONDS = 60
LOGIN_MAX_ATTEMPTS = 8
_login_attempts: dict[str, deque[float]] = defaultdict(deque)


class LoginInput(BaseModel):
    login_id: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=1, max_length=128)


class ScanInput(BaseModel):
    location: int = Field(ge=1, le=8)


class AnswerInput(BaseModel):
    answer: str = Field(min_length=1, max_length=255)


class OverrideInput(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    team_identifier: str
    action: Literal["UNLOCK", "MARK_CORRECT"]
    reason: str = Field(min_length=3, max_length=500)


class ResetInput(BaseModel):
    # The duplicate password and explicit confirmation make this irreversible action deliberate.
    password: str = Field(min_length=1, max_length=128)
    password_confirmation: str = Field(min_length=1, max_length=128)
    confirmed: bool
    reason: str = Field(min_length=3, max_length=500)


class SecretAgentInput(BaseModel):
    agent_name: str = Field(min_length=2, max_length=120)


class PasswordChangeInput(BaseModel):
    current_super_password: str = Field(min_length=1, max_length=128)
    target_login_id: str = Field(min_length=3, max_length=40)
    new_password: str = Field(min_length=8, max_length=128)
    new_password_confirmation: str = Field(min_length=8, max_length=128)
    reason: str = Field(min_length=3, max_length=500)


def now() -> datetime:
    return datetime.now(timezone.utc)


def answer_is_correct(checkpoint: int, submitted_answer: str) -> bool:
    """Round 1's deliberately simple, case-insensitive answer policy."""
    answer = submitted_answer.strip().upper()
    if checkpoint == 1:
        return answer == "ODD"
    if checkpoint == 2:
        return answer == "42"
    # The final code needs both fragments, separated by a dash or whitespace.
    return re.fullmatch(r"ODD(?:[-\s]+)42", answer) is not None


def guard_login_rate(login_id: str) -> None:
    """Small per-ID throttle that does not block many teams behind campus Wi-Fi."""
    attempts = _login_attempts[login_id.strip().upper()]
    cutoff = monotonic() - LOGIN_WINDOW_SECONDS
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    if len(attempts) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many sign-in attempts. Please wait one minute and try again.")
    attempts.append(monotonic())


def current_account(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> EventAccount:
    if not credentials:
        raise HTTPException(status_code=401, detail="Please sign in.")
    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Your session is invalid or expired.")
    account = db.query(EventAccount).filter(EventAccount.id == payload["sub"]).first()
    if not account:
        raise HTTPException(status_code=401, detail="Your account is not active.")
    if not account.is_active:
        if account.role == EventRole.PARTICIPANT:
            raise HTTPException(status_code=403, detail="Round 1 has ended for this team. Please see Instagram for results.")
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


def agent_selection(db: Session, account: EventAccount) -> Round1SecretAgentSelection | None:
    return db.query(Round1SecretAgentSelection).filter(Round1SecretAgentSelection.team_id == account.team_id).first()


def finish_outcome(db: Session, team_id: str | None) -> Round1FinishOutcome | None:
    if not team_id:
        return None
    return db.query(Round1FinishOutcome).filter(Round1FinishOutcome.team_id == team_id).first()


def outcome_data(outcome: Round1FinishOutcome | None) -> dict:
    if not outcome:
        return {"rank": None, "qualified": False, "completed_at": None}
    return {"rank": outcome.rank, "qualified": outcome.is_qualified, "completed_at": outcome.completed_at.isoformat()}


def record_finish(db: Session, allocation: Round1RouteAllocationModel) -> Round1FinishOutcome:
    """Serialize final submissions so exactly the first sixteen are qualified."""
    config = db.query(Round1ConfigModel).filter(Round1ConfigModel.id == 1).with_for_update().one()
    existing = finish_outcome(db, allocation.team_id)
    if existing:
        return existing

    rank = db.query(func.count(Round1FinishOutcome.id)).scalar() + 1
    team = db.query(Team).filter(Team.id == allocation.team_id).with_for_update().first()
    if not team:
        raise HTTPException(status_code=409, detail="Team roster record is missing.")
    qualified = rank <= QUALIFIER_LIMIT
    # Every team starts at 400; Round 1 finish position adds 140, 135 ... 65.
    round1_award = 140.0 - 5.0 * (rank - 1) if qualified else 0.0
    team.total_score = BASE_POINTS + round1_award
    outcome = Round1FinishOutcome(
        team_id=team.id,
        team_identifier=allocation.team_identifier,
        rank=rank,
        is_qualified=qualified,
        completed_at=getattr(allocation, "cp3_completed_at") or now(),
        points_snapshot=team.total_score,
    )
    db.add(outcome)
    team.is_qualified_for_next_round = qualified
    team.current_round = 2 if qualified else 1
    team.status = TeamStatus.ACTIVE if qualified else TeamStatus.ELIMINATED
    db.flush()

    # When the sixteenth team qualifies, remaining participant accounts lose access.
    if rank == QUALIFIER_LIMIT:
        qualified_ids = [item[0] for item in db.query(Round1FinishOutcome.team_id).filter(Round1FinishOutcome.is_qualified == True).all()]
        db.query(EventAccount).filter(
            EventAccount.role == EventRole.PARTICIPANT,
            ~EventAccount.team_id.in_(qualified_ids),
        ).update({EventAccount.is_active: False}, synchronize_session=False)
    return outcome


def seed_base_points(db: Session) -> None:
    for team in db.query(Team).all():
        team.total_score = BASE_POINTS
        team.is_qualified_for_next_round = False
        team.current_round = 1
        team.status = TeamStatus.ACTIVE


def participant_state(db: Session, account: EventAccount) -> dict:
    allocation = allocation_for_account(db, account)
    checkpoint = checkpoint_for(allocation)
    config = event_config(db)
    selection = agent_selection(db, account)
    if checkpoint == 4:
        return {"complete": True, "checkpoint": 4, "round_started": bool(config.started_at), "instagram": "ASYMPTOTES_BMSIT", "secret_agent_submitted": bool(selection), **outcome_data(finish_outcome(db, account.team_id))}
    location, _set, attempts, _completed = checkpoint_values(allocation, checkpoint)
    return {
        "complete": False,
        "checkpoint": checkpoint,
        "round_started": bool(config.started_at),
        "riddle": R1_LOCATIONS[location]["riddle"],
        "is_scanned": has_scanned(db, allocation, checkpoint, location),
        "attempts_used": attempts,
        "is_locked": attempts >= 3,
        "secret_agent_submitted": bool(selection),
        # Location name, question set, target, other teams and future clues are withheld.
    }


@router.post("/login")
def login(payload: LoginInput, request: Request, db: Session = Depends(get_db)):
    guard_login_rate(payload.login_id)
    account = db.query(EventAccount).filter(EventAccount.login_id == payload.login_id.strip().upper()).first()
    if not account or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect ID or password.")
    if not account.is_active:
        if account.role == EventRole.PARTICIPANT:
            return {"success": True, "data": {"redirect": "instagram"}, "message": "Round 1 has ended for this team. Please see Instagram for results."}
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect ID or password.")
    token = create_access_token(account.id, account.role.value)
    return {"success": True, "data": {"token": token, "role": account.role.value, "display_name": account.display_name}, "message": "Signed in."}


@router.get("/me")
def me(account: EventAccount = Depends(current_account)):
    return {"success": True, "data": {"role": account.role.value, "display_name": account.display_name, "location_number": account.location_number}, "message": "Account loaded."}


@router.get("/participant/state")
def get_participant_state(account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)), db: Session = Depends(get_db)):
    return {"success": True, "data": participant_state(db, account), "message": "Current event state loaded."}


@router.post("/participant/secret-agent")
def nominate_secret_agent(payload: SecretAgentInput, account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)), db: Session = Depends(get_db)):
    if agent_selection(db, account):
        raise HTTPException(status_code=409, detail="Your team has already submitted its Secret Agent name.")
    agent_name = payload.agent_name.strip()
    if len(agent_name) < 2:
        raise HTTPException(status_code=422, detail="Enter a valid Secret Agent name.")
    db.add(Round1SecretAgentSelection(team_id=account.team_id, agent_name=agent_name))
    db.commit()
    return {"success": True, "data": participant_state(db, account), "message": "Secret Agent recorded confidentially."}


@router.post("/participant/scan")
def scan(payload: ScanInput, account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)), db: Session = Depends(get_db)):
    config = event_config(db)
    if not config.started_at:
        raise HTTPException(status_code=409, detail="The round has not started yet.")
    if not agent_selection(db, account):
        raise HTTPException(status_code=409, detail="Choose your team's Secret Agent before starting the hunt.")
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
    if not agent_selection(db, account):
        raise HTTPException(status_code=409, detail="Choose your team's Secret Agent before submitting an answer.")
    allocation = allocation_for_account(db, account)
    checkpoint = checkpoint_for(allocation)
    if checkpoint == 4:
        raise HTTPException(status_code=409, detail="Your team has already completed Round 1.")
    location, question_set, attempts, _completed = checkpoint_values(allocation, checkpoint)
    if attempts >= 3:
        raise HTTPException(status_code=409, detail="This checkpoint is locked. Please contact a super admin.")
    if not has_scanned(db, allocation, checkpoint, location):
        raise HTTPException(status_code=403, detail="Scan your active location QR before entering an answer.")

    exact = answer_is_correct(checkpoint, payload.answer)
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
        if checkpoint == 3:
            db.flush()
            record_finish(db, allocation)
    db.commit()
    state = participant_state(db, account)
    message = "Correct. Your next clue is now available." if exact and checkpoint < 3 else "Your time has been recorded. Please check Instagram for results." if exact else "That answer was not accepted. Use the required code; capital letters do not matter."
    return {"success": True, "data": {"correct": exact, "state": state, "outcome": outcome_data(finish_outcome(db, account.team_id)) if exact and checkpoint == 3 else None}, "message": message}


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
        outcome = finish_outcome(db, allocation.team_id)
        selection = db.query(Round1SecretAgentSelection).filter(Round1SecretAgentSelection.team_id == allocation.team_id).first()
        team = db.query(Team).filter(Team.id == allocation.team_id).first()
        teams.append({"team_identifier": allocation.team_identifier, "team_name": allocation.team_name, "checkpoint": checkpoint, "complete": checkpoint == 4, "attempts": getattr(allocation, f"cp{display_checkpoint}_attempts", 0), "location": getattr(allocation, f"cp{checkpoint}_location", None) if checkpoint < 4 else None, "set": getattr(allocation, f"cp{display_checkpoint}_set"), "last_answer": attempt.submitted_answer if attempt else None, "last_answer_correct": attempt.is_correct if attempt else None, "points": team.total_score if team else 0, "secret_agent_name": selection.agent_name if selection else None, **outcome_data(outcome)})
    return {"success": True, "data": {"started": bool(config.started_at), "qualifier_limit": QUALIFIER_LIMIT, "qualified_count": db.query(func.count(Round1FinishOutcome.id)).filter(Round1FinishOutcome.is_qualified == True).scalar(), "teams": teams, "instagram": "ASYMPTOTES_BMSIT"}, "message": "Control room loaded."}


@router.get("/control/accounts")
def accounts(account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    """Password targets only; password hashes and values never leave the server."""
    items = db.query(EventAccount).order_by(EventAccount.role, EventAccount.login_id).all()
    return {"success": True, "data": [
        {"login_id": item.login_id, "display_name": item.display_name, "role": item.role.value, "is_active": item.is_active}
        for item in items
    ], "message": "Login accounts loaded."}


@router.post("/control/accounts/password")
def change_account_password(payload: PasswordChangeInput, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    """Super-admin-only password change with current-password confirmation and audit record."""
    if payload.new_password != payload.new_password_confirmation:
        raise HTTPException(status_code=400, detail="The two new password entries do not match.")
    if not verify_password(payload.current_super_password, account.password_hash):
        raise HTTPException(status_code=401, detail="Super admin password confirmation failed.")
    target = db.query(EventAccount).filter(EventAccount.login_id == payload.target_login_id.strip().upper()).first()
    if not target:
        raise HTTPException(status_code=404, detail="Login account not found.")
    target.password_hash = get_password_hash(payload.new_password)
    db.add(Round1Override(
        team_identifier=target.login_id,
        checkpoint_number=0,
        action="PASSWORD_CHANGE",
        reason=f"{payload.reason.strip()} (password value not logged)",
        performed_by=account.id,
    ))
    db.commit()
    return {"success": True, "data": {"login_id": target.login_id}, "message": f"Password updated for {target.login_id}."}


@router.post("/control/start")
def start(account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    config = event_config(db)
    if not config.started_at:
        seed_base_points(db)
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
        if checkpoint == 3:
            db.flush()
            record_finish(db, allocation)
    db.add(Round1Override(team_identifier=allocation.team_identifier, checkpoint_number=checkpoint, action=payload.action, reason=payload.reason, performed_by=account.id))
    db.commit()
    return {"success": True, "data": {"team_identifier": allocation.team_identifier, "action": payload.action}, "message": "Override recorded."}


@router.post("/control/reset")
def reset_round(payload: ResetInput, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    """Reset all Round 1 progress while preserving the roster, routes, and credentials."""
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Explicit reset confirmation is required.")
    if payload.password != payload.password_confirmation:
        raise HTTPException(status_code=400, detail="The two password entries do not match.")
    if not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Super admin password confirmation failed.")

    get_or_create_route_allocations(db)
    result = reset_round1_live_state(db, actor=account)
    db.query(Round1FinishOutcome).delete(synchronize_session=False)
    db.query(Round1SecretAgentSelection).delete(synchronize_session=False)
    seed_base_points(db)
    db.query(EventAccount).filter(EventAccount.role == EventRole.PARTICIPANT).update({EventAccount.is_active: True}, synchronize_session=False)
    # Keep a dedicated immutable record even though attempts/check-ins are cleared.
    db.add(Round1Override(
        team_identifier="ALL_TEAMS",
        checkpoint_number=0,
        action="RESET",
        reason=payload.reason,
        performed_by=account.id,
    ))
    db.commit()
    return {"success": True, "data": result, "message": "Round 1 has been reset. Teams, routes, and login accounts are preserved."}


@router.get("/control/report.pdf")
def download_report(account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    """Download an organizer-only verification report of every Round 1 submission."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    pdf.setTitle("ASYMPTOTES Round 1 verification report")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(36, height - 38, "ASYMPTOTES · Round 1 verification report")
    pdf.setFont("Helvetica", 8)
    pdf.drawString(36, height - 52, f"Generated {now().isoformat()} UTC · first {QUALIFIER_LIMIT} final submissions qualify")
    y = height - 76
    for allocation in db.query(Round1RouteAllocationModel).order_by(Round1RouteAllocationModel.team_identifier).all():
        outcome = finish_outcome(db, allocation.team_id)
        team = db.query(Team).filter(Team.id == allocation.team_id).first()
        selection = db.query(Round1SecretAgentSelection).filter(Round1SecretAgentSelection.team_id == allocation.team_id).first()
        if y < 54:
            pdf.showPage(); y = height - 42
        pdf.setFont("Helvetica-Bold", 9)
        finish = outcome.completed_at.isoformat() if outcome else "Not finished"
        rank = f"#{outcome.rank} {'QUALIFIED' if outcome.is_qualified else 'ELIMINATED'}" if outcome else "Pending"
        pdf.drawString(36, y, f"TEAM {allocation.team_identifier} · {allocation.team_name} · {rank} · finish: {finish} · points: {team.total_score if team else 0}")
        y -= 12
        pdf.setFont("Helvetica", 7)
        agent = selection.agent_name if selection else "Not submitted"
        pdf.drawString(50, y, f"Secret Agent: {agent}")
        y -= 10
        attempts = db.query(Round1CheckpointAttemptModel).filter(Round1CheckpointAttemptModel.team_id == allocation.team_id).order_by(Round1CheckpointAttemptModel.created_at).all()
        for attempt in attempts:
            if y < 42:
                pdf.showPage(); y = height - 42
            pdf.drawString(64, y, f"R1.{attempt.checkpoint_number} · L{attempt.location_number} · Set {attempt.question_set} · answer: {attempt.submitted_answer} · {'correct' if attempt.is_correct else 'incorrect'} · {attempt.created_at.isoformat()}")
            y -= 9
        y -= 5
    pdf.save()
    return Response(content=buffer.getvalue(), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=asymptotes-round1-verification.pdf"})
