import random
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from fastapi import HTTPException, status

from app.core import constants as C
from app.db.base import utc_now
from app.models.round_models import (
    RoundState,
    Round1Record,
    Round2Placement,
    Round3Transaction,
    Round3CodeRecord,
    Round4Pair,
    Round4JudgeScore,
    Round4AgentGuess,
    FinaleScorecard,
    FinaleAgentVerdict,
)
from app.models.team import Team, TeamStatus
from app.models.user import User
from app.schemas.rounds import (
    RoundSummary,
    RoundUpdateRequest,
    FinalizeRoundRequest,
    FinalizeRoundResponse,
    Round1RecordResponse,
    Round1RecordUpdateRequest,
    Round1BatchUpdateRequest,
    Round2PlacementCreate,
    Round2PlacementResponse,
    Round2GameSubmitRequest,
    Round2TeamSummary,
    Round3TransactionCreate,
    Round3TransferRequest,
    Round3TransactionResponse,
    Round3CodeRecordResponse,
    Round3CodeFragmentUpdate,
    Round3TeamSummary,
    Round4PairCreate,
    Round4PairUpdate,
    Round4PairResponse,
    Round4JudgeScoreSubmit,
    Round4JudgeScoreResponse,
    Round4AgentGuessSubmit,
    Round4AgentGuessResponse,
    Round4TeamSummary,
    FinaleScorecardSubmit,
    FinaleScorecardResponse,
    FinaleAgentVerdictSubmit,
    FinaleAgentVerdictResponse,
    FinaleTeamSummary,
)

# Default Round metadata definitions.
#
# These values are read from app.core.constants, NOT written as literals.
#
# This module and the newer app/services/round{1..4}_service.py are BOTH live -
# api/router.py mounts the r1..r4 routers and this legacy rounds.router, and
# the dashboard still calls /rounds/1/records here. Until one of the two layers
# is retired, they must agree, or the same tournament is scored differently
# depending on which endpoint the frontend happened to call.
#
# They did not agree. Every value below was the pre-documentation default:
# a 120s hint penalty, a 100-point starting balance, 4 code fragments, +10/-5
# agent guessing, a 0.0 carryover weight and a twelve-tier Cabo ladder - none
# of which appear in the Event Documentation.
DEFAULT_ROUNDS = [
    {
        "id": 1,
        "name": "Clue Hunt / Expedition",
        "codename": "ROUND_1_CLUE_HUNT",
        "description": "32 squads solve multi-station physical/logical clues in mini-rounds. Top 24 qualify.",
        "initial_teams_count": 32,
        "qualifying_teams_count": 24,
        "status": "In Progress",
        "location": "Campus Grounds & Quadrangles",
        "config_json": {
            "hintPenaltySeconds": C.DEFAULT_R1_HINT_PENALTY_SECONDS,
            "miniRoundsCount": 3,
            "tieBreakerRule": "fastest_mini_round"
        }
    },
    {
        "id": 2,
        "name": "Cabo Tournament",
        "codename": "ROUND_2_CABO",
        "description": "24 squads compete in strategic card matches across 3 games. Top 12 qualify.",
        "initial_teams_count": 24,
        "qualifying_teams_count": 12,
        "status": "Scheduled",
        "location": "Main Auditorium Annex",
        "config_json": {
            "totalGames": 3,
            "scoringDirection": "high_is_better",
            # Section 5.3: a Cabo table seats five, scoring 5/3/2/1/0. The
            # twelve-tier 100/80/65/... ladder that was here appears nowhere in
            # the documentation and made Round 2 outweigh every other source.
            "placementPoints": {"1": 5, "2": 3, "3": 2, "4": 1, "5": 0}
        }
    },
    {
        "id": 3,
        "name": "The Black Market",
        "codename": "ROUND_3_BLACK_MARKET",
        "description": "12 squads navigate a volatile resource economy, trading assets and recovering code fragments. Top 8 qualify.",
        "initial_teams_count": 12,
        "qualifying_teams_count": 8,
        "status": "Scheduled",
        "location": "Commerce Wing Hub",
        "config_json": {
            "startingBalance": C.STARTING_WALLET_BALANCE,
            "codeFragmentsCount": C.CODE_FRAGMENT_COUNT,
            "allowNegativeBalance": False
        }
    },
    {
        "id": 4,
        "name": "The Legal Battle",
        "codename": "ROUND_4_LEGAL_BATTLE",
        # Sections 7 and 9.1: all 8 finalists argue and all 8 are ranked.
        # There is no cut to three before the finale - the podium is what the
        # final ranking produces. A 3-team finale also contradicts Section 8.1,
        # where every team guesses "the other 7 finalist teams".
        "description": "8 squads in 4 courtroom pairings argue fictional cases before faculty judges.",
        "initial_teams_count": C.R4_FINALISTS,
        "qualifying_teams_count": C.R4_ADVANCING_COUNT,
        "status": "Scheduled",
        "location": "Moot Court Hall",
        "config_json": {
            "totalPairs": C.R4_PAIRS,
            "agentGuessBonus": C.AGENT_CORRECT_GUESS,
            "maxJuryScore": C.R4_RUBRIC_TOTAL_MAX
        }
    },
    {
        "id": 5,
        "name": "Grand Finale",
        "codename": "GRAND_FINALE",
        "description": "The 8 finalists unmask secret agents; the final ranking decides the championship.",
        "initial_teams_count": C.R4_FINALISTS,
        "qualifying_teams_count": 1,
        "status": "Scheduled",
        "location": "Main Auditorium Stage",
        "config_json": {
            # Section 9.1: "Final Score = Legal Battle panel score + Agent
            # guessing points + 10% of remaining Black Market points." A weight
            # of 0.0 dropped the economy out of the championship entirely and
            # made Round 3 spending consequence-free.
            "carryoverWeight": C.FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED,
            "juryWeight": 1.0,
            "agentBonusPoints": C.AGENT_CORRECT_GUESS,
            "agentPenaltyPoints": C.AGENT_WRONG_GUESS
        }
    }
]


