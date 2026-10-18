"""Live, team-ID Round 3: simultaneous clue auction and dealer games.

This is deliberately separate from the legacy /rounds/round3 email-account API.
All balances, turns, queues, bids and results are enforced on the server.
"""

import json
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.routes.r1_event import current_account, require_roles
from app.core.security import get_password_hash, verify_password
from app.db.session import get_db
from app.models.event_account import EventAccount, EventRole
from app.models.participant import Participant
from app.models.round3_live import (
    Round3AuctionBid, Round3AuctionLot, Round3DealerTable, Round3GameAttempt,
    Round3LiveConfig, Round3LiveLedger, Round3LiveTeam, Round3TeamSession,
    Round3PuzzleUse, Round3QualificationRule, Round3QualifiedTeam,
)
from app.models.team import Team
from app.services.audit_service import log_audit_event
from app.services.round3_puzzles import PUZZLES, is_correct, public_payload, puzzle_by_key

router = APIRouter(prefix="/r3-live", tags=["Round 3 Live Market"])
# Organizer-published Day 2 field and the tie-adjusted R1 + Cabo + exercise
# totals in scripts/build_round2_bottom8_report.py. These are preview values;
# SUPER_ADMIN can correct each opening value before the 30-minute start.
QUALIFIERS = {
    2: 1315, 24: 1215, 16: 1130, 17: 1370, 32: 1180, 18: 1320,
    26: 1285, 9: 1180, 28: 1215, 29: 1200, 7: 1255, 12: 1175, 31: 1230,
}
PUBLISHED_BREAKDOWN = {
    2: (535, 780, 0), 24: (485, 730, 0), 16: (475, 655, 0),
    17: (505, 865, 0), 32: (540, 640, 0), 18: (515, 805, 0),
    26: (500, 785, 0), 9: (400, 780, 0), 28: (530, 685, 0),
    29: (510, 685, 5), 7: (525, 730, 0), 12: (490, 685, 0),
    31: (495, 730, 5),
}
GAME_SECONDS = 75
RESERVATION_SECONDS = 120
ROUND_SECONDS = 30 * 60
STATION_NAMES = (
    "Alibi Logic", "Pattern Decoder", "Wordplay Trap", "Spatial Scramble",
    "Deduction Desk", "Observation Vault", "Sequence Signal", "Quick-Thinking Lock",
)
MAX_ACTIVE_TEAM_ASSIGNMENTS = 2

# Confirmed Day 2 attendance roster. This changes participant display records
# only; team login IDs, password hashes, scores and account activation are not
# touched. A deployment before the round starts safely reconciles these names.
ROUND3_ROSTER_OVERRIDES = {
    24: ("Diganth Sairam Kothari", "D Venkatesh Kumar", "Anirudh CR", "Samarth Sudesh Shenoy"),
    17: ("Arnav Atul", "Ujjwal Kumar Gupta", "Kumar Satyam", "Ishan Verma", "Nalin Sharma"),
    7: ("Divyansh Mishra", "Namish Goyal", "Naman Kashyap", "Kartik Sahni", "Saanvi Pawar"),
    31: ("Kokil Reddy", "Vishwas Skandhan", "Shashank", "Sujan"),
    32: ("Varnit Gupta", "Parasmani", "Divyansh Kumar Singh", "Archit Kumar", "Ayush Kumar Yadav"),
    2: ("Sai Nikhil Meda", "Rohit Gudage", "G Avinash Reddy", "N Soha", "Risha S Rao"),
    26: ("Dinesh R", "Aditi Y A", "Trisha Kadur", "Varsha H V", "Purvi Reddy H"),
    18: ("D Mithun", "Rakshan M", "M S Pranay", "Harsha D Y", "Vaageesha Theertha"),
    16: ("Kavya Sahu", "J Benito Nathanael", "Pranav Rakshith M", "Kushishree Suresh", "Shreyaa N D"),
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def normalize_final_code(value: str) -> bool:
    """For the later legal-round gate only; not used to enter Round 3."""
    return re.sub(r"\s+", "", value).casefold() == "oddecho"


def _person_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def sync_round3_rosters(db: Session) -> None:
    """Reconcile confirmed attendees without changing any login credentials."""
    for team_number, desired_names in ROUND3_ROSTER_OVERRIDES.items():
        team = db.query(Team).filter(Team.team_number == team_number).first()
        if not team:
            continue
        current = db.query(Participant).filter(Participant.team_id == team.id).order_by(
            Participant.created_at, Participant.id
        ).all()
        unused = current[:]
        assignments: list[tuple[Participant, str]] = []
        for desired in desired_names:
            desired_key = _person_key(desired)
            match = next((person for person in unused if _person_key(person.name) == desired_key), None)
            if match is None:
                first = desired_key[:4]
                match = next((person for person in unused if _person_key(person.name).startswith(first)), None)
            if match is None and unused:
                match = unused[0]
            if match is None:
                # Current selected teams all have enough existing participant
                # records, but keep this path safe for a later roster addition.
                suffix = uuid.uuid4().hex[:10]
                match = Participant(
                    name=desired,
                    email=f"r3-{team_number}-{suffix}@event.local",
                    usn=f"R3-{team_number}-{suffix}",
                    team_id=team.id,
                )
                db.add(match)
            else:
                unused.remove(match)
            assignments.append((match, desired))
        for person, desired in assignments:
            person.name = desired
            person.team_id = team.id
        for person in unused:
            person.team_id = None


class OpeningPointsInput(BaseModel):
    team_identifier: str
    points: float = Field(ge=0, le=100000, allow_inf_nan=False)


class TableInput(BaseModel):
    game_name: str = Field(min_length=3, max_length=100)
    max_points: float = Field(gt=0, le=100, allow_inf_nan=False)
    is_enabled: bool = True
    room_number: int | None = Field(default=None, ge=1, le=9999)
    game_mode: Literal["ONLINE", "OFFLINE"] | None = None
    admin_login_id: str | None = None
    table_number: int | None = Field(default=None, ge=1, le=99)


class AdminInput(BaseModel):
    login_id: str = Field(pattern=r"^ADMIN[0-9]{2,3}$")
    display_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=72)


class DealerReassignmentInput(BaseModel):
    admin_login_id: str = Field(min_length=7, max_length=20)
    room_number: int = Field(ge=1, le=9999)


class BalanceAdjustmentInput(BaseModel):
    team_identifier: str
    delta: float = Field(allow_inf_nan=False, ge=-100000, le=100000)
    reason: str = Field(min_length=5, max_length=200)


class BalanceSetInput(BaseModel):
    team_identifier: str
    points: float = Field(ge=0, le=100000, allow_inf_nan=False)
    reason: str = Field(min_length=5, max_length=200)


class LotInput(BaseModel):
    opening_bid: float = Field(ge=0, le=100000, allow_inf_nan=False)
    description: str = Field(min_length=3, max_length=500)  # public teaser
    clue_text: str = Field(min_length=3, max_length=3000)  # winner-only case help


class SpinInput(BaseModel):
    participant_id: str


class ScoreInput(BaseModel):
    points: float = Field(ge=0, allow_inf_nan=False)
    note: str = Field(min_length=3, max_length=500)


class StationStartInput(BaseModel):
    access_code: str = Field(pattern=r"^[0-9]{3}$")


class StationAnswerInput(BaseModel):
    answer: str = Field(min_length=1, max_length=120)


class BidInput(BaseModel):
    amount: float = Field(gt=0, le=100000, allow_inf_nan=False)


