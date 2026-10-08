"""Live Round 2 Cabo control surface, separate from the legacy tournament routes."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.routes.r1_event import BASE_POINTS, current_account, require_roles
from app.db.session import get_db
from app.models.event_account import EventAccount, EventRole, Round1FinishOutcome
from app.models.participant import Participant
from app.models.round2_live import Round2CaboScore, Round2CaboSeat, Round2CaboTable, Round2LiveAudit, Round2LiveConfig, Round2TeamAward
from app.models.team import Team

router = APIRouter(prefix="/r2", tags=["Round 2 Live Cabo"])
QUALIFIER_COUNT = 16
# These invited teams join the sixteen Round 1 qualifiers for Round 2.
EXTRA_TEAM_IDENTIFIERS = ("1005", "1009", "1019")
TABLE_COUNT = QUALIFIER_COUNT + len(EXTRA_TEAM_IDENTIFIERS)
TABLE_SIZE = 5
WIN_POINTS = 40.0
LOSS_POINTS = -40.0
AWARD_START = 80.0
AWARD_STEP = 5.0
THREE_TABLE_ADMIN_IDS = frozenset({"ADMIN01", "ADMIN02", "ADMIN03"})


class TableAssignmentInput(BaseModel):
    admin_login_id: str = Field(min_length=3, max_length=40)
    table_numbers: list[int] = Field(min_length=2, max_length=3)


class AdminAssignmentBatch(BaseModel):
    assignments: list[TableAssignmentInput] = Field(min_length=8, max_length=8)


class SeatScoreInput(BaseModel):
    participant_id: str
    outcome: Literal["WIN", "LOSS"]


class TableScoresInput(BaseModel):
    scores: list[SeatScoreInput] = Field(min_length=5, max_length=5)


def now() -> datetime:
    return datetime.now(timezone.utc)


def config(db: Session) -> Round2LiveConfig:
    item = db.query(Round2LiveConfig).filter(Round2LiveConfig.id == 1).first()
    if not item:
        item = Round2LiveConfig(id=1)
        db.add(item)
        db.commit()
        db.refresh(item)
    return item


def round2_teams(db: Session) -> list[Team]:
    outcomes = db.query(Round1FinishOutcome).filter(Round1FinishOutcome.is_qualified.is_(True)).order_by(Round1FinishOutcome.rank).all()
    if len(outcomes) != QUALIFIER_COUNT:
        raise HTTPException(status_code=409, detail="Round 2 needs exactly 16 qualified Round 1 teams before tables can be generated.")
    qualifier_ids = [outcome.team_id for outcome in outcomes]
    teams = {team.id: team for team in db.query(Team).filter(Team.id.in_(qualifier_ids)).all()}
    ordered = [teams[item] for item in qualifier_ids if item in teams]
    if len(ordered) != QUALIFIER_COUNT:
        raise HTTPException(status_code=409, detail="One or more qualified teams are missing from the roster.")
    extras = db.query(Team).filter(Team.team_number.in_([int(item) - 1000 for item in EXTRA_TEAM_IDENTIFIERS])).all()
    by_identifier = {f"{1000 + team.team_number}": team for team in extras}
    if set(by_identifier) != set(EXTRA_TEAM_IDENTIFIERS):
        raise HTTPException(status_code=409, detail="One or more invited Round 2 teams are missing from the roster.")
    overlapping = [item for item in EXTRA_TEAM_IDENTIFIERS if by_identifier[item].id in qualifier_ids]
    if overlapping:
        raise HTTPException(status_code=409, detail=f"Invited team(s) {', '.join('TEAM' + item for item in overlapping)} already qualified in the top 16. Choose a replacement team so Round 2 has 19 unique teams.")
    return ordered + [by_identifier[item] for item in EXTRA_TEAM_IDENTIFIERS]


def tables_for_admin(login_id: str) -> int:
    return 3 if login_id.strip().upper() in THREE_TABLE_ADMIN_IDS else 2


def members_for(team: Team, db: Session) -> list[Participant]:
    members = db.query(Participant).filter(Participant.team_id == team.id).order_by(Participant.name, Participant.id).all()
    if len(members) != TABLE_SIZE:
        raise HTTPException(status_code=409, detail=f"{team.name} must have exactly five roster members for Cabo.")
    return members


def tables_payload(db: Session, tables: list[Round2CaboTable]) -> list[dict]:
    """Load all table details in bulk so the live Supabase database is not queried once per seat."""
    if not tables:
        return []

    table_ids = [table.id for table in tables]
    admin_ids = {table.assigned_admin_id for table in tables if table.assigned_admin_id}
    admins = {
        item.id: item
        for item in db.query(EventAccount).filter(EventAccount.id.in_(admin_ids)).all()
    } if admin_ids else {}
    seats = db.query(Round2CaboSeat).filter(Round2CaboSeat.table_id.in_(table_ids)).order_by(
        Round2CaboSeat.table_id, Round2CaboSeat.seat_position
    ).all()
    participants = {
        item.id: item
        for item in db.query(Participant).filter(Participant.id.in_({seat.participant_id for seat in seats})).all()
    } if seats else {}
    teams = {
        item.id: item
        for item in db.query(Team).filter(Team.id.in_({seat.team_id for seat in seats})).all()
    } if seats else {}
    scores = {
        item.seat_id: item
        for item in db.query(Round2CaboScore).filter(Round2CaboScore.seat_id.in_({seat.id for seat in seats})).all()
    } if seats else {}
    seats_by_table: dict[str, list[Round2CaboSeat]] = {table.id: [] for table in tables}
    for seat in seats:
        seats_by_table.setdefault(seat.table_id, []).append(seat)

    payloads = []
    for table in tables:
        admin = admins.get(table.assigned_admin_id)
        players = []
        for seat in seats_by_table.get(table.id, []):
            participant = participants.get(seat.participant_id)
            team = teams.get(seat.team_id)
            score = scores.get(seat.id)
            players.append({
                "participant_id": seat.participant_id,
                "participant_name": participant.name if participant else "Unknown member",
                "team_id": seat.team_id,
                "team_identifier": f"TEAM{1000 + team.team_number}" if team else "Unknown team",
                "team_name": team.name if team else "Unknown team",
                "seat_position": seat.seat_position,
                "outcome": score.outcome if score else None,
                "base_points": score.base_points if score else None,
            })
        payloads.append({
            "table_number": table.table_number,
            "admin_login_id": admin.login_id if admin else None,
            "admin_name": admin.display_name if admin else None,
            "players": players,
            "complete": len(players) == TABLE_SIZE and all(item["outcome"] for item in players),
        })
    return payloads


def table_payload(db: Session, table: Round2CaboTable) -> dict:
    return tables_payload(db, [table])[0]


def r1_points(db: Session, team_id: str) -> float:
    outcome = db.query(Round1FinishOutcome).filter(Round1FinishOutcome.team_id == team_id).first()
    if outcome:
        return outcome.points_snapshot
    return BASE_POINTS


def recompute_team_total(db: Session, team_id: str) -> float:
    base_result = db.query(func.coalesce(func.sum(Round2CaboScore.base_points), 0.0)).join(
        Round2CaboSeat, Round2CaboSeat.id == Round2CaboScore.seat_id
    ).filter(Round2CaboSeat.team_id == team_id).scalar()
    award = db.query(Round2TeamAward).filter(Round2TeamAward.team_id == team_id).first()
    total = r1_points(db, team_id) + float(base_result or 0.0) + (award.points if award else 0.0)
    team = db.query(Team).filter(Team.id == team_id).first()
    if team:
        team.total_score = total
    return total


def standings(db: Session) -> list[dict]:
    teams = round2_teams(db)
    outcomes = {item.team_id: item for item in db.query(Round1FinishOutcome).filter(Round1FinishOutcome.is_qualified.is_(True)).all()}
    team_ids = [team.id for team in teams]
    score_totals = {
        team_id: float(points or 0.0)
        for team_id, points in db.query(
            Round2CaboSeat.team_id,
            func.coalesce(func.sum(Round2CaboScore.base_points), 0.0),
        ).outerjoin(
            Round2CaboScore, Round2CaboScore.seat_id == Round2CaboSeat.id
        ).filter(Round2CaboSeat.team_id.in_(team_ids)).group_by(Round2CaboSeat.team_id).all()
    }
    awards = {
        item.team_id: item
        for item in db.query(Round2TeamAward).filter(Round2TeamAward.team_id.in_(team_ids)).all()
    }
    rows = []
    for team in teams:
        cabo_points = score_totals.get(team.id, 0.0)
        award = awards.get(team.id)
        first_round_points = outcomes[team.id].points_snapshot if team.id in outcomes else BASE_POINTS
        rows.append({
            "team_id": team.id,
            "team_identifier": f"TEAM{1000 + team.team_number}",
            "team_name": team.name,
            "r1_rank": outcomes[team.id].rank if team.id in outcomes else None,
            "r1_points": first_round_points,
            "cabo_points": cabo_points,
            "rank_award": award.points if award else 0.0,
            "rank": award.rank if award else None,
            "total_points": first_round_points + cabo_points + (award.points if award else 0.0),
        })
    return sorted(rows, key=lambda item: (-item["cabo_points"], item["r1_rank"] or 9999, item["team_identifier"]))


def audit(db: Session, account: EventAccount, action: str, detail: str) -> None:
    db.add(Round2LiveAudit(action=action, detail=detail, performed_by=account.id))


@router.get("/control/overview")
def overview(account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    cfg = config(db)
    tables = db.query(Round2CaboTable).order_by(Round2CaboTable.table_number).all()
    return {"success": True, "data": {
        "generated": bool(cfg.tables_generated_at), "finalized": cfg.is_finalized,
        "tables": tables_payload(db, tables), "standings": standings(db) if cfg.tables_generated_at else [],
        "award_scale": [AWARD_START - AWARD_STEP * offset for offset in range(TABLE_COUNT)],
    }, "message": "Round 2 control loaded."}


@router.post("/control/generate")
def generate(account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    cfg = config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=409, detail="Round 2 is finalized and cannot be regenerated.")
    if cfg.tables_generated_at:
        raise HTTPException(status_code=409, detail="Round 2 tables already exist. Use the existing assignments.")
    teams = round2_teams(db)
    members = {team.id: members_for(team, db) for team in teams}
    admins = db.query(EventAccount).filter(EventAccount.role == EventRole.ADMIN, EventAccount.is_active.is_(True)).order_by(EventAccount.login_id).all()
    if len(admins) != 8:
        raise HTTPException(status_code=409, detail="Round 2 needs exactly eight active admin accounts.")
    tables = []
    table_number = 1
    for admin in admins:
        for _ in range(tables_for_admin(admin.login_id)):
            tables.append(Round2CaboTable(table_number=table_number, assigned_admin_id=admin.id))
            table_number += 1
    if len(tables) != TABLE_COUNT:
        raise HTTPException(status_code=409, detail="Admin allocation must provide 19 tables: ADMIN01–ADMIN03 get three each and ADMIN04–ADMIN08 get two each.")
    db.add_all(tables)
    db.flush()
    member_index = {team.id: 0 for team in teams}
    seats: list[Round2CaboSeat] = []
    for table_index, table in enumerate(tables):
        for seat_index, team_offset in enumerate(range(TABLE_SIZE), start=1):
            team = teams[(table_index + team_offset) % TABLE_COUNT]
            player = members[team.id][member_index[team.id]]
            member_index[team.id] += 1
            seats.append(Round2CaboSeat(table_id=table.id, participant_id=player.id, team_id=team.id, seat_position=seat_index))
    db.add_all(seats)
    cfg.tables_generated_at = now()
    cfg.generated_by = account.id
    audit(db, account, "GENERATE_TABLES", "Generated 19 Round 2 Cabo tables for the 16 qualifiers plus TEAM1005, TEAM1009, and TEAM1019; every table contains five distinct teams.")
    db.commit()
    return {"success": True, "data": {"tables_created": TABLE_COUNT, "seats_created": len(seats)}, "message": "Nineteen Cabo tables are ready: ADMIN01–ADMIN03 have three tables each; ADMIN04–ADMIN08 have two each."}


@router.post("/control/assign-admins")
def assign_admins(payload: AdminAssignmentBatch, account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    cfg = config(db)
    if not cfg.tables_generated_at or cfg.is_finalized:
        raise HTTPException(status_code=409, detail="Round 2 tables must be generated and unlocked before assigning admins.")
    claimed = [number for item in payload.assignments for number in item.table_numbers]
    if sorted(claimed) != list(range(1, TABLE_COUNT + 1)):
        raise HTTPException(status_code=422, detail="Assign every table exactly once.")
    admins = {item.login_id: item for item in db.query(EventAccount).filter(EventAccount.role == EventRole.ADMIN, EventAccount.is_active.is_(True)).all()}
    supplied_ids = {item.admin_login_id.strip().upper() for item in payload.assignments}
    if supplied_ids != set(admins) or len(supplied_ids) != 8:
        raise HTTPException(status_code=422, detail="Use each of the eight admins exactly once.")
    for item in payload.assignments:
        admin_id = item.admin_login_id.strip().upper()
        admin = admins.get(admin_id)
        if not admin:
            raise HTTPException(status_code=404, detail=f"Admin {item.admin_login_id} was not found.")
        if len(item.table_numbers) != tables_for_admin(admin_id):
            raise HTTPException(status_code=422, detail=f"{admin_id} must be assigned {tables_for_admin(admin_id)} tables.")
        db.query(Round2CaboTable).filter(Round2CaboTable.table_number.in_(item.table_numbers)).update({Round2CaboTable.assigned_admin_id: admin.id}, synchronize_session=False)
    audit(db, account, "ASSIGN_TABLES", "Updated the 19-table Round 2 allocation: ADMIN01–ADMIN03 have three tables and ADMIN04–ADMIN08 have two.")
    db.commit()
    return {"success": True, "data": {"assigned_tables": TABLE_COUNT}, "message": "Round 2 table-admin assignments saved."}


@router.post("/control/apply-rank-awards")
def apply_rank_awards(account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    cfg = config(db)
    if not cfg.tables_generated_at or cfg.is_finalized:
        raise HTTPException(status_code=409, detail="Round 2 must be generated and unlocked before applying leaderboard awards.")
    existing = db.query(Round2TeamAward).count()
    if existing:
        db.query(Round2TeamAward).delete(synchronize_session=False)
        db.flush()
    ordered = standings(db)
    for index, row in enumerate(ordered, start=1):
        # Rank awards never become penalties: ranks 17–19 receive zero.
        points = max(0.0, AWARD_START - AWARD_STEP * (index - 1))
        db.add(Round2TeamAward(team_id=row["team_id"], rank=index, points=points, applied_by=account.id))
        db.flush()
        recompute_team_total(db, row["team_id"])
    audit(db, account, "APPLY_RANK_AWARDS", "Applied 80, 75, ... 0 Cabo leaderboard awards to the 19 Round 2 teams.")
    db.commit()
    return {"success": True, "data": {"awards_applied": TABLE_COUNT}, "message": "Round 2 ranking awards applied to all 19 team totals."}


@router.post("/control/finalize")
def finalize(account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)), db: Session = Depends(get_db)):
    cfg = config(db)
    if not cfg.tables_generated_at:
        raise HTTPException(status_code=409, detail="Generate the Round 2 tables first.")
    incomplete = db.query(Round2CaboSeat).outerjoin(Round2CaboScore, Round2CaboScore.seat_id == Round2CaboSeat.id).filter(Round2CaboScore.id.is_(None)).count()
    if incomplete:
        raise HTTPException(status_code=409, detail=f"{incomplete} player results are still missing.")
    if db.query(Round2TeamAward).count() != TABLE_COUNT:
        raise HTTPException(status_code=409, detail="Apply the Round 2 leaderboard awards before finalizing.")
    cfg.is_finalized = True
    cfg.finalized_at = now()
    cfg.finalized_by = account.id
    audit(db, account, "FINALIZE", "Round 2 locked after all 95 player outcomes and ranking awards were recorded.")
    db.commit()
    return {"success": True, "data": {"finalized": True}, "message": "Round 2 is finalized and locked."}


@router.get("/admin/tables")
def admin_tables(account: EventAccount = Depends(require_roles(EventRole.ADMIN)), db: Session = Depends(get_db)):
    cfg = config(db)
    tables = db.query(Round2CaboTable).filter(Round2CaboTable.assigned_admin_id == account.id).order_by(Round2CaboTable.table_number).all()
    return {"success": True, "data": {"available": bool(cfg.tables_generated_at and tables), "finalized": cfg.is_finalized, "tables": tables_payload(db, tables)}, "message": "Round 2 table assignment loaded."}


@router.post("/admin/tables/{table_number}/scores")
def record_scores(table_number: int, payload: TableScoresInput, account: EventAccount = Depends(require_roles(EventRole.ADMIN)), db: Session = Depends(get_db)):
    cfg = config(db)
    if not cfg.tables_generated_at or cfg.is_finalized:
        raise HTTPException(status_code=409, detail="Round 2 is not open for score entry.")
    table = db.query(Round2CaboTable).filter(Round2CaboTable.table_number == table_number).first()
    if not table or table.assigned_admin_id != account.id:
        raise HTTPException(status_code=403, detail="This table is not assigned to your admin account.")
    seats = db.query(Round2CaboSeat).filter(Round2CaboSeat.table_id == table.id).all()
    by_player = {seat.participant_id: seat for seat in seats}
    if set(item.participant_id for item in payload.scores) != set(by_player):
        raise HTTPException(status_code=422, detail="Enter one WIN or LOSS outcome for every player at this table.")
    for item in payload.scores:
        seat = by_player[item.participant_id]
        score = db.query(Round2CaboScore).filter(Round2CaboScore.seat_id == seat.id).first()
        points = WIN_POINTS if item.outcome == "WIN" else LOSS_POINTS
        if score:
            score.outcome = item.outcome
            score.base_points = points
            score.recorded_by = account.id
            score.recorded_at = now()
        else:
            db.add(Round2CaboScore(seat_id=seat.id, outcome=item.outcome, base_points=points, recorded_by=account.id))
        recompute_team_total(db, seat.team_id)
    audit(db, account, "RECORD_TABLE", f"Recorded Cabo WIN/LOSS results for Round 2 Table {table_number}.")
    db.commit()
    return {"success": True, "data": table_payload(db, table), "message": "Table results saved and team totals updated."}
