from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.models.round2 import CaboConfigModel, CaboGameModel, CaboPlacementModel, default_cabo_point_table
from app.models.core import Team
from app.models.progression import TieReview
from app.scoring.round2_scoring import process_round2_standings, compute_team_round2_points
from app.services.audit_service import log_audit_event
from app.services.progression_service import is_round_finalized, get_eligible_team_ids, record_round_finalization
from app.services.tie_review_service import get_or_create_tie_review
from app.schemas.rounds.round2 import RecordGamePlacementsInput

def get_or_create_cabo_config(db: Session) -> CaboConfigModel:
    cfg = db.query(CaboConfigModel).filter(CaboConfigModel.id == 1).first()
    if not cfg:
        cfg = CaboConfigModel(
            id=1,
            scoring_direction="higher_is_better",
            tie_policy="strict_unique",
            point_table=default_cabo_point_table(),
            is_finalized=False
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg

def ensure_cabo_games(db: Session):
    for i in range(1, 4):
        gid = f"r2-game-{i}"
        g = db.query(CaboGameModel).filter(CaboGameModel.id == gid).first()
        if not g:
            g = CaboGameModel(id=gid, game_number=i, name=f"Cabo Game {i}", is_completed=False)
            db.add(g)
    db.commit()

def update_cabo_config(db: Session, scoring_direction: Optional[str], point_table: Optional[Dict], actor) -> CaboConfigModel:
    cfg = get_or_create_cabo_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Round 2 is finalized. Configuration locked.")

    if scoring_direction:
        cfg.scoring_direction = scoring_direction
    if point_table:
        cfg.point_table = {str(k): float(v) for k, v in point_table.items()}

    log_audit_event(
        db=db,
        action="ROUND2_CONFIG_UPDATED",
        entity_type="CaboConfig",
        entity_id="1",
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=2,
        details={"scoring_direction": cfg.scoring_direction}
    )
    db.commit()
    db.refresh(cfg)
    return cfg

def record_game_placements(db: Session, game_number: int, input_data: RecordGamePlacementsInput, actor):
    cfg = get_or_create_cabo_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Round 2 is finalized. Edits locked.")

    if not is_round_finalized(db, 1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Round 1 is not yet finalized. Teams are not eligible for Round 2 until Round 1 is sealed."
        )

    eligible_team_ids = set(get_eligible_team_ids(db, 2))
    ensure_cabo_games(db)
    gid = f"r2-game-{game_number}"
    game = db.query(CaboGameModel).filter(CaboGameModel.id == gid).first()
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Game {game_number} not found.")

    # Validate all incoming teams are eligible
    for p in input_data.placements:
        if p.team_id not in eligible_team_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team '{p.team_id}' is not qualified from Round 1. Only qualified squads may compete in Round 2."
            )

    # Validate duplicate placements in submission
    submitted_placements = [p.placement for p in input_data.placements]
    if len(submitted_placements) != len(set(submitted_placements)):
        if cfg.tie_policy == "strict_unique":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate placements found in single Cabo game submission under strict_unique policy.")

    point_table = cfg.point_table or {}

    for p in input_data.placements:
        pid = f"r2-g{game_number}-{p.team_id}"
        placement_rec = db.query(CaboPlacementModel).filter(CaboPlacementModel.id == pid).first()
        pts = float(point_table.get(str(p.placement), 25 - p.placement))
        if not placement_rec:
            placement_rec = CaboPlacementModel(
                id=pid,
                game_id=gid,
                team_id=p.team_id,
                placement=p.placement,
                points=pts,
                notes=p.notes
            )
            db.add(placement_rec)
        else:
            placement_rec.placement = p.placement
            placement_rec.points = pts
            placement_rec.notes = p.notes

    # Check if all 24 eligible teams recorded
    all_game_placements = db.query(CaboPlacementModel).filter(CaboPlacementModel.game_id == gid).count()
    if all_game_placements >= 24:
        game.is_completed = True

    log_audit_event(
        db=db,
        action="CABO_GAME_PLACEMENTS_SAVED",
        entity_type="CaboGame",
        entity_id=gid,
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=2,
        details={"game_number": game_number, "placements_count": len(input_data.placements)}
    )
    db.commit()