class QualificationCountInput(BaseModel):
    qualifying_count: int = Field(ge=1, le=13)


class ResetInput(BaseModel):
    # Match the protected Round 1 reset flow: duplicate password plus a
    # separate explicit confirmation from the browser warning.
    password: str = Field(min_length=1, max_length=128)
    password_confirmation: str = Field(min_length=1, max_length=128)
    confirmed: bool
    reason: str = Field(min_length=3, max_length=500)


def config(db: Session) -> Round3LiveConfig:
    item = db.get(Round3LiveConfig, 1)
    if not item:
        item = Round3LiveConfig(id=1)
        db.add(item)
        db.flush()
    return item


def qualification_rule(db: Session) -> Round3QualificationRule:
    item = db.get(Round3QualificationRule, 1)
    if not item:
        item = Round3QualificationRule(id=1, qualifying_count=6)
        db.add(item)
        db.flush()
    return item


def is_open(cfg: Round3LiveConfig) -> bool:
    now = utcnow()
    return bool(cfg.starts_at and cfg.ends_at and as_utc(cfg.starts_at) <= now <= as_utc(cfg.ends_at) and cfg.closed_at is None)


def require_open(db: Session) -> Round3LiveConfig:
    cfg = config(db)
    if not is_open(cfg):
        raise HTTPException(409, "The auction and game window is not open.")
    return cfg


def eligible(db: Session, account: EventAccount) -> Round3LiveTeam:
    if account.role != EventRole.PARTICIPANT or not account.team_id:
        raise HTTPException(403, "Only a qualified team can use this screen.")
    row = db.get(Round3LiveTeam, account.team_id)
    if not row or not row.is_eligible:
        raise HTTPException(403, "This team is not in the thirteen-team Round 3 field.")
    cfg = config(db)
    session_id = getattr(account, "_event_jti", None)
    session = db.get(Round3TeamSession, session_id) if session_id else None
    if session_id and (not session or session.team_id != row.team_id or session.signed_out_at):
        raise HTTPException(401, "This device was signed out. Please sign in again.")
    if cfg.starts_at and not cfg.closed_at and not session:
        raise HTTPException(401, "Please sign in once to enter the live round.")
    if session:
        # A valid JWT remains usable for the whole event day. Touch the device
        # once per minute so the three-active-device admission check remains
        # accurate without turning every participant poll into a database write.
        current = utcnow()
        if as_utc(session.last_seen_at) < current - timedelta(minutes=1):
            session.last_seen_at = current
            db.commit()
    return row


def balance(db: Session, team: Round3LiveTeam) -> float:
    delta = db.query(func.coalesce(func.sum(Round3LiveLedger.delta), 0.0)).filter(Round3LiveLedger.team_id == team.team_id).scalar()
    return round(team.opening_points + float(delta or 0), 2)


def sync_team_total(db: Session, team_id: str) -> None:
    team = db.get(Team, team_id)
    snapshot = db.get(Round3LiveTeam, team_id)
    if team and snapshot:
        db.flush()
        team.total_score = balance(db, snapshot)


def held_bids(db: Session, team_id: str, except_lot: str | None = None) -> float:
    lots = db.query(Round3AuctionLot).filter(Round3AuctionLot.status == "LIVE").all()
    held = 0.0
    for lot in lots:
        if lot.id == except_lot:
            continue
        top = db.query(Round3AuctionBid).filter(Round3AuctionBid.lot_id == lot.id).order_by(
            Round3AuctionBid.amount.desc(), Round3AuctionBid.created_at, Round3AuctionBid.id
        ).first()
        if top and top.team_id == team_id:
            held += top.amount
    return held


def attempt_meta(attempt: Round3GameAttempt) -> dict:
    try:
        value = json.loads(attempt.outcome_note or "{}")
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}


def set_attempt_meta(attempt: Round3GameAttempt, **updates: object) -> dict:
    value = {**attempt_meta(attempt), **updates}
    attempt.outcome_note = json.dumps(value, separators=(",", ":"))
    return value


def team_payload(db: Session, row: Round3LiveTeam) -> dict:
    team = db.get(Team, row.team_id)
    published = PUBLISHED_BREAKDOWN.get(team.team_number) if team else None
    txs = db.query(Round3LiveLedger).filter(Round3LiveLedger.team_id == row.team_id).order_by(Round3LiveLedger.created_at.desc()).all()
    members = db.query(Participant).filter(Participant.team_id == row.team_id).order_by(Participant.name).all()
    attempts = db.query(Round3GameAttempt).filter(Round3GameAttempt.team_id == row.team_id).order_by(Round3GameAttempt.created_at.desc()).all()
    completed_attempts = [item for item in attempts if item.status == "COMPLETE"]
    active_attempts = [item for item in attempts if item.status in {"RESERVED", "ACTIVE"}]
    available = balance(db, row)
    active_devices = 0
    if config(db).starts_at:
        active_devices = db.query(Round3TeamSession).filter(
            Round3TeamSession.team_id == row.team_id,
            Round3TeamSession.signed_out_at.is_(None),
            Round3TeamSession.last_seen_at >= utcnow() - timedelta(minutes=3),
        ).count()
    return {
        "team_identifier": f"TEAM{1000 + team.team_number}" if team else "Unknown",
        "team_name": team.name if team else "Unknown",
        "opening_points": row.opening_points,
        "opening_breakdown": ({"treasure_hunt": published[0], "cabo": published[1], "exercise": published[2],
                               "organizer_correction": row.opening_points - sum(published)} if published else None),
        "balance": available,
        "available_to_bid": round(available - held_bids(db, row.team_id), 2),
        "members": [{"id": person.id, "name": person.name,
                     "games_completed": sum(1 for item in completed_attempts if item.participant_id == person.id),
                     "played": any(item.participant_id == person.id for item in completed_attempts)} for person in members],
        "ledger": [{"delta": tx.delta, "category": tx.category, "description": tx.description, "at": as_utc(tx.created_at).isoformat()} for tx in txs],
        "attempt": attempt_payload(db, active_attempts[0], reveal_access=True) if active_attempts else None,
        "attempts": [attempt_payload(db, item, reveal_access=True) for item in active_attempts],
        "games_completed": len(completed_attempts),
        "active_devices": active_devices,
    }


def attempt_payload(db: Session, attempt: Round3GameAttempt, *, reveal_access: bool = False, reveal_puzzle: bool = False) -> dict:
    table = db.get(Round3DealerTable, attempt.table_number)
    meta = attempt_meta(attempt)
    payload = {
        "id": attempt.id, "table_number": attempt.table_number,
        "room_number": table.room_number if table else None,
        "game_name": table.game_name if table else "Game",
        "game_mode": table.game_mode if table else None,
        "status": attempt.status,
        "queue_position": None,
        "participant_id": attempt.participant_id,
        "participant_name": db.get(Participant, attempt.participant_id).name if db.get(Participant, attempt.participant_id) else "Unknown",
        "reserved_until": as_utc(attempt.reserved_until).isoformat() if attempt.reserved_until else None,
        "started_at": as_utc(attempt.started_at).isoformat() if attempt.started_at else None,
        "spun_at": as_utc(attempt.created_at).isoformat() if attempt.created_at else None,
        "queued_at": as_utc(attempt.queued_at).isoformat() if attempt.queued_at else None,
        "points": attempt.points,
        "correct": meta.get("correct"),
        "access_code_revealed": bool(meta.get("code_revealed_at")),
    }
    if reveal_access and attempt.status == "RESERVED" and meta.get("code_revealed_at"):
        payload["access_code"] = meta.get("access_code")
    if reveal_puzzle and attempt.status == "ACTIVE" and meta.get("puzzle_key"):
        try:
            payload["puzzle"] = public_payload(puzzle_by_key(str(meta["puzzle_key"])))
        except KeyError:
            payload["puzzle"] = None
    return payload