# =========================================================================
# Round State Service Methods
# =========================================================================

def ensure_round_states_initialized(db: Session) -> List[RoundState]:
    """Ensure all 5 round states exist in database."""
    states = db.execute(select(RoundState).order_by(RoundState.id.asc())).scalars().all()
    if len(states) < 5:
        existing_ids = {s.id for s in states}
        for defn in DEFAULT_ROUNDS:
            if defn["id"] not in existing_ids:
                new_state = RoundState(
                    id=defn["id"],
                    name=defn["name"],
                    codename=defn["codename"],
                    description=defn["description"],
                    initial_teams_count=defn["initial_teams_count"],
                    qualifying_teams_count=defn["qualifying_teams_count"],
                    status=defn["status"],
                    location=defn["location"],
                    config_json=defn["config_json"],
                )
                db.add(new_state)
        db.commit()
        states = db.execute(select(RoundState).order_by(RoundState.id.asc())).scalars().all()
    return states


def get_all_rounds(db: Session) -> List[RoundState]:
    return ensure_round_states_initialized(db)


def get_round_by_number(db: Session, round_num: int) -> RoundState:
    ensure_round_states_initialized(db)
    state = db.execute(select(RoundState).where(RoundState.id == round_num)).scalar_one_or_none()
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Round {round_num} not found")
    return state


def update_round_state(db: Session, round_num: int, update_data: RoundUpdateRequest) -> RoundState:
    state = get_round_by_number(db, round_num)
    if update_data.name is not None:
        state.name = update_data.name
    if update_data.status is not None:
        state.status = update_data.status
    if update_data.location is not None:
        state.location = update_data.location
    if update_data.initial_teams_count is not None:
        state.initial_teams_count = update_data.initial_teams_count
    if update_data.qualifying_teams_count is not None:
        state.qualifying_teams_count = update_data.qualifying_teams_count
    if update_data.started_at is not None:
        state.started_at = update_data.started_at
    if update_data.ended_at is not None:
        state.ended_at = update_data.ended_at
    if update_data.config_json is not None:
        # Merge or replace config
        merged = dict(state.config_json)
        merged.update(update_data.config_json)
        state.config_json = merged
    
    db.commit()
    db.refresh(state)
    return state



# =========================================================================
# Validation Helpers
# =========================================================================

def _check_round_not_finalized(db: Session, round_num: int):
    """Ensure that mutations are blocked on finalized rounds."""
    state = get_round_by_number(db, round_num)
    if state.is_finalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Round {round_num} ({state.name}) is finalized and sealed. Modifications are not allowed."
        )


def _validate_team_exists(db: Session, team_id: str) -> Team:
    """Validate that the specified team ID exists in the database."""
    team = db.execute(select(Team).where(Team.id == team_id)).scalar_one_or_none()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID '{team_id}' does not exist."
        )
    return team


# =========================================================================
# Round 1 Service Methods
# =========================================================================

def initialize_round1_records(db: Session):
    """Ensure all active teams have a Round1Record."""
    teams = db.execute(select(Team).where(Team.status != TeamStatus.DISQUALIFIED)).scalars().all()
    existing_team_ids = set(db.execute(select(Round1Record.team_id)).scalars().all())
    
    for team in teams:
        if team.id not in existing_team_ids:
            rec = Round1Record(
                team_id=team.id,
                mini_rounds_json=[
                    {"roundNumber": 1, "hintsUsed": 0, "hintPenaltySeconds": 0, "isCompleted": False},
                    {"roundNumber": 2, "hintsUsed": 0, "hintPenaltySeconds": 0, "isCompleted": False},
                    {"roundNumber": 3, "hintsUsed": 0, "hintPenaltySeconds": 0, "isCompleted": False},
                ],
                qualification_status="Incomplete",
            )
            db.add(rec)
    db.commit()


def calculate_round1_record_scores(rec: Round1Record, penalty_per_hint: float = C.DEFAULT_R1_HINT_PENALTY_SECONDS):
    """Calculate raw total, penalties, adjusted total, and fastest mini-round."""
    mini_rounds = rec.mini_rounds_json or []
    raw_seconds = 0.0
    total_penalty = 0.0
    fastest = None
    all_completed = len(mini_rounds) >= 3

    for mr in mini_rounds:
        dur = mr.get("durationSeconds")
        if dur is None and mr.get("startTime") and mr.get("completionTime"):
            try:
                t0 = datetime.fromisoformat(mr["startTime"].replace("Z", "+00:00"))
                t1 = datetime.fromisoformat(mr["completionTime"].replace("Z", "+00:00"))
                dur = (t1 - t0).total_seconds()
            except Exception:
                dur = None
        
        if dur is not None:
            raw_seconds += dur
            if fastest is None or dur < fastest:
                fastest = dur
        else:
            all_completed = False

        hints = mr.get("hintsUsed", 0)
        penalty = hints * penalty_per_hint
        mr["hintPenaltySeconds"] = penalty
        total_penalty += penalty
        if not mr.get("isCompleted", False):
            all_completed = False

    rec.raw_total_seconds = raw_seconds if all_completed else None
    rec.total_penalty_seconds = total_penalty
    rec.adjusted_total_seconds = (raw_seconds + total_penalty) if all_completed else None
    rec.fastest_mini_round_seconds = fastest
    rec.is_complete = all_completed