def get_round2_overview(db: Session) -> Dict[str, Any]:
    cfg = get_or_create_cabo_config(db)
    ensure_cabo_games(db)
    r1_finalized = is_round_finalized(db, 1)
    eligible_team_ids = get_eligible_team_ids(db, 2)

    # Fetch teams
    teams = db.query(Team).filter(Team.id.in_(eligible_team_ids)).all() if eligible_team_ids else []
    # If R1 not finalized, display all 24 placeholder teams
    if not r1_finalized:
        teams = db.query(Team).limit(24).all()

    games = db.query(CaboGameModel).order_by(CaboGameModel.game_number.asc()).all()
    all_placements = db.query(CaboPlacementModel).all()
    placements_by_team_game = {}
    for p in all_placements:
        placements_by_team_game.setdefault(p.team_id, {})[p.game_id] = p

    raw_records = []
    for team in teams:
        team_p = placements_by_team_game.get(team.id, {})
        g1 = team_p.get("r2-game-1")
        g2 = team_p.get("r2-game-2")
        g3 = team_p.get("r2-game-3")

        record = compute_team_round2_points(
            team_id=team.id,
            team_number=team.team_number,
            team_name=team.name,
            round1_qualified=team.id in eligible_team_ids,
            games_placements=[
                g1.placement if g1 else None,
                g2.placement if g2 else None,
                g3.placement if g3 else None
            ],
            point_table=cfg.point_table
        )
        raw_records.append(record)

    standings = process_round2_standings(
        records=raw_records,
        config={
            "scoring_direction": cfg.scoring_direction,
            "point_table": cfg.point_table,
            "is_finalized": cfg.is_finalized
        },
        round1_finalized=r1_finalized
    )

    if standings.get("ties_affecting_cutoff"):
        tied_teams = [r for r in standings["records"] if r["team_id"] in standings["tied_teams_at_cutoff"]]
        get_or_create_tie_review(
            db=db,
            round_number=2,
            teams_involved=tied_teams,
            ranking_metric="total_points",
            cutoff_position=12,
            notes="Points tie straddles 12th and 13th place qualification cutoff for Round 3."
        )

    tie_rev = db.query(TieReview).filter(TieReview.id == "tie-r2-cutoff12").first()
    if tie_rev and tie_rev.review_status == "RESOLVED" and standings.get("ties_affecting_cutoff"):
        standings["can_finalize"] = len([i for i in standings["issues"] if i["code"] != "CUTOFF_TIE"]) == 0
        standings["issues"] = [i for i in standings["issues"] if i["code"] != "CUTOFF_TIE"]

    games_response = []
    for g in games:
        g_placements = [p for p in all_placements if p.game_id == g.id]
        games_response.append({
            "id": g.id,
            "game_number": g.game_number,
            "name": g.name,
            "is_completed": g.is_completed,
            "placements": {p.team_id: {"placement": p.placement, "points": p.points} for p in g_placements}
        })

    return {
        "config": {
            "scoring_direction": cfg.scoring_direction,
            "tie_policy": cfg.tie_policy,
            "point_table": cfg.point_table or {},
            "is_finalized": cfg.is_finalized,
            "finalized_at": cfg.finalized_at.isoformat() if cfg.finalized_at else None,
            "finalized_by": cfg.finalized_by
        },
        "games": games_response,
        "records": standings["records"],
        "can_finalize": standings["can_finalize"],
        "issues": standings["issues"],
        "ties_affecting_cutoff": standings["ties_affecting_cutoff"],
        "complete_count": standings["complete_count"],
        "incomplete_count": standings["incomplete_count"]
    }

def finalize_round2(db: Session, actor, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = get_or_create_cabo_config(db)
    if cfg.is_finalized:
        eligible = get_eligible_team_ids(db, 3)
        return {
            "can_finalize": True,
            "issues": [],
            "finalized": True,
            "advancing_team_ids": eligible,
            "message": "Round 2 is already finalized.",
            "success": True,
            "round_number": 2,
            "roundNumber": 2,
            "qualified_team_ids": eligible,
            "qualifiedTeamIds": eligible,
            "total_eligible": len(eligible) if eligible else 12,
            "totalEligible": len(eligible) if eligible else 12,
        }

    override = bool(payload and (payload.get("overrideDiscrepancy") or payload.get("override_discrepancy")))
    if not is_round_finalized(db, 1) and not override:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot finalize Round 2: Round 1 is not finalized yet."
        )

    overview = get_round2_overview(db)
    if not overview["can_finalize"] and not override:
        return {
            "can_finalize": False,
            "issues": overview["issues"],
            "finalized": False,
            "message": "Finalization blocked by server-side safeguards.",
            "success": False,
            "round_number": 2,
            "roundNumber": 2,
            "qualified_team_ids": [],
            "qualifiedTeamIds": [],
            "total_eligible": 0,
            "totalEligible": 0,
        }

    records = overview["records"]
    advancing_team_ids = [r["team_id"] for r in records if r.get("rank") and r["rank"] <= 12]

    tie_rev = db.query(TieReview).filter(TieReview.id == "tie-r2-cutoff12").first()
    if tie_rev and tie_rev.review_status == "RESOLVED" and tie_rev.advancing_team_ids:
        resolved_adv = set(tie_rev.advancing_team_ids)
        advancing_team_ids = [r["team_id"] for r in records if (r.get("rank") and r["rank"] < 12) or (r["team_id"] in resolved_adv)]

    if not advancing_team_ids and override:
        all_teams = db.query(Team).order_by(Team.team_number.asc()).limit(12).all()
        advancing_team_ids = [t.id for t in all_teams]

    record_round_finalization(
        db=db,
        round_number=2,
        records=records,
        advancing_team_ids=advancing_team_ids,
        finalized_by=actor.id
    )

    cfg.is_finalized = True
    cfg.finalized_at = datetime.now(timezone.utc)
    cfg.finalized_by = actor.id

    from app.services.round_service import ensure_round_states_initialized
    ensure_round_states_initialized(db)
    from app.models.round_models import RoundState
    rs = db.query(RoundState).filter(RoundState.id == 2).first()
    if rs:
        rs.is_finalized = True
        rs.finalized_at = cfg.finalized_at
        rs.finalized_by = actor.id
        rs.status = "Completed"

    log_audit_event(
        db=db,
        action="ROUND_FINALIZED",
        entity_type="CaboConfig",
        entity_id="1",
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=2,
        details={"advancing_team_ids": advancing_team_ids, "advancing_count": len(advancing_team_ids)}
    )
    db.commit()

    return {
        "can_finalize": True,
        "issues": [],
        "finalized": True,
        "advancing_team_ids": advancing_team_ids,
        "message": "Round 2 successfully finalized. 12 squads advance to Round 3: The Black Market.",
        "success": True,
        "round_number": 2,
        "roundNumber": 2,
        "qualified_team_ids": advancing_team_ids,
        "qualifiedTeamIds": advancing_team_ids,
        "total_eligible": len(advancing_team_ids),
        "totalEligible": len(advancing_team_ids),
    }