def record_automated_result(db: Session, attempt: Round3GameAttempt, table: Round3DealerTable, correct: bool, reason: str) -> None:
    awarded = float(table.max_points) if correct else 0.0
    attempt.status, attempt.points, attempt.ended_at = "COMPLETE", awarded, utcnow()
    set_attempt_meta(attempt, correct=correct, result=reason)
    existing = db.query(Round3LiveLedger).filter(Round3LiveLedger.reference_id == attempt.id).first()
    if not existing:
        db.add(Round3LiveLedger(
            team_id=attempt.team_id,
            delta=awarded,
            category="PUZZLE",
            description=f"Table {table.table_number}: {table.game_name} — {reason}",
            reference_id=attempt.id,
        ))
    sync_team_total(db, attempt.team_id)


def expire_and_promote(db: Session, table: Round3DealerTable) -> None:
    """Expire abandoned reservations and finish timed-out puzzles safely."""
    now = utcnow()
    current = db.query(Round3GameAttempt).filter(
        Round3GameAttempt.table_number == table.table_number,
        Round3GameAttempt.status.in_(["RESERVED", "ACTIVE"]),
    ).order_by(Round3GameAttempt.created_at).all()
    for attempt in current:
        if attempt.status == "RESERVED" and attempt.reserved_until and as_utc(attempt.reserved_until) < now:
            attempt.status, attempt.ended_at = "EXPIRED", now
        elif attempt.status == "ACTIVE" and attempt.started_at and as_utc(attempt.started_at) + timedelta(seconds=GAME_SECONDS) < now:
            record_automated_result(db, attempt, table, False, "Time expired — 0 points")
    # A game started by the deadline retains its full 75 seconds. No new
    # reservation may be promoted after the bidding/game window closes.
    if not is_open(config(db)):
        db.query(Round3GameAttempt).filter(
            Round3GameAttempt.table_number == table.table_number,
            Round3GameAttempt.status == "RESERVED",
        ).update({Round3GameAttempt.status: "EXPIRED", Round3GameAttempt.ended_at: now}, synchronize_session=False)
        db.flush()
        return
    db.flush()
    db.flush()


def lot_payload(db: Session, lot: Round3AuctionLot, team_id: str | None = None) -> dict:
    top = db.query(Round3AuctionBid).filter(Round3AuctionBid.lot_id == lot.id).order_by(
        Round3AuctionBid.amount.desc(), Round3AuctionBid.created_at, Round3AuctionBid.id,
    ).first()
    return {
        "id": lot.id, "level": lot.level, "token_number": lot.token_number,
        "title": lot.title, "description": lot.description, "status": lot.status,
        "clue_text": lot.clue_text if team_id is None or (lot.status == "CLOSED" and lot.winner_team_id == team_id) else None,
        "opening_bid": lot.opening_bid, "highest_bid": top.amount if top else None,
        "you_are_highest": bool(top and team_id and top.team_id == team_id),
        "winner_team_id": lot.winner_team_id if not team_id else None,
        "winning_bid": lot.winning_bid,
    }


def ensure_setup(db: Session) -> None:
    if db.query(Round3LiveTeam).count():
        # Upgrade an earlier, unstarted preview setup in place. Production data
        # is never rewritten after the round has started.
        if not config(db).starts_at:
            sync_round3_rosters(db)
            for table in db.query(Round3DealerTable).order_by(Round3DealerTable.table_number).all():
                table.game_mode = "ONLINE"
                if "awaiting organizer choice" in table.game_name.casefold():
                    table.game_name = STATION_NAMES[(table.table_number - 1) % len(STATION_NAMES)]
                if 1 <= table.table_number <= 8:
                    expected = db.query(EventAccount).filter(
                        EventAccount.login_id == f"ADMIN{table.table_number:02d}",
                        EventAccount.role == EventRole.ADMIN,
                        EventAccount.is_active.is_(True),
                    ).first()
                    if expected:
                        table.admin_id = expected.id
            qualification_rule(db)
            db.commit()
        return
    for team_number, score in QUALIFIERS.items():
        team = db.query(Team).filter(Team.team_number == team_number).first()
        if not team:
            raise HTTPException(409, f"TEAM{1000 + team_number} is missing from the roster.")
        db.add(Round3LiveTeam(team_id=team.id, opening_points=score))
    admins = []
    for number in range(1, 9):
        admin = db.query(EventAccount).filter(
            EventAccount.login_id == f"ADMIN{number:02d}",
            EventAccount.role == EventRole.ADMIN,
            EventAccount.is_active.is_(True),
        ).first()
        if not admin:
            raise HTTPException(409, f"ADMIN{number:02d} must be active for Table {number}.")
        admins.append(admin)
    for number in range(1, 9):
        db.add(Round3DealerTable(
            table_number=number, room_number=100 + number,
            game_mode="ONLINE",
            game_name=STATION_NAMES[number - 1],
            admin_id=admins[number - 1].id if len(admins) >= number else None,
            is_enabled=False,
            max_points=50,
        ))
    for level, count in ((1, 3), (2, 2)):
        for number in range(1, count + 1):
            db.add(Round3AuctionLot(level=level, token_number=number, title=f"Level {level} clue token {number}", description="Case clue details pending organizer approval.", opening_bid=0))
    qualification_rule(db)
    sync_round3_rosters(db)
    db.commit()