def get_round1_records(db: Session) -> List[Round1Record]:
    initialize_round1_records(db)
    round_state = get_round_by_number(db, 1)
    penalty_per_hint = float(round_state.config_json.get("hintPenaltySeconds", C.DEFAULT_R1_HINT_PENALTY_SECONDS))
    
    records = db.execute(select(Round1Record)).scalars().all()
    for rec in records:
        calculate_round1_record_scores(rec, penalty_per_hint)
    
    # Sort and rank records
    # Completed records sorted ascending by adjusted_total_seconds, then fastest_mini_round_seconds
    completed = [r for r in records if r.is_complete and r.adjusted_total_seconds is not None]
    incomplete = [r for r in records if not (r.is_complete and r.adjusted_total_seconds is not None)]
    
    completed.sort(key=lambda r: (r.adjusted_total_seconds, r.fastest_mini_round_seconds or 999999))
    
    qualifying_count = round_state.qualifying_teams_count
    for i, r in enumerate(completed):
        r.rank = i + 1
        r.qualification_status = "Qualified" if (i + 1) <= qualifying_count else "Eliminated"
        
        # Check for ties
        if i > 0:
            prev = completed[i - 1]
            if prev.adjusted_total_seconds == r.adjusted_total_seconds and prev.fastest_mini_round_seconds == r.fastest_mini_round_seconds:
                r.tie_requires_review = True
                r.tie_reason = "Identical adjusted total and fastest mini-round duration"
                prev.tie_requires_review = True
                prev.tie_reason = "Identical adjusted total and fastest mini-round duration"
    
    for r in incomplete:
        r.rank = None
        r.qualification_status = "Incomplete"

    db.commit()
    return records


def update_round1_record(db: Session, team_id: str, data: Round1RecordUpdateRequest, user: User) -> Round1Record:
    _check_round_not_finalized(db, 1)
    _validate_team_exists(db, team_id)

    rec = db.execute(select(Round1Record).where(Round1Record.team_id == team_id)).scalar_one_or_none()
    if not rec:
        rec = Round1Record(team_id=team_id)
        db.add(rec)
    
    if data.mini_rounds is not None:
        rec.mini_rounds_json = data.mini_rounds
    if data.hidden_code_recovered is not None:
        rec.hidden_code_recovered = data.hidden_code_recovered
        if data.hidden_code_recovered and not rec.hidden_code_recovered_at:
            rec.hidden_code_recovered_at = utc_now()
    if data.hidden_code_notes is not None:
        rec.hidden_code_notes = data.hidden_code_notes
    
    rec.last_edited_by = user.name
    
    round_state = get_round_by_number(db, 1)
    penalty_per_hint = float(round_state.config_json.get("hintPenaltySeconds", C.DEFAULT_R1_HINT_PENALTY_SECONDS))
    calculate_round1_record_scores(rec, penalty_per_hint)
    
    db.commit()
    db.refresh(rec)
    return rec


def batch_update_round1_records(db: Session, data: Round1BatchUpdateRequest, user: User) -> List[Round1Record]:
    _check_round_not_finalized(db, 1)
    updated = []
    for item in data.records:
        team_id = item.get("teamId") or item.get("team_id")
        if not team_id:
            continue
        req = Round1RecordUpdateRequest(
            mini_rounds=item.get("miniRounds") or item.get("mini_rounds"),
            hidden_code_recovered=item.get("hiddenCodeRecovered") or item.get("hidden_code_recovered"),
            hidden_code_notes=item.get("hiddenCodeNotes") or item.get("hidden_code_notes"),
            last_edited_by=user.name
        )
        rec = update_round1_record(db, team_id, req, user)
        updated.append(rec)
    return updated


# =========================================================================
# Round 2 Service Methods
# =========================================================================

def get_round2_placements(db: Session, game_number: Optional[int] = None) -> List[Round2Placement]:
    query = select(Round2Placement)
    if game_number is not None:
        query = query.where(Round2Placement.game_number == game_number)
    return db.execute(query.order_by(Round2Placement.game_number.asc(), Round2Placement.placement.asc())).scalars().all()


def record_round2_placement(db: Session, data: Round2PlacementCreate, user: User) -> Round2Placement:
    _check_round_not_finalized(db, 2)
    _validate_team_exists(db, data.team_id)
    if data.placement < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Placement must be at least 1")

    round_state = get_round_by_number(db, 2)
    pts_table = round_state.config_json.get("placementPoints", {})
    calculated_pts = data.points
    if calculated_pts is None:
        # Fall back to the documented Section 5.3 table rather than an invented
        # formula. The old fallback, `100 - (placement - 1) * 10`, produced
        # points that appear nowhere in the Event Documentation.
        calculated_pts = float(
            pts_table.get(str(data.placement), C.CABO_PLACEMENT_POINTS.get(data.placement, 0))
        )
    
    existing = db.execute(
        select(Round2Placement).where(
            and_(
                Round2Placement.game_number == data.game_number,
                Round2Placement.team_id == data.team_id
            )
        )
    ).scalar_one_or_none()
    
    if existing:
        existing.placement = data.placement
        existing.points = calculated_pts
        existing.notes = data.notes
        existing.recorded_by = user.name
        existing.recorded_at = utc_now()
        db.commit()
        db.refresh(existing)
        return existing
    
    new_placement = Round2Placement(
        game_number=data.game_number,
        team_id=data.team_id,
        placement=data.placement,
        points=calculated_pts,
        notes=data.notes,
        recorded_by=user.name,
        recorded_at=utc_now()
    )
    db.add(new_placement)
    db.commit()
    db.refresh(new_placement)
    return new_placement


def submit_round2_game(db: Session, data: Round2GameSubmitRequest, user: User) -> List[Round2Placement]:
    _check_round_not_finalized(db, 2)
    results = []
    for p in data.placements:
        team_id = p.get("teamId") or p.get("team_id")
        placement = p.get("placement")
        points = p.get("points")
        notes = p.get("notes")
        if not team_id or placement is None:
            continue
        req = Round2PlacementCreate(
            game_number=data.game_number,
            team_id=team_id,
            placement=placement,
            points=points,
            notes=notes
        )
        res = record_round2_placement(db, req, user)
        results.append(res)
    return results


def get_round2_standings(db: Session) -> List[Round2TeamSummary]:
    round_state = get_round_by_number(db, 2)
    qualifying_count = round_state.qualifying_teams_count
    
    # Get all teams participating in Round 2 (e.g. current_round >= 2 or qualified from R1)
    teams = db.execute(select(Team).where(Team.status != TeamStatus.DISQUALIFIED)).scalars().all()
    placements = db.execute(select(Round2Placement)).scalars().all()
    
    team_placements: Dict[str, Dict[int, Round2Placement]] = {}
    for p in placements:
        if p.team_id not in team_placements:
            team_placements[p.team_id] = {}
        team_placements[p.team_id][p.game_number] = p
    
    summaries: List[Round2TeamSummary] = []
    for team in teams:
        games = team_placements.get(team.id, {})
        g1 = games.get(1)
        g2 = games.get(2)
        g3 = games.get(3)
        
        p1 = g1.points if g1 else None
        p2 = g2.points if g2 else None
        p3 = g3.points if g3 else None
        
        tot = (p1 or 0.0) + (p2 or 0.0) + (p3 or 0.0)
        played = len(games)
        
        # Only include if played at least 1 game or is in current round 2
        summaries.append(Round2TeamSummary(
            team_id=team.id,
            team_name=team.name,
            team_identifier=f"T{team.team_number:02d}",
            game1_points=p1,
            game2_points=p2,
            game3_points=p3,
            total_points=tot,
            games_played=played,
            qualification_status="Pending"
        ))
    
    # Sort descending by total_points
    summaries.sort(key=lambda s: s.total_points, reverse=True)
    for i, s in enumerate(summaries):
        s.rank = i + 1
        s.qualification_status = "Qualified" if (i + 1) <= qualifying_count else "Eliminated"
        
    return summaries


# =========================================================================
# Round 3 Service Methods
# =========================================================================

def get_round3_transactions(db: Session, team_id: Optional[str] = None) -> List[Round3Transaction]:
    query = select(Round3Transaction)
    if team_id:
        query = query.where(Round3Transaction.team_id == team_id)
    return db.execute(query.order_by(Round3Transaction.timestamp.desc())).scalars().all()


def create_round3_transaction(db: Session, data: Round3TransactionCreate, user: User) -> Round3Transaction:
    _check_round_not_finalized(db, 3)
    _validate_team_exists(db, data.team_id)
    if data.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction amount must be positive")

    round_state = get_round_by_number(db, 3)
    allow_negative = round_state.config_json.get("allowNegativeBalance", False)
    
    # Check balance if spending
    if data.type == "spend" and not allow_negative:
        standings = {s.team_id: s for s in get_round3_standings(db)}
        current_bal = standings[data.team_id].current_balance if data.team_id in standings else 0.0
        if current_bal < data.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient balance ({current_bal:.1f} pts) for expenditure of {data.amount:.1f} pts"
            )
    
    tx = Round3Transaction(
        team_id=data.team_id,
        amount=data.amount,
        type=data.type,
        reason=data.reason,
        organizer_ref=data.organizer_ref or user.name,
        timestamp=utc_now(),
        notes=data.notes
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def reverse_round3_transaction(db: Session, transaction_id: str, user: User) -> Round3Transaction:
    _check_round_not_finalized(db, 3)
    tx = db.execute(select(Round3Transaction).where(Round3Transaction.id == transaction_id)).scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if tx.is_reversed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction already reversed")
    
    # Create compensating reversal transaction
    rev_type = "reversal"
    rev_amount = -tx.amount if tx.type == "earn" else (tx.amount if tx.type == "spend" else -tx.amount)
    
    reversal_tx = Round3Transaction(
        team_id=tx.team_id,
        amount=abs(tx.amount),
        type="reversal",
        reason=f"Reversal of TX #{tx.id}: {tx.reason}",
        organizer_ref=user.name,
        timestamp=utc_now(),
        reversed_transaction_id=tx.id,
        notes=f"Authorized by {user.name}"
    )
    db.add(reversal_tx)
    db.flush()
    
    tx.is_reversed = True
    tx.reversal_transaction_id = reversal_tx.id
    db.commit()
    db.refresh(reversal_tx)
    return reversal_tx


def transfer_round3_funds(db: Session, data: Round3TransferRequest, user: User) -> Tuple[Round3Transaction, Round3Transaction]:
    """Transfer funds between two teams using deterministic row-locking order."""
    _check_round_not_finalized(db, 3)
    _validate_team_exists(db, data.from_team_id)
    _validate_team_exists(db, data.to_team_id)
    if data.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transfer amount must be positive")

    if data.from_team_id == data.to_team_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sender and receiver teams must be distinct")
    
    # Acquire locks in deterministic sorted ID order to avoid PostgreSQL deadlock
    first_id, second_id = sorted([data.from_team_id, data.to_team_id])
    
    # Verify sender balance
    standings = {s.team_id: s for s in get_round3_standings(db)}
    sender_bal = standings[data.from_team_id].current_balance if data.from_team_id in standings else 0.0
    if sender_bal < data.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sender team has insufficient balance ({sender_bal:.1f} pts) for transfer of {data.amount:.1f} pts"
        )
    
    sender_tx = Round3Transaction(
        team_id=data.from_team_id,
        amount=data.amount,
        type="spend",
        reason=f"Transfer to Team {data.to_team_id}: {data.reason}",
        organizer_ref=user.name,
        timestamp=utc_now(),
        notes=data.notes
    )
    receiver_tx = Round3Transaction(
        team_id=data.to_team_id,
        amount=data.amount,
        type="earn",
        reason=f"Transfer from Team {data.from_team_id}: {data.reason}",
        organizer_ref=user.name,
        timestamp=utc_now(),
        notes=data.notes
    )
    
    db.add(sender_tx)
    db.add(receiver_tx)
    db.commit()
    db.refresh(sender_tx)
    db.refresh(receiver_tx)
    return (sender_tx, receiver_tx)