@router.get("/control/overview")
def control_overview(account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    ensure_setup(db)
    cfg = config(db)
    rows = db.query(Round3LiveTeam, Team).join(Team, Team.id == Round3LiveTeam.team_id).order_by(Team.team_number).all()
    tables = db.query(Round3DealerTable).order_by(Round3DealerTable.table_number).all()
    lots = db.query(Round3AuctionLot).order_by(Round3AuctionLot.level, Round3AuctionLot.token_number).all()
    rule = qualification_rule(db)
    ledger_totals = {
        team_id: float(total or 0)
        for team_id, total in db.query(
            Round3LiveLedger.team_id, func.sum(Round3LiveLedger.delta)
        ).group_by(Round3LiveLedger.team_id).all()
    }
    balances = {
        row.team_id: round(float(row.opening_points) + ledger_totals.get(row.team_id, 0), 2)
        for row, _team in rows
    }
    member_counts = {
        team_id: count
        for team_id, count in db.query(Participant.team_id, func.count(Participant.id))
        .filter(Participant.team_id.in_([row.team_id for row, _team in rows]))
        .group_by(Participant.team_id).all()
    }
    played_counts = {
        team_id: count
        for team_id, count in db.query(
            Round3GameAttempt.team_id,
            func.count(func.distinct(Round3GameAttempt.participant_id)),
        ).filter(Round3GameAttempt.status == "COMPLETE")
        .group_by(Round3GameAttempt.team_id).all()
    }
    admins_by_id = {
        admin.id: admin
        for admin in db.query(EventAccount).filter(EventAccount.role == EventRole.ADMIN).all()
    }
    ranked = sorted(rows, key=lambda item: (-balances[item[0].team_id], item[1].name.casefold(), item[1].team_number))
    qualified_ids = {item.team_id for item in db.query(Round3QualifiedTeam).all()}
    cutoff_tie = bool(
        rule.qualifying_count < len(ranked)
        and balances[ranked[rule.qualifying_count - 1][0].team_id] == balances[ranked[rule.qualifying_count][0].team_id]
    )
    rank_by_team = {row.team_id: index + 1 for index, (row, _team) in enumerate(ranked)}
    return {"success": True, "data": {
        "started": bool(cfg.starts_at), "open": is_open(cfg), "closed": bool(cfg.closed_at), "starts_at": as_utc(cfg.starts_at).isoformat() if cfg.starts_at else None,
        "ends_at": as_utc(cfg.ends_at).isoformat() if cfg.ends_at else None,
        "teams": [{
            "team_identifier": f"TEAM{1000 + team.team_number}", "team_name": team.name,
            "opening_points": row.opening_points, "balance": balances[row.team_id],
            "members": member_counts.get(team.id, 0),
            "played": played_counts.get(team.id, 0),
            "rank": rank_by_team[row.team_id],
            "projected_qualified": rank_by_team[row.team_id] <= rule.qualifying_count,
            "qualified": row.team_id in qualified_ids,
        } for row, team in rows],
        "tables": [{"number": t.table_number, "room": t.room_number, "mode": t.game_mode, "game_name": t.game_name, "max_points": t.max_points, "enabled": t.is_enabled,
                    "admin": admins_by_id[t.admin_id].login_id if t.admin_id in admins_by_id else None} for t in tables],
        "admins": [{"login_id": admin.login_id, "display_name": admin.display_name, "is_active": admin.is_active}
                   for admin in db.query(EventAccount).filter(EventAccount.role == EventRole.ADMIN).order_by(EventAccount.login_id).all()],
        "lots": [lot_payload(db, lot) for lot in lots],
        "qualification": {
            "count": rule.qualifying_count,
            "finalized": bool(rule.finalized_at),
            "finalized_at": as_utc(rule.finalized_at).isoformat() if rule.finalized_at else None,
            "cutoff_tie": cutoff_tie,
            "qualified_team_ids": [
                f"TEAM{1000 + team.team_number}" for team in
                db.query(Team).join(Round3QualifiedTeam, Round3QualifiedTeam.team_id == Team.id)
                .order_by(Round3QualifiedTeam.rank).all()
            ],
        },
        "questions": {
            "total": sum(len(items) for items in PUZZLES.values()),
            "used": db.query(Round3PuzzleUse).count(),
        },
    }, "message": "Round 3 control loaded."}


@router.post("/control/qualification-count")
def set_qualification_count(payload: QualificationCountInput, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    ensure_setup(db)
    rule = db.query(Round3QualificationRule).filter(Round3QualificationRule.id == 1).with_for_update().one()
    if rule.finalized_at:
        raise HTTPException(409, "Round 3 qualifiers are already locked.")
    if payload.qualifying_count > db.query(Round3LiveTeam).count():
        raise HTTPException(409, "Qualification count cannot exceed the active Round 3 field.")
    rule.qualifying_count = payload.qualifying_count
    db.commit()
    return {"success": True, "data": {"qualifying_count": rule.qualifying_count}, "message": "Round 4 qualification count saved."}


@router.post("/control/qualifications/finalize")
def finalize_qualifications(account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    cfg = config(db)
    if not cfg.closed_at:
        raise HTTPException(409, "Close Round 3 before locking the Round 4 qualifiers.")
    if db.query(Round3GameAttempt).filter(Round3GameAttempt.status.in_(["RESERVED", "ACTIVE"])).count():
        raise HTTPException(409, "Wait for every reserved or active station attempt to finish or expire.")
    rule = db.query(Round3QualificationRule).filter(Round3QualificationRule.id == 1).with_for_update().one()
    if rule.finalized_at:
        raise HTTPException(409, "Round 3 qualifiers are already locked.")
    rows = db.query(Round3LiveTeam, Team).join(Team, Team.id == Round3LiveTeam.team_id).all()
    ranked = sorted(rows, key=lambda item: (-balance(db, item[0]), item[1].name.casefold(), item[1].team_number))
    if rule.qualifying_count < len(ranked) and balance(db, ranked[rule.qualifying_count - 1][0]) == balance(db, ranked[rule.qualifying_count][0]):
        raise HTTPException(409, "The qualification cutoff is tied. Apply an audited decision or change the qualifying count before locking.")
    db.query(Round3QualifiedTeam).delete(synchronize_session=False)
    for _row, team in rows:
        team.is_qualified_for_next_round = False
    for index, (row, team) in enumerate(ranked[:rule.qualifying_count], start=1):
        db.add(Round3QualifiedTeam(team_id=row.team_id, rank=index, points_snapshot=balance(db, row)))
        team.is_qualified_for_next_round = True
    rule.finalized_at, rule.finalized_by = utcnow(), account.id
    db.commit()
    return {"success": True, "data": {"qualified": rule.qualifying_count}, "message": "Round 4 qualifiers locked from the final Round 3 standings."}


@router.post("/control/teams/opening-points")
def set_opening_points(payload: OpeningPointsInput, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    ensure_setup(db)
    if config(db).starts_at:
        raise HTTPException(409, "Opening points are locked after Round 3 starts.")
    number_text = payload.team_identifier.strip().upper().removeprefix("TEAM")
    if not number_text.isdigit():
        raise HTTPException(422, "Use a TEAM number, for example TEAM1017.")
    team = db.query(Team).filter(Team.team_number == int(number_text) - 1000).first()
    row = db.get(Round3LiveTeam, team.id) if team else None
    if not row:
        raise HTTPException(404, "This is not one of the thirteen selected teams.")
    row.opening_points = payload.points
    team.total_score = payload.points
    db.commit()
    return {"success": True, "data": {"team_identifier": payload.team_identifier, "opening_points": row.opening_points}, "message": "Opening points updated before the round starts."}


@router.post("/control/teams/adjust")
def adjust_team_balance(payload: BalanceAdjustmentInput, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    ensure_setup(db)
    cfg = config(db)
    if not cfg.starts_at or cfg.closed_at:
        raise HTTPException(409, "Balance corrections are available only while Round 3 is running or settling.")
    identifier = payload.team_identifier.strip().upper()
    team = db.query(Team).filter(Team.team_number == int(identifier.removeprefix("TEAM")) - 1000).first() if identifier.removeprefix("TEAM").isdigit() else None
    row = db.get(Round3LiveTeam, team.id) if team else None
    if not row:
        raise HTTPException(404, "This is not one of the thirteen selected teams.")
    db.query(Round3LiveTeam).filter(Round3LiveTeam.team_id == row.team_id).with_for_update().one()
    if payload.delta == 0 or balance(db, row) + payload.delta < held_bids(db, row.team_id):
        raise HTTPException(409, "Adjustment must be non-zero and cannot spend points held in leading bids.")
    tx = Round3LiveLedger(team_id=row.team_id, delta=payload.delta, category="ADMIN_CORRECTION",
                          description=f"Organizer correction: {payload.reason.strip()}", reference_id=f"correction-{uuid.uuid4().hex}")
    db.add(tx)
    sync_team_total(db, row.team_id)
    db.commit()
    return {"success": True, "data": {"balance": balance(db, row)}, "message": "Audited team balance correction saved."}


@router.post("/control/teams/set-balance")
def set_team_balance(payload: BalanceSetInput, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    """Set an exact team total while retaining an auditable correction ledger."""
    ensure_setup(db)
    rule = qualification_rule(db)
    if rule.finalized_at:
        raise HTTPException(409, "Points are locked after Round 4 qualifiers are finalized.")
    identifier = payload.team_identifier.strip().upper()
    number_text = identifier.removeprefix("TEAM")
    team = db.query(Team).filter(Team.team_number == int(number_text) - 1000).first() if number_text.isdigit() else None
    row = db.get(Round3LiveTeam, team.id) if team else None
    if not row:
        raise HTTPException(404, "This is not one of the thirteen selected teams.")
    db.query(Round3LiveTeam).filter(Round3LiveTeam.team_id == row.team_id).with_for_update().one()
    cfg = config(db)
    if not cfg.starts_at:
        row.opening_points = payload.points
        team.total_score = payload.points
        db.commit()
        return {"success": True, "data": {"balance": payload.points}, "message": "Exact opening total saved."}
    current = balance(db, row)
    delta = round(payload.points - current, 2)
    if payload.points < held_bids(db, row.team_id):
        raise HTTPException(409, "The new total cannot be lower than points held in leading bids.")
    if delta:
        db.add(Round3LiveLedger(
            team_id=row.team_id,
            delta=delta,
            category="ADMIN_CORRECTION",
            description=f"Organizer set exact total to {payload.points:g}: {payload.reason.strip()}",
            reference_id=f"set-balance-{uuid.uuid4().hex}",
        ))
        sync_team_total(db, row.team_id)
    db.commit()
    return {"success": True, "data": {"balance": balance(db, row)}, "message": "Exact team total saved with an audit entry."}


@router.get("/control/teams/{team_identifier}")
def control_team_detail(team_identifier: str, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    number_text = team_identifier.strip().upper().removeprefix("TEAM")
    if not number_text.isdigit():
        raise HTTPException(422, "Use a TEAM number.")
    team = db.query(Team).filter(Team.team_number == int(number_text) - 1000).first()
    row = db.get(Round3LiveTeam, team.id) if team else None
    if not row:
        raise HTTPException(404, "This is not a selected team.")
    return {"success": True, "data": team_payload(db, row), "message": "Private team ledger loaded."}


@router.post("/control/tables/{number}")
def set_table(number: int, payload: TableInput, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    ensure_setup(db)
    table = db.get(Round3DealerTable, number)
    if not table:
        raise HTTPException(404, "Table not found.")
    if config(db).starts_at:
        raise HTTPException(409, "Game configuration is locked after opening.")
    if 1 <= number <= 8 and payload.table_number not in (None, number):
        raise HTTPException(409, "Round 3 table numbers 1-8 are fixed to ADMIN01-ADMIN08.")
    if payload.admin_login_id is not None:
        if 1 <= number <= 8 and payload.admin_login_id.strip().upper() != f"ADMIN{number:02d}":
            raise HTTPException(409, f"Table {number} is fixed to ADMIN{number:02d} during normal setup.")
        admin = db.query(EventAccount).filter(EventAccount.login_id == payload.admin_login_id.strip().upper(),
                                              EventAccount.role == EventRole.ADMIN, EventAccount.is_active.is_(True)).first()
        if not admin:
            raise HTTPException(422, "Select an active admin account.")
        assigned = db.query(Round3DealerTable).filter(Round3DealerTable.admin_id == admin.id,
                                                       Round3DealerTable.table_number != number).first()
        if assigned:
            raise HTTPException(409, f"{admin.login_id} is already assigned to table {assigned.table_number}.")
        table.admin_id = admin.id
    if payload.table_number is not None and payload.table_number != number:
        if db.get(Round3DealerTable, payload.table_number):
            raise HTTPException(409, "That table number is already in use.")
        table.table_number = payload.table_number
    if payload.room_number is not None:
        table.room_number = payload.room_number
    if payload.game_mode is not None:
        table.game_mode = payload.game_mode
    table.game_name, table.max_points, table.is_enabled = payload.game_name.strip(), payload.max_points, payload.is_enabled
    db.commit()
    return {"success": True, "data": {"number": table.table_number}, "message": "Dealer game and station assignment saved."}


@router.post("/control/admins")
def create_dealer_admin(payload: AdminInput, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    ensure_setup(db)
    login_id = payload.login_id.strip().upper()
    if db.query(EventAccount).filter(EventAccount.login_id == login_id).first():
        raise HTTPException(409, "This admin ID already exists.")
    dealer = EventAccount(login_id=login_id, display_name=payload.display_name.strip(),
                          password_hash=get_password_hash(payload.password), role=EventRole.ADMIN)
    db.add(dealer)
    db.commit()
    return {"success": True, "data": {"login_id": login_id}, "message": "Dealer admin created. Assign them to a table to activate their station."}


@router.get("/control/puzzle-bank")
def puzzle_bank(account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN))):
    """Private organiser review of the complete bank, including accepted answers."""
    tables = []
    for table_number, puzzles in PUZZLES.items():
        tables.append({
            "table_number": table_number,
            "station_name": STATION_NAMES[table_number - 1],
            "count": len(puzzles),
            "puzzles": [
                {
                    **public_payload(puzzle),
                    "answers": list(puzzle.answers),
                }
                for puzzle in puzzles
            ],
        })
    return {
        "success": True,
        "data": {"total": sum(item["count"] for item in tables), "game_seconds": GAME_SECONDS, "tables": tables},
        "message": "Private puzzle bank loaded.",
    }


@router.post("/control/tables/{number}/dealer")
def reassign_dealer(number: int, payload: DealerReassignmentInput, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    ensure_setup(db)
    table = db.query(Round3DealerTable).filter(Round3DealerTable.table_number == number).with_for_update().first()
    if not table:
        raise HTTPException(404, "Table not found.")
    admin = db.query(EventAccount).filter(EventAccount.login_id == payload.admin_login_id.strip().upper(),
                                          EventAccount.role == EventRole.ADMIN, EventAccount.is_active.is_(True)).first()
    if not admin:
        raise HTTPException(422, "Select an active dealer admin.")
    assigned = db.query(Round3DealerTable).filter(Round3DealerTable.admin_id == admin.id,
                                                   Round3DealerTable.table_number != number).first()
    if assigned:
        raise HTTPException(409, f"{admin.login_id} is already assigned to table {assigned.table_number}.")
    table.admin_id, table.room_number = admin.id, payload.room_number
    db.commit()
    return {"success": True, "data": {"number": number, "admin": admin.login_id, "room": payload.room_number},
            "message": "Dealer assignment updated; both admin screens refresh automatically."}


@router.post("/control/start")
def start(account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    ensure_setup(db)
    cfg = config(db)
    if cfg.starts_at:
        raise HTTPException(409, "Round 3 has already started; do not start it twice.")
    if db.query(Round3DealerTable).filter(Round3DealerTable.is_enabled.is_(True)).count() != 8:
        raise HTTPException(409, "Configure and enable all eight puzzle laptops before starting.")
    if db.query(Round3DealerTable).filter(Round3DealerTable.admin_id.is_(None)).count():
        raise HTTPException(409, "Assign one station account to every puzzle laptop before starting.")
    if db.query(Round3LiveTeam).count() != 13:
        raise HTTPException(409, "Exactly thirteen qualified teams are required.")
    for number in range(1, 9):
        table = db.get(Round3DealerTable, number)
        expected = db.query(EventAccount).filter(EventAccount.login_id == f"ADMIN{number:02d}").first()
        if not table or not expected or table.admin_id != expected.id:
            raise HTTPException(409, f"Table {number} must be assigned to ADMIN{number:02d} before starting.")
    cfg.starts_at = utcnow()
    cfg.ends_at = cfg.starts_at + timedelta(seconds=ROUND_SECONDS)
    for row in db.query(Round3LiveTeam).all():
        sync_team_total(db, row.team_id)
    db.commit()
    return {"success": True, "data": {"ends_at": as_utc(cfg.ends_at).isoformat()}, "message": "The 30-minute auction and games window is open."}


@router.post("/control/close")
def close_round(account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    cfg = config(db)
    if not cfg.starts_at or cfg.closed_at:
        raise HTTPException(409, "Round 3 is not open or is already closed.")
    if db.query(Round3AuctionLot).filter(Round3AuctionLot.status == "LIVE").count():
        raise HTTPException(409, "Close all live auction lots first so winning bids are recorded.")
    cfg.closed_at = utcnow()
    db.flush()
    for table in db.query(Round3DealerTable).all():
        expire_and_promote(db, table)
    db.commit()
    return {"success": True, "data": {"closed": True}, "message": "Round 3 closed; standings remain private to super admins."}


@router.post("/control/reset")
def reset_round(payload: ResetInput, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    """Return Round 3 to setup while preserving its roster and configuration."""
    if not payload.confirmed:
        raise HTTPException(400, "Explicit reset confirmation is required.")
    if payload.password != payload.password_confirmation:
        raise HTTPException(400, "The two password entries do not match.")
    if not verify_password(payload.password, account.password_hash):
        raise HTTPException(401, "Super admin password confirmation failed.")

    ensure_setup(db)
    cfg = db.query(Round3LiveConfig).filter(Round3LiveConfig.id == 1).with_for_update().one()
    counts = {
        "attempts": db.query(Round3GameAttempt).count(),
        "puzzles": db.query(Round3PuzzleUse).count(),
        "bids": db.query(Round3AuctionBid).count(),
        "ledger_entries": db.query(Round3LiveLedger).count(),
        "sessions": db.query(Round3TeamSession).count(),
        "qualifiers": db.query(Round3QualifiedTeam).count(),
    }

    # Delete dependent rows before attempts/lots so PostgreSQL foreign keys
    # remain satisfied. Static questions, selected teams and station setup stay.
    db.query(Round3PuzzleUse).delete(synchronize_session=False)
    db.query(Round3AuctionBid).delete(synchronize_session=False)
    db.query(Round3LiveLedger).delete(synchronize_session=False)
    db.query(Round3GameAttempt).delete(synchronize_session=False)
    db.query(Round3TeamSession).delete(synchronize_session=False)
    db.query(Round3QualifiedTeam).delete(synchronize_session=False)

    for lot in db.query(Round3AuctionLot).all():
        lot.status = "DRAFT"
        lot.opened_at = None
        lot.closed_at = None
        lot.winner_team_id = None
        lot.winning_bid = None

    rule = qualification_rule(db)
    rule.finalized_at = None
    rule.finalized_by = None
    cfg.starts_at = None
    cfg.ends_at = None
    cfg.closed_at = None

    # Round 3 owns the live total after it starts. Restore every selected team
    # to its verified opening balance and keep it eligible for this round.
    for snapshot in db.query(Round3LiveTeam).all():
        team = db.get(Team, snapshot.team_id)
        if team:
            team.total_score = snapshot.opening_points
            team.is_qualified_for_next_round = True

    log_audit_event(
        db,
        action="ROUND3_RESET_TO_SETUP",
        round_number=3,
        entity_type="round3_live",
        entity_id="ALL_TEAMS",
        actor_id=account.id,
        actor_role=account.role,
        details={"reason": payload.reason.strip(), "cleared": counts},
    )
    db.commit()
    return {
        "success": True,
        "data": {"started": False, "cleared": counts},
        "message": "Round 3 has been reset. Teams, opening points, station assignments, room numbers and auction clue configuration are preserved.",
    }


@router.post("/control/lots/{lot_id}/configure")
def configure_lot(lot_id: str, payload: LotInput, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    lot = db.get(Round3AuctionLot, lot_id)
    if not lot or lot.status != "DRAFT":
        raise HTTPException(409, "Only a draft clue lot can be configured.")
    lot.opening_bid, lot.description, lot.clue_text = payload.opening_bid, payload.description.strip(), payload.clue_text.strip()
    db.commit()
    return {"success": True, "data": lot_payload(db, lot), "message": "Clue lot saved."}


@router.post("/control/lots/{lot_id}/open")
def open_lot(lot_id: str, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    require_open(db)
    lot = db.get(Round3AuctionLot, lot_id)
    if not lot or lot.status != "DRAFT":
        raise HTTPException(409, "This clue lot cannot be opened.")
    if not lot.description or not lot.clue_text or "pending organizer" in lot.description.lower():
        raise HTTPException(409, "Add a public teaser and the winner-only case clue before opening this lot.")
    lot.status, lot.opened_at = "LIVE", utcnow()
    db.commit()
    return {"success": True, "data": lot_payload(db, lot), "message": "Clue lot is live."}


@router.post("/control/lots/{lot_id}/close")
def close_lot(lot_id: str, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    # One row serializes all bid/settlement operations and prevents double spending.
    db.query(Round3LiveConfig).filter(Round3LiveConfig.id == 1).with_for_update().one()
    lot = db.get(Round3AuctionLot, lot_id)
    if not lot or lot.status != "LIVE":
        raise HTTPException(409, "This clue lot is not live.")
    winner = db.query(Round3AuctionBid).filter(Round3AuctionBid.lot_id == lot_id).order_by(
        Round3AuctionBid.amount.desc(), Round3AuctionBid.created_at, Round3AuctionBid.id,
    ).first()
    lot.status, lot.closed_at = "CLOSED", utcnow()
    if winner:
        team = db.get(Round3LiveTeam, winner.team_id)
        if balance(db, team) < winner.amount:
            raise HTTPException(409, "Winning team lacks the required balance; contact a super admin.")
        lot.winner_team_id, lot.winning_bid = winner.team_id, winner.amount
        db.add(Round3LiveLedger(team_id=winner.team_id, delta=-winner.amount, category="AUCTION", description=f"Won {lot.title}", reference_id=lot.id))
        sync_team_total(db, winner.team_id)
    db.commit()
    return {"success": True, "data": lot_payload(db, lot), "message": "Auction lot settled."}


@router.get("/participant/state")
def participant_state(account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)), db: Session = Depends(get_db)):
    row = eligible(db, account)
    cfg = config(db)
    # Refresh every active assignment held by this team. A timed-out attempt is
    # completed as a loss here even if nobody is watching the station laptop.
    current = db.query(Round3GameAttempt).filter(
        Round3GameAttempt.team_id == row.team_id,
        Round3GameAttempt.status.in_(["RESERVED", "ACTIVE"]),
    ).all()
    for item in current:
        table = db.query(Round3DealerTable).filter(Round3DealerTable.table_number == item.table_number).with_for_update().one()
        expire_and_promote(db, table)
    db.commit()
    lots = db.query(Round3AuctionLot).order_by(Round3AuctionLot.level, Round3AuctionLot.token_number).all()
    return {"success": True, "data": {
        "open": is_open(cfg), "starts_at": as_utc(cfg.starts_at).isoformat() if cfg.starts_at else None,
        "ends_at": as_utc(cfg.ends_at).isoformat() if cfg.ends_at else None,
        "team": team_payload(db, row),
        "wheel_tables": [{"number": table.table_number, "mode": table.game_mode} for table in
                         db.query(Round3DealerTable).filter(Round3DealerTable.is_enabled.is_(True)).order_by(Round3DealerTable.table_number).all()],
        "lots": [{**lot_payload(db, lot, row.team_id),
                  "description": "Sealed intelligence. Watch for the auctioneer's release." if lot.status == "DRAFT" else lot.description}
                 for lot in lots],
    }, "message": "Your private team Round 3 state loaded."}


@router.post("/participant/signout")
def signout(account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)), db: Session = Depends(get_db)):
    session_id = getattr(account, "_event_jti", None)
    session = db.get(Round3TeamSession, session_id) if session_id else None
    if session and session.team_id == account.team_id:
        session.signed_out_at = utcnow()
        db.commit()
    return {"success": True, "data": {"signed_out": True}, "message": "This device signed out."}


@router.post("/participant/assign")
@router.post("/participant/spin")
def assign_station(payload: SpinInput, account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)), db: Session = Depends(get_db)):
    require_open(db)
    row = eligible(db, account)
    participant = db.get(Participant, payload.participant_id)
    if not participant or participant.team_id != row.team_id:
        raise HTTPException(403, "Select a member of your own team.")
    # Three devices may remain logged in, but only two players from one team
    # may occupy stations at the same time. The third device can follow/bid.
    db.query(Round3LiveTeam).filter(Round3LiveTeam.team_id == row.team_id).with_for_update().one()
    # Serialize question assignment so concurrent devices cannot reserve the
    # same one-use question.
    db.query(Round3LiveConfig).filter(Round3LiveConfig.id == 1).with_for_update().one()
    active = db.query(Round3GameAttempt).filter(
        Round3GameAttempt.team_id == row.team_id,
        Round3GameAttempt.status.in_(["RESERVED", "ACTIVE"]),
    ).all()
    if len(active) >= MAX_ACTIVE_TEAM_ASSIGNMENTS:
        raise HTTPException(409, "Your team already has two live station assignments. The third login can follow the auction or team status.")
    if any(item.participant_id == participant.id for item in active):
        raise HTTPException(409, "This member already has a live station assignment.")
    tables = db.query(Round3DealerTable).filter(Round3DealerTable.is_enabled.is_(True)).order_by(Round3DealerTable.table_number).all()
    if len(tables) != 8:
        raise HTTPException(409, "All eight puzzle stations must be enabled before automatic assignment.")

    for item in tables:
        db.query(Round3DealerTable).filter(Round3DealerTable.table_number == item.table_number).with_for_update().one()
        expire_and_promote(db, item)

    recent_team = db.query(Round3GameAttempt).filter(
        Round3GameAttempt.team_id == row.team_id,
        Round3GameAttempt.status == "COMPLETE",
    ).order_by(Round3GameAttempt.ended_at.desc(), Round3GameAttempt.created_at.desc()).first()
    recent_player = db.query(Round3GameAttempt).filter(
        Round3GameAttempt.participant_id == participant.id,
        Round3GameAttempt.status == "COMPLETE",
    ).order_by(Round3GameAttempt.ended_at.desc(), Round3GameAttempt.created_at.desc()).limit(2).all()
    blocked = ({recent_team.table_number} if recent_team else set()) | {item.table_number for item in recent_player}
    occupied = {item.table_number for item in db.query(Round3GameAttempt).filter(
        Round3GameAttempt.status.in_(["RESERVED", "ACTIVE"]),
    ).all()}
    used_keys = {value for (value,) in db.query(Round3PuzzleUse.puzzle_key).all()}
    remaining_by_table = {
        item.table_number: [puzzle for puzzle in PUZZLES.get(item.table_number, ()) if puzzle.key not in used_keys]
        for item in tables
    }
    available = [
        item for item in tables
        if item.table_number not in blocked
        and item.table_number not in occupied
        and remaining_by_table[item.table_number]
    ]
    if not available:
        raise HTTPException(409, "Every eligible station is busy, cooling down, or has exhausted its one-use questions. Wait for another table to finish.")

    attempt_counts = dict(db.query(Round3GameAttempt.table_number, func.count(Round3GameAttempt.id)).filter(
        Round3GameAttempt.status == "COMPLETE",
    ).group_by(Round3GameAttempt.table_number).all())
    table = min(available, key=lambda item: (attempt_counts.get(item.table_number, 0), item.table_number))
    puzzle = remaining_by_table[table.table_number][0]
    attempt = Round3GameAttempt(
        id=f"r3game-{uuid.uuid4().hex[:18]}",
        team_id=row.team_id,
        participant_id=participant.id,
        table_number=table.table_number,
        status="RESERVED",
        reserved_until=utcnow() + timedelta(seconds=RESERVATION_SECONDS),
    )
    set_attempt_meta(attempt, puzzle_key=puzzle.key, access_code=f"{secrets.randbelow(900) + 100:03d}")
    db.add(attempt)
    db.add(Round3PuzzleUse(
        puzzle_key=puzzle.key,
        table_number=table.table_number,
        attempt_id=attempt.id,
        team_id=row.team_id,
        participant_id=participant.id,
    ))
    db.commit()
    return {"success": True, "data": attempt_payload(db, attempt, reveal_access=True), "message": "Station assigned. Go to the laptop, then send the three-digit arrival code."}


@router.post("/participant/attempts/{attempt_id}/reveal-code")
def reveal_station_code(attempt_id: str, account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)), db: Session = Depends(get_db)):
    require_open(db)
    row = eligible(db, account)
    attempt = db.get(Round3GameAttempt, attempt_id)
    if not attempt or attempt.team_id != row.team_id:
        raise HTTPException(404, "Station assignment not found.")
    if attempt.status != "RESERVED":
        raise HTTPException(409, "This station code is no longer available.")
    table = db.query(Round3DealerTable).filter(Round3DealerTable.table_number == attempt.table_number).with_for_update().one()
    expire_and_promote(db, table)
    if attempt.status != "RESERVED":
        raise HTTPException(409, "This reservation expired before the code was sent.")
    meta = attempt_meta(attempt)
    if not meta.get("code_revealed_at"):
        set_attempt_meta(attempt, code_revealed_at=utcnow().isoformat())
    db.commit()
    return {"success": True, "data": attempt_payload(db, attempt, reveal_access=True), "message": "The three-digit code is now visible on the assigned table laptop."}


@router.post("/participant/queue")
def queue(account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)), db: Session = Depends(get_db)):
    raise HTTPException(410, "Queues are no longer used. Automatic assignment selects only an available station.")


@router.post("/participant/cancel")
def cancel(account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)), db: Session = Depends(get_db)):
    row = eligible(db, account)
    attempt = db.query(Round3GameAttempt).filter(Round3GameAttempt.team_id == row.team_id, Round3GameAttempt.status == "RESERVED").order_by(Round3GameAttempt.created_at.desc()).first()
    if not attempt:
        raise HTTPException(409, "No unstarted turn can be cancelled.")
    table = db.query(Round3DealerTable).filter(Round3DealerTable.table_number == attempt.table_number).with_for_update().one()
    attempt.status, attempt.ended_at = "CANCELLED", utcnow()
    db.flush()
    db.commit()
    return {"success": True, "data": {"cancelled": True}, "message": "Reservation cancelled. The station is available again."}


@router.post("/participant/attempts/{attempt_id}/cancel")
def cancel_assignment(attempt_id: str, account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)), db: Session = Depends(get_db)):
    row = eligible(db, account)
    attempt = db.get(Round3GameAttempt, attempt_id)
    if not attempt or attempt.team_id != row.team_id:
        raise HTTPException(404, "Assignment not found.")
    if attempt.status != "RESERVED":
        raise HTTPException(409, "Only an unstarted reservation can be cancelled.")
    db.query(Round3DealerTable).filter(Round3DealerTable.table_number == attempt.table_number).with_for_update().one()
    attempt.status, attempt.ended_at = "CANCELLED", utcnow()
    db.commit()
    return {"success": True, "data": {"cancelled": True}, "message": "Reservation cancelled. The station is available again."}