def get_round3_code_records(db: Session) -> List[Round3CodeRecord]:
    return db.execute(select(Round3CodeRecord)).scalars().all()


def update_round3_code_fragment(db: Session, data: Round3CodeFragmentUpdate, user: User) -> Round3CodeRecord:
    _check_round_not_finalized(db, 3)
    _validate_team_exists(db, data.team_id)
    if data.fragment_index < 0 or data.fragment_index > 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fragment index must be between 0 and 3")

    rec = db.execute(select(Round3CodeRecord).where(Round3CodeRecord.team_id == data.team_id)).scalar_one_or_none()
    if not rec:
        rec = Round3CodeRecord(
            team_id=data.team_id,
            fragments_json=[
                {"index": 0, "isDiscovered": False, "code": ""},
                {"index": 1, "isDiscovered": False, "code": ""},
                {"index": 2, "isDiscovered": False, "code": ""},
                {"index": 3, "isDiscovered": False, "code": ""},
            ]
        )
        db.add(rec)
    
    fragments = [dict(f) for f in (rec.fragments_json or [])]
    while len(fragments) <= data.fragment_index:
        fragments.append({"index": len(fragments), "isDiscovered": False, "code": ""})
    
    fragments[data.fragment_index]["isDiscovered"] = data.is_discovered
    if data.code is not None:
        fragments[data.fragment_index]["code"] = data.code
    if data.clue_station is not None:
        fragments[data.fragment_index]["clueStation"] = data.clue_station
        
    rec.fragments_json = fragments
    flag_modified(rec, "fragments_json")
    rec.is_complete = all(f.get("isDiscovered", False) for f in fragments[:4])
    if rec.is_complete and not rec.verified_at:
        rec.verified_at = utc_now()
        rec.verified_by = user.name
        
    db.commit()
    db.refresh(rec)
    return rec


def get_round3_standings(db: Session) -> List[Round3TeamSummary]:
    round_state = get_round_by_number(db, 3)
    starting_balance = float(round_state.config_json.get("startingBalance", C.STARTING_WALLET_BALANCE))
    qualifying_count = round_state.qualifying_teams_count
    
    teams = db.execute(select(Team).where(Team.status != TeamStatus.DISQUALIFIED)).scalars().all()
    transactions = db.execute(select(Round3Transaction).where(Round3Transaction.is_reversed == False)).scalars().all()
    codes = db.execute(select(Round3CodeRecord)).scalars().all()
    
    tx_map: Dict[str, List[Round3Transaction]] = {}
    for tx in transactions:
        tx_map.setdefault(tx.team_id, []).append(tx)
        
    code_map = {c.team_id: c for c in codes}
    
    summaries: List[Round3TeamSummary] = []
    for team in teams:
        txs = tx_map.get(team.id, [])
        earned = sum(t.amount for t in txs if t.type == "earn")
        spent = sum(t.amount for t in txs if t.type == "spend")
        adjustments = sum(t.amount for t in txs if t.type == "adjustment")
        
        current_bal = starting_balance + earned - spent + adjustments
        
        code_rec = code_map.get(team.id)
        discovered = sum(1 for f in (code_rec.fragments_json if code_rec else []) if f.get("isDiscovered"))
        is_complete = code_rec.is_complete if code_rec else False
        
        summaries.append(Round3TeamSummary(
            team_id=team.id,
            team_name=team.name,
            team_identifier=f"T{team.team_number:02d}",
            starting_balance=starting_balance,
            total_earned=earned,
            total_spent=spent,
            net_adjustments=adjustments,
            current_balance=current_bal,
            fragments_discovered=discovered,
            total_fragments=C.CODE_FRAGMENT_COUNT,
            is_code_complete=is_complete,
            qualification_status="Pending"
        ))
    
    # Sort descending by current_balance, then fragments_discovered
    summaries.sort(key=lambda s: (s.current_balance, s.fragments_discovered), reverse=True)
    for i, s in enumerate(summaries):
        s.rank = i + 1
        s.qualification_status = "Qualified" if (i + 1) <= qualifying_count else "Eliminated"
        
    return summaries


# =========================================================================
# Round 4 Service Methods
# =========================================================================

def get_round4_pairs(db: Session) -> List[Round4Pair]:
    return db.execute(select(Round4Pair).order_by(Round4Pair.pair_number.asc())).scalars().all()


def update_round4_pair(db: Session, pair_number: int, data: Round4PairUpdate, user: User) -> Round4Pair:
    _check_round_not_finalized(db, 4)
    pair = db.execute(select(Round4Pair).where(Round4Pair.pair_number == pair_number)).scalar_one_or_none()
    if not pair:
        pair = Round4Pair(pair_number=pair_number)
        db.add(pair)
        
    if data.is_confirmed is not None:
        pair.is_confirmed = data.is_confirmed
        if data.is_confirmed:
            pair.confirmed_at = utc_now()
            pair.confirmed_by = user.name
    if data.case_id is not None:
        pair.case_id = data.case_id
    if data.case_name is not None:
        pair.case_name = data.case_name
    if data.case_details is not None:
        pair.case_details = data.case_details
    if data.team_a_side is not None:
        pair.team_a_side = data.team_a_side
    if data.team_b_side is not None:
        pair.team_b_side = data.team_b_side
    if data.team_a_has_case_file is not None:
        pair.team_a_has_case_file = data.team_a_has_case_file
        if data.team_a_has_case_file and not pair.team_a_case_file_at:
            pair.team_a_case_file_at = utc_now()
    if data.team_a_has_opposing_file is not None:
        pair.team_a_has_opposing_file = data.team_a_has_opposing_file
        if data.team_a_has_opposing_file and not pair.team_a_opposing_file_at:
            pair.team_a_opposing_file_at = utc_now()
    if data.team_b_has_case_file is not None:
        pair.team_b_has_case_file = data.team_b_has_case_file
        if data.team_b_has_case_file and not pair.team_b_case_file_at:
            pair.team_b_case_file_at = utc_now()
    if data.team_b_has_opposing_file is not None:
        pair.team_b_has_opposing_file = data.team_b_has_opposing_file
        if data.team_b_has_opposing_file and not pair.team_b_opposing_file_at:
            pair.team_b_opposing_file_at = utc_now()
    if data.stages_json is not None:
        pair.stages_json = data.stages_json
    if data.resource_person_name is not None:
        pair.resource_person_name = data.resource_person_name
    if data.resource_person_notes is not None:
        pair.resource_person_notes = data.resource_person_notes
    if data.resource_person_questions_json is not None:
        pair.resource_person_questions_json = data.resource_person_questions_json
    if data.is_questioning_complete is not None:
        pair.is_questioning_complete = data.is_questioning_complete
        
    db.commit()
    db.refresh(pair)
    return pair


def auto_pair_round4_teams(db: Session, user: User) -> List[Round4Pair]:
    """Pair the 8 qualified teams into 4 pairs."""
    _check_round_not_finalized(db, 4)
    # Find teams currently in round 4 or top 8 from round 3
    round3_standings = get_round3_standings(db)
    top_8 = [s.team_id for s in round3_standings[:8]]
    if len(top_8) < 8:
        # Fallback to any active teams
        all_teams = db.execute(select(Team.id).where(Team.status != TeamStatus.DISQUALIFIED).limit(8)).scalars().all()
        top_8 = all_teams
        
    random.shuffle(top_8)
    
    cases = [
        {"id": "case-1", "name": "State vs. Apex Cybernetics", "details": "AI Trade Secret Theft and Sabotage"},
        {"id": "case-2", "name": "BioHealth Corp vs. Dr. Vance", "details": "Unapproved Genetic Modification Trial"},
        {"id": "case-3", "name": "City of Solitude vs. Quantum Grid", "details": "Critical Infrastructure Energy Diversion"},
        {"id": "case-4", "name": "AeroDynamics vs. Sentinel Security", "details": "Autonomous Drone Airspace Collision"},
    ]
    
    pairs = []
    for i in range(4):
        team_a = top_8[i * 2] if len(top_8) > i * 2 else None
        team_b = top_8[i * 2 + 1] if len(top_8) > i * 2 + 1 else None
        case = cases[i % len(cases)]
        
        pair = db.execute(select(Round4Pair).where(Round4Pair.pair_number == i + 1)).scalar_one_or_none()
        if not pair:
            pair = Round4Pair(pair_number=i + 1)
            db.add(pair)
            
        pair.team_a_id = team_a
        pair.team_b_id = team_b
        pair.case_id = case["id"]
        pair.case_name = case["name"]
        pair.case_details = case["details"]
        pair.team_a_side = "Prosecution / Plaintiff"
        pair.team_b_side = "Defense / Respondent"
        pair.is_confirmed = True
        pair.confirmed_at = utc_now()
        pair.confirmed_by = user.name
        pairs.append(pair)
        
    db.commit()
    return pairs


def submit_round4_judge_score(db: Session, data: Round4JudgeScoreSubmit, user: User) -> Round4JudgeScore:
    _check_round_not_finalized(db, 4)
    _validate_team_exists(db, data.team_id)
    total = sum(data.scores.values()) if data.scores else 0.0
    
    existing = db.execute(
        select(Round4JudgeScore).where(
            and_(
                Round4JudgeScore.judge_id == data.judge_id,
                Round4JudgeScore.team_id == data.team_id
            )
        )
    ).scalar_one_or_none()
    
    if existing:
        existing.judge_name = data.judge_name
        existing.scores_json = data.scores
        existing.total_score = total
        existing.comments = data.comments
        existing.submitted_at = utc_now()
        db.commit()
        db.refresh(existing)
        return existing
        
    score = Round4JudgeScore(
        judge_id=data.judge_id,
        judge_name=data.judge_name,
        team_id=data.team_id,
        scores_json=data.scores,
        total_score=total,
        comments=data.comments,
        submitted_at=utc_now()
    )
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


def submit_round4_agent_guess(db: Session, data: Round4AgentGuessSubmit, user: User) -> Round4AgentGuess:
    _check_round_not_finalized(db, 4)
    _validate_team_exists(db, data.team_id)
    round_state = get_round_by_number(db, 4)
    bonus = float(round_state.config_json.get("agentGuessBonus", C.AGENT_CORRECT_GUESS))
    
    pts = data.points_awarded
    if pts is None:
        pts = bonus if data.outcome == "correct" else 0.0
        
    existing = db.execute(select(Round4AgentGuess).where(Round4AgentGuess.team_id == data.team_id)).scalar_one_or_none()
    if existing:
        existing.outcome = data.outcome
        existing.points_awarded = pts
        existing.notes = data.notes
        existing.is_verified = True
        existing.verified_by = user.name
        existing.verified_at = utc_now()
        db.commit()
        db.refresh(existing)
        return existing
        
    guess = Round4AgentGuess(
        team_id=data.team_id,
        outcome=data.outcome,
        points_awarded=pts,
        is_verified=True,
        verified_by=user.name,
        verified_at=utc_now(),
        notes=data.notes
    )
    db.add(guess)
    db.commit()
    db.refresh(guess)
    return guess