@router.post("/participant/lots/{lot_id}/bid")
def place_bid(lot_id: str, payload: BidInput, account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)), db: Session = Depends(get_db)):
    require_open(db)
    row = eligible(db, account)
    db.query(Round3LiveConfig).filter(Round3LiveConfig.id == 1).with_for_update().one()
    lot = db.get(Round3AuctionLot, lot_id)
    if not lot or lot.status != "LIVE":
        raise HTTPException(409, "This clue token is not available for bidding.")
    top = db.query(Round3AuctionBid).filter(Round3AuctionBid.lot_id == lot_id).order_by(Round3AuctionBid.amount.desc(), Round3AuctionBid.created_at, Round3AuctionBid.id).first()
    if payload.amount < lot.opening_bid or (top and payload.amount <= top.amount):
        raise HTTPException(409, "Bid must exceed the current highest bid and meet the opening price.")
    if payload.amount > balance(db, row) - held_bids(db, row.team_id, except_lot=lot.id):
        raise HTTPException(409, "Not enough uncommitted team points for this bid.")
    db.add(Round3AuctionBid(lot_id=lot_id, team_id=row.team_id, amount=payload.amount))
    db.commit()
    return {"success": True, "data": {"amount": payload.amount}, "message": "Bid recorded. Points are held only while your team leads."}