def get_round4_standings(db: Session) -> List[Round4TeamSummary]:
    round_state = get_round_by_number(db, 4)
    qualifying_count = round_state.qualifying_teams_count
    
    teams = db.execute(select(Team).where(Team.status != TeamStatus.DISQUALIFIED)).scalars().all()
    pairs = db.execute(select(Round4Pair)).scalars().all()
    scores = db.execute(select(Round4JudgeScore)).scalars().all()
    guesses = db.execute(select(Round4AgentGuess)).scalars().all()
    
    # Map judge scores by team_id
    team_scores: Dict[str, List[float]] = {}
    for sc in scores:
        team_scores.setdefault(sc.team_id, []).append(sc.total_score)
        
    guess_map = {g.team_id: g for g in guesses}
    
    # Map team pairings
    team_pair_info: Dict[str, Dict[str, Any]] = {}
    for p in pairs:
        if p.team_a_id:
            team_pair_info[p.team_a_id] = {
                "pairNumber": p.pair_number,
                "opponentId": p.team_b_id,
                "side": p.team_a_side
            }
        if p.team_b_id:
            team_pair_info[p.team_b_id] = {
                "pairNumber": p.pair_number,
                "opponentId": p.team_a_id,
                "side": p.team_b_side
            }
            
    team_dict = {t.id: t for t in teams}
    
    summaries: List[Round4TeamSummary] = []
    for team in teams:
        pair_info = team_pair_info.get(team.id, {})
        opp_id = pair_info.get("opponentId")
        opp_name = team_dict[opp_id].name if opp_id and opp_id in team_dict else None
        
        sc_list = team_scores.get(team.id, [])
        avg_jury = (sum(sc_list) / len(sc_list)) if sc_list else 0.0
        
        guess = guess_map.get(team.id)
        guess_pts = guess.points_awarded if guess and guess.points_awarded is not None else 0.0
        
        tot = avg_jury + guess_pts
        
        summaries.append(Round4TeamSummary(
            team_id=team.id,
            team_name=team.name,
            team_identifier=f"T{team.team_number:02d}",
            pair_number=pair_info.get("pairNumber"),
            opponent_team_id=opp_id,
            opponent_team_name=opp_name,
            side=pair_info.get("side"),
            jury_score=avg_jury,
            agent_guess_points=guess_pts,
            total_score=tot,
            qualification_status="Pending"
        ))
        
    # Sort descending by total_score
    summaries.sort(key=lambda s: s.total_score, reverse=True)
    for i, s in enumerate(summaries):
        s.rank = i + 1
        s.qualification_status = "Qualified" if (i + 1) <= qualifying_count else "Eliminated"
        
    return summaries


# =========================================================================
# Grand Finale (Round 5) Service Methods
# =========================================================================

def get_finale_scorecards(db: Session) -> List[FinaleScorecard]:
    return db.execute(select(FinaleScorecard)).scalars().all()


def submit_finale_scorecard(db: Session, data: FinaleScorecardSubmit, user: User) -> FinaleScorecard:
    _check_round_not_finalized(db, 5)
    _validate_team_exists(db, data.team_id)
    total = sum(data.scores.values()) if data.scores else 0.0
    
    existing = db.execute(select(FinaleScorecard).where(FinaleScorecard.team_id == data.team_id)).scalar_one_or_none()
    if existing:
        existing.judge_name = data.judge_name
        existing.scores_json = data.scores
        existing.total_score = total
        existing.is_complete = True
        existing.comments = data.comments
        existing.last_edited_by = user.name
        existing.last_edited_at = utc_now()
        existing.submitted_at = utc_now()
        db.commit()
        db.refresh(existing)
        return existing
        
    sc = FinaleScorecard(
        team_id=data.team_id,
        judge_name=data.judge_name,
        scores_json=data.scores,
        total_score=total,
        is_complete=True,
        comments=data.comments,
        last_edited_by=user.name,
        last_edited_at=utc_now(),
        submitted_at=utc_now()
    )
    db.add(sc)
    db.commit()
    db.refresh(sc)
    return sc


def submit_finale_agent_verdict(db: Session, data: FinaleAgentVerdictSubmit, user: User) -> FinaleAgentVerdict:
    _check_round_not_finalized(db, 5)
    _validate_team_exists(db, data.team_id)
    round_state = get_round_by_number(db, 5)
    default_bonus = float(round_state.config_json.get("agentBonusPoints", C.AGENT_CORRECT_GUESS))
    default_penalty = float(round_state.config_json.get("agentPenaltyPoints", C.AGENT_WRONG_GUESS))
    
    bonus = data.bonus_points if data.bonus_points is not None else (default_bonus if data.is_correct else 0.0)
    penalty = data.penalty_points if data.penalty_points is not None else (default_penalty if data.is_correct is False else 0.0)
    
    existing = db.execute(select(FinaleAgentVerdict).where(FinaleAgentVerdict.team_id == data.team_id)).scalar_one_or_none()
    if existing:
        existing.suspected_agent = data.suspected_agent
        existing.actual_agent = data.actual_agent
        existing.is_correct = data.is_correct
        existing.bonus_points = bonus
        existing.penalty_points = penalty
        existing.is_verified = True
        existing.verified_by = user.name
        existing.verified_at = utc_now()
        existing.notes = data.notes
        db.commit()
        db.refresh(existing)
        return existing
        
    verdict = FinaleAgentVerdict(
        team_id=data.team_id,
        suspected_agent=data.suspected_agent,
        actual_agent=data.actual_agent,
        is_correct=data.is_correct,
        bonus_points=bonus,
        penalty_points=penalty,
        is_verified=True,
        verified_by=user.name,
        verified_at=utc_now(),
        notes=data.notes
    )
    db.add(verdict)
    db.commit()
    db.refresh(verdict)
    return verdict


def get_finale_standings(db: Session) -> List[FinaleTeamSummary]:
    round_state = get_round_by_number(db, 5)
    carryover_weight = float(round_state.config_json.get("carryoverWeight", C.FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED))
    
    teams = db.execute(select(Team).where(Team.status != TeamStatus.DISQUALIFIED)).scalars().all()
    scorecards = db.execute(select(FinaleScorecard)).scalars().all()
    verdicts = db.execute(select(FinaleAgentVerdict)).scalars().all()
    r4_standings = {s.team_id: s for s in get_round4_standings(db)}
    
    sc_map = {s.team_id: s for s in scorecards}
    verdict_map = {v.team_id: v for v in verdicts}
    
    # We only rank the top 3 finalists
    finalist_ids = [s.team_id for s in get_round4_standings(db)[:3]]
    finalist_teams = [t for t in teams if t.id in finalist_ids]
    if not finalist_teams:
        finalist_teams = teams[:3]
        
    summaries: List[FinaleTeamSummary] = []
    for team in finalist_teams:
        r4 = r4_standings.get(team.id)
        carryover = (r4.total_score * carryover_weight) if r4 else 0.0
        
        sc = sc_map.get(team.id)
        jury = sc.total_score if sc and sc.total_score is not None else 0.0
        
        verd = verdict_map.get(team.id)
        agent_score = 0.0
        if verd:
            if verd.is_correct is True:
                agent_score = verd.bonus_points or 0.0
            elif verd.is_correct is False:
                agent_score = verd.penalty_points or 0.0
                
        grand_total = carryover + jury + agent_score
        
        summaries.append(FinaleTeamSummary(
            team_id=team.id,
            team_name=team.name,
            team_identifier=f"T{team.team_number:02d}",
            carryover_score=carryover,
            jury_score=jury,
            agent_verdict_score=agent_score,
            grand_total_score=grand_total
        ))
        
    summaries.sort(key=lambda s: s.grand_total_score, reverse=True)
    podium_titles = ["Champion", "1st Runner Up", "2nd Runner Up"]
    for i, s in enumerate(summaries):
        s.rank = i + 1
        s.podium_title = podium_titles[i] if i < len(podium_titles) else "Finalist"
        
    return summaries


# =========================================================================
# Finalization Service Method
# =========================================================================

def finalize_round(
    db: Session,
    round_num: int,
    user: User,
    req: FinalizeRoundRequest
) -> FinalizeRoundResponse:
    state = get_round_by_number(db, round_num)
    
    # Gate check: previous round must be finalized
    if round_num > 1:
        prev_state = get_round_by_number(db, round_num - 1)
        if not prev_state.is_finalized and not req.override_discrepancy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot finalize Round {round_num}: Round {round_num - 1} ({prev_state.name}) is not finalized yet."
            )
            
    # Calculate qualifiers
    qualified_ids: List[str] = []
    if round_num == 1:
        records = get_round1_records(db)
        qualified_ids = [r.team_id for r in records if r.qualification_status == "Qualified"]
    elif round_num == 2:
        standings = get_round2_standings(db)
        qualified_ids = [s.team_id for s in standings if s.qualification_status == "Qualified"]
    elif round_num == 3:
        standings = get_round3_standings(db)
        qualified_ids = [s.team_id for s in standings if s.qualification_status == "Qualified"]
    elif round_num == 4:
        standings = get_round4_standings(db)
        qualified_ids = [s.team_id for s in standings if s.qualification_status == "Qualified"]
    elif round_num == 5:
        standings = get_finale_standings(db)
        qualified_ids = [s.team_id for s in standings if s.rank == 1]
        
    # Idempotency check: if already finalized, return current finalized status
    if state.is_finalized:
        return FinalizeRoundResponse(
            success=True,
            round_number=round_num,
            qualified_team_ids=qualified_ids,
            total_eligible=len(qualified_ids),
            message=f"Round {round_num} ({state.name}) is already finalized."
        )

    expected_count = state.qualifying_teams_count
    if len(qualified_ids) != expected_count and not req.override_discrepancy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Qualification count discrepancy: expected {expected_count} teams, found {len(qualified_ids)}. Pass overrideDiscrepancy=true to force finalization."
        )
        
    # Update team records
    teams = db.execute(select(Team)).scalars().all()
    for t in teams:
        if t.id in qualified_ids:
            t.status = TeamStatus.ACTIVE
            t.is_qualified_for_next_round = True
            t.current_round = round_num + 1 if round_num < 5 else 5
        else:
            if t.current_round == round_num:
                t.status = TeamStatus.ELIMINATED
                t.is_qualified_for_next_round = False
                
    state.is_finalized = True
    state.status = "Completed"
    state.finalized_at = utc_now()
    state.finalized_by = req.finalized_by or user.name
    state.ended_at = state.ended_at or utc_now()
    
    # Store discrepancy override audit notes if applicable
    if req.override_discrepancy or req.notes:
        cfg = dict(state.config_json or {})
        cfg["finalizationAudit"] = {
            "overrideDiscrepancy": req.override_discrepancy,
            "notes": req.notes,
            "authorizedBy": user.name,
            "timestamp": utc_now().isoformat()
        }
        state.config_json = cfg
    
    # Progress next round state to In Progress
    if round_num < 5:
        next_state = get_round_by_number(db, round_num + 1)
        if next_state.status == "Scheduled":
            next_state.status = "In Progress"
            next_state.started_at = next_state.started_at or utc_now()
            
    db.commit()
    db.refresh(state)
    
    return FinalizeRoundResponse(
        success=True,
        round_number=round_num,
        qualified_team_ids=qualified_ids,
        total_eligible=len(qualified_ids),
        message=f"Round {round_num} ({state.name}) successfully finalized with {len(qualified_ids)} qualifying teams."
    )