@router.get("/admin/table")
def dealer_table(account: EventAccount = Depends(require_roles(EventRole.ADMIN)), db: Session = Depends(get_db)):
    table = db.query(Round3DealerTable).filter(Round3DealerTable.admin_id == account.id).first()
    started = bool(config(db).starts_at)
    if not table:
        return {"success": True, "data": {"assigned": False, "started": started}, "message": "No dealer table is assigned."}
    db.query(Round3DealerTable).filter(Round3DealerTable.table_number == table.table_number).with_for_update().one()
    expire_and_promote(db, table)
    db.commit()
    attempts = db.query(Round3GameAttempt).filter(Round3GameAttempt.table_number == table.table_number, Round3GameAttempt.status.in_(["RESERVED", "ACTIVE"])).order_by(Round3GameAttempt.created_at).all()
    return {"success": True, "data": {"assigned": True, "started": started, "number": table.table_number, "room": table.room_number, "mode": table.game_mode, "game_name": table.game_name, "max_points": table.max_points,
        "attempts": [{**attempt_payload(db, attempt, reveal_access=True, reveal_puzzle=True), "team_identifier": f"TEAM{1000 + db.get(Team, attempt.team_id).team_number}"} for attempt in attempts]}, "message": "Automated puzzle station loaded."}


@router.post("/admin/attempts/{attempt_id}/unlock")
def unlock_station(attempt_id: str, payload: StationStartInput, account: EventAccount = Depends(require_roles(EventRole.ADMIN)), db: Session = Depends(get_db)):
    require_open(db)
    attempt = db.get(Round3GameAttempt, attempt_id)
    if not attempt:
        raise HTTPException(404, "Station reservation not found.")
    table = db.query(Round3DealerTable).filter(Round3DealerTable.table_number == attempt.table_number).with_for_update().one()
    if table.admin_id != account.id:
        raise HTTPException(403, "This laptop is not assigned to that station.")
    expire_and_promote(db, table)
    if attempt.status != "RESERVED":
        raise HTTPException(409, "This reservation expired or the puzzle has already started.")
    meta = attempt_meta(attempt)
    if not meta.get("code_revealed_at"):
        raise HTTPException(409, "The player must send the arrival code from their team device first.")
    if not secrets.compare_digest(str(meta.get("access_code", "")), payload.access_code):
        failures = int(meta.get("code_failures", 0)) + 1
        set_attempt_meta(attempt, code_failures=failures)
        if failures >= 5:
            attempt.status, attempt.ended_at = "EXPIRED", utcnow()
        db.commit()
        if failures >= 5:
            raise HTTPException(409, "Too many incorrect codes. This reservation was released; request a new station assignment.")
        raise HTTPException(403, "Arrival code does not match this reservation.")
    attempt.status, attempt.started_at, attempt.reserved_until = "ACTIVE", utcnow(), None
    db.commit()
    return {"success": True, "data": attempt_payload(db, attempt, reveal_puzzle=True), "message": "Puzzle unlocked. The 75-second server timer is running."}


@router.post("/admin/attempts/{attempt_id}/answer")
def submit_station_answer(attempt_id: str, payload: StationAnswerInput, account: EventAccount = Depends(require_roles(EventRole.ADMIN)), db: Session = Depends(get_db)):
    attempt = db.get(Round3GameAttempt, attempt_id)
    if not attempt:
        raise HTTPException(404, "Puzzle attempt not found.")
    table = db.query(Round3DealerTable).filter(Round3DealerTable.table_number == attempt.table_number).with_for_update().one()
    if table.admin_id != account.id:
        raise HTTPException(403, "This laptop is not assigned to that station.")
    if attempt.status != "ACTIVE" or not attempt.started_at:
        raise HTTPException(409, "This puzzle is not active or has already been locked.")
    if utcnow() > as_utc(attempt.started_at) + timedelta(seconds=GAME_SECONDS):
        record_automated_result(db, attempt, table, False, "Time expired — 0 points")
        db.commit()
        raise HTTPException(409, "Time expired. The answer was locked and no points were awarded.")
    key = str(attempt_meta(attempt).get("puzzle_key", ""))
    try:
        puzzle = puzzle_by_key(key)
    except KeyError as problem:
        raise HTTPException(500, "This station's puzzle configuration is missing.") from problem
    correct = is_correct(puzzle, payload.answer)
    reason = f"Correct answer — +{table.max_points:g} points" if correct else "Incorrect answer — 0 points"
    record_automated_result(db, attempt, table, correct, reason)
    db.commit()
    return {"success": True, "data": {**attempt_payload(db, attempt), "correct": correct, "awarded": attempt.points}, "message": reason}


@router.post("/admin/attempts/{attempt_id}/start")
def start_game(attempt_id: str, account: EventAccount = Depends(require_roles(EventRole.ADMIN)), db: Session = Depends(get_db)):
    raise HTTPException(410, "Manual dealer start was removed. Enter the team's four-digit arrival code on the station screen.")


@router.post("/admin/attempts/{attempt_id}/finish")
def finish_game(attempt_id: str, payload: ScoreInput, account: EventAccount = Depends(require_roles(EventRole.ADMIN)), db: Session = Depends(get_db)):
    raise HTTPException(410, "Manual scoring was removed. The station validates the locked answer automatically.")
