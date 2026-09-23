from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.models.finale import (
    FinaleConfigModel, FinaleScorecardModel, FinaleAgentVerdictModel,
    default_finale_criteria
)
from app.models.core import Team
from app.models.progression import RoundQualification, TieReview
from app.scoring.finale_scoring import (
    calculate_scorecard_total, calculate_finale_score_breakdown, process_finale_standings
)
from app.services.audit_service import log_audit_event
from app.services.progression_service import is_round_finalized, get_eligible_team_ids, record_round_finalization
from app.services.tie_review_service import get_or_create_tie_review
from app.schemas.rounds.finale import SubmitScorecardInput, SubmitAgentVerdictInput

def get_or_create_finale_config(db: Session) -> FinaleConfigModel:
    cfg = db.query(FinaleConfigModel).filter(FinaleConfigModel.id == 1).first()
    if not cfg:
        cfg = FinaleConfigModel(
            id=1,
            is_scoring_rules_confirmed=False,
            criteria=default_finale_criteria(),
            round4_score_carried_over=True,
            round4_score_weight=0.2,
            finale_activity_weight=1.0,
            scoring_direction="higher_wins",
            is_finalized=False
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg

def update_finale_config(db: Session, updates: Dict[str, Any], actor) -> FinaleConfigModel:
    cfg = get_or_create_finale_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grand Finale is finalized. Configuration locked.")

    if "is_scoring_rules_confirmed" in updates and updates["is_scoring_rules_confirmed"] is not None:
        cfg.is_scoring_rules_confirmed = bool(updates["is_scoring_rules_confirmed"])
        if cfg.is_scoring_rules_confirmed and not cfg.confirmed_at:
            cfg.confirmed_at = datetime.now(timezone.utc)
            cfg.confirmed_by = actor.id
    if "criteria" in updates and updates["criteria"]:
        cfg.criteria = updates["criteria"]
    if "round4_score_carried_over" in updates and updates["round4_score_carried_over"] is not None:
        cfg.round4_score_carried_over = bool(updates["round4_score_carried_over"])
    if "round4_score_weight" in updates and updates["round4_score_weight"] is not None:
        cfg.round4_score_weight = float(updates["round4_score_weight"])
    if "finale_activity_weight" in updates and updates["finale_activity_weight"] is not None:
        cfg.finale_activity_weight = float(updates["finale_activity_weight"])
    if "agent_bonus_points_for_correct" in updates:
        cfg.agent_bonus_points_for_correct = updates["agent_bonus_points_for_correct"]
    if "agent_penalty_points_for_incorrect" in updates:
        cfg.agent_penalty_points_for_incorrect = updates["agent_penalty_points_for_incorrect"]
    if "scoring_direction" in updates and updates["scoring_direction"]:
        cfg.scoring_direction = updates["scoring_direction"]

    log_audit_event(
        db=db,
        action="FINALE_CONFIG_UPDATED",
        entity_type="FinaleConfig",
        entity_id="1",
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=5,
        details={"is_scoring_rules_confirmed": cfg.is_scoring_rules_confirmed}
    )
    db.commit()
    db.refresh(cfg)
    return cfg

def submit_scorecard(db: Session, team_id: str, input_data: SubmitScorecardInput, actor) -> FinaleScorecardModel:
    cfg = get_or_create_finale_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grand Finale is finalized.")

    if not is_round_finalized(db, 4):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Round 4 must be finalized before Grand Finale scores can be entered.")

    eligible = set(get_eligible_team_ids(db, 5))
    if team_id not in eligible:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Team '{team_id}' is not an official finalist from Round 4.")

    # Validate criterion boundaries
    criteria_map = {c["id"]: c.get("maxMarks", 50) for c in (cfg.criteria or [])}
    for crit_id, val in input_data.scores.items():
        if val is not None:
            max_m = criteria_map.get(crit_id, 50)
            if val < 0 or val > max_m:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Score {val} for '{crit_id}' exceeds max allowed [{0}, {max_m}].")

    eval_result = calculate_scorecard_total(input_data.scores, cfg.criteria or [])

    sc = db.query(FinaleScorecardModel).filter(FinaleScorecardModel.team_id == team_id).first()
    now = datetime.now(timezone.utc)
    if not sc:
        sc = FinaleScorecardModel(
            team_id=team_id,
            judge_name=input_data.judge_name,
            scores=input_data.scores,
            total_score=eval_result["total_score"],
            is_complete=eval_result["is_complete"],
            submitted_at=now,
            comments=input_data.comments
        )
        db.add(sc)
    else:
        sc.judge_name = input_data.judge_name
        sc.scores = input_data.scores
        sc.total_score = eval_result["total_score"]
        sc.is_complete = eval_result["is_complete"]
        sc.submitted_at = now
        sc.comments = input_data.comments

    log_audit_event(
        db=db,
        action="FINALE_SCORECARD_SUBMITTED",
        entity_type="FinaleScorecard",
        entity_id=team_id,
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=5,
        details={"team_id": team_id, "total_score": sc.total_score, "is_complete": sc.is_complete}
    )
    db.commit()
    db.refresh(sc)
    return sc

def submit_agent_verdict(db: Session, team_id: str, input_data: SubmitAgentVerdictInput, actor) -> FinaleAgentVerdictModel:
    v = db.query(FinaleAgentVerdictModel).filter(FinaleAgentVerdictModel.team_id == team_id).first()
    now = datetime.now(timezone.utc)
    if not v:
        v = FinaleAgentVerdictModel(
            team_id=team_id,
            suspected_agent=input_data.suspected_agent,
            actual_agent=input_data.actual_agent,
            is_correct=input_data.is_correct,
            bonus_points=input_data.bonus_points,
            penalty_points=input_data.penalty_points,
            is_verified=True,
            verified_by=actor.id,
            verified_at=now,
            notes=input_data.notes
        )
        db.add(v)
    else:
        v.suspected_agent = input_data.suspected_agent
        v.actual_agent = input_data.actual_agent
        v.is_correct = input_data.is_correct
        v.bonus_points = input_data.bonus_points
        v.penalty_points = input_data.penalty_points
        v.is_verified = True
        v.verified_by = actor.id
        v.verified_at = now
        v.notes = input_data.notes

    log_audit_event(
        db=db,
        action="FINALE_AGENT_VERDICT_SUBMITTED",
        entity_type="FinaleAgentVerdict",
        entity_id=team_id,
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=5,
        details={"team_id": team_id, "is_correct": v.is_correct}
    )
    db.commit()
    db.refresh(v)
    return v

def get_finale_overview(db: Session) -> Dict[str, Any]:
    cfg = get_or_create_finale_config(db)
    r4_finalized = is_round_finalized(db, 4)
    eligible_team_ids = get_eligible_team_ids(db, 5)

    teams = db.query(Team).filter(Team.id.in_(eligible_team_ids)).all() if eligible_team_ids else []
    if not r4_finalized:
        teams = db.query(Team).limit(3).all()

    # Get round 4 carried scores from round 4 qualification records
    r4_quals = {q.team_id: q for q in db.query(RoundQualification).filter(RoundQualification.round_number == 4).all()}

    scorecards = {sc.team_id: sc for sc in db.query(FinaleScorecardModel).all()}
    verdicts = {v.team_id: v for v in db.query(FinaleAgentVerdictModel).all()}

    raw_records = []
    for team in teams:
        sc = scorecards.get(team.id)
        sc_dict = {
            "team_id": team.id,
            "judge_name": sc.judge_name if sc else "Faculty Panel",
            "scores": sc.scores if sc else {},
            "total_score": sc.total_score if sc else None,
            "is_complete": sc.is_complete if sc else False,
            "submitted_at": sc.submitted_at.isoformat() if sc and sc.submitted_at else None,
            "comments": sc.comments if sc else None
        }

        v = verdicts.get(team.id)
        v_dict = {
            "is_correct": v.is_correct if v else None,
            "bonus_points": v.bonus_points if v else None,
            "penalty_points": v.penalty_points if v else None,
            "is_verified": v.is_verified if v else False
        } if v else None

        r4_score = r4_quals.get(team.id).score_snapshot if r4_quals.get(team.id) else None

        breakdown = calculate_finale_score_breakdown(
            team_id=team.id,
            round4_score=r4_score,
            scorecard=sc_dict,
            agent_verdict=v_dict,
            config={
                "is_scoring_rules_confirmed": cfg.is_scoring_rules_confirmed,
                "round4_score_carried_over": cfg.round4_score_carried_over,
                "round4_score_weight": cfg.round4_score_weight,
                "finale_activity_weight": cfg.finale_activity_weight
            }
        )

        raw_records.append({
            "team_id": team.id,
            "team_number": team.team_number,
            "team_name": team.name,
            "round4_score": r4_score,
            "scorecard": sc_dict,
            "score_breakdown": breakdown,
            "review_status": "Ready for Finalization" if breakdown["is_complete"] else "Scores Incomplete"
        })

    standings = process_finale_standings(
        records=raw_records,
        config={
            "is_scoring_rules_confirmed": cfg.is_scoring_rules_confirmed,
            "scoring_direction": cfg.scoring_direction
        },
        round4_finalized=r4_finalized
    )

    if standings.get("ties_affecting_placement"):
        tied_teams = [r for r in standings["records"] if r["team_id"] in standings["tied_teams"]]
        get_or_create_tie_review(
            db=db,
            round_number=5,
            teams_involved=tied_teams,
            ranking_metric="total_finale_score",
            cutoff_position=1,
            notes="Podium placement tie for championship honors requires explicit manual marshal determination."
        )

    tie_rev = db.query(TieReview).filter(TieReview.id == "tie-r5-cutoff1").first()
    if tie_rev and tie_rev.review_status == "RESOLVED" and standings.get("ties_affecting_placement"):
        standings["can_finalize"] = len([i for i in standings["issues"] if i["code"] != "PODIUM_TIE"]) == 0
        standings["issues"] = [i for i in standings["issues"] if i["code"] != "PODIUM_TIE"]

    return {
        "config": {
            "is_scoring_rules_confirmed": cfg.is_scoring_rules_confirmed,
            "confirmed_at": cfg.confirmed_at.isoformat() if cfg.confirmed_at else None,
            "confirmed_by": cfg.confirmed_by,
            "criteria": cfg.criteria or [],
            "round4_score_carried_over": cfg.round4_score_carried_over,
            "round4_score_weight": cfg.round4_score_weight,
            "finale_activity_weight": cfg.finale_activity_weight,
            "agent_bonus_points_for_correct": cfg.agent_bonus_points_for_correct,
            "agent_penalty_points_for_incorrect": cfg.agent_penalty_points_for_incorrect,
            "scoring_direction": cfg.scoring_direction,
            "is_finalized": cfg.is_finalized,
            "finalized_at": cfg.finalized_at.isoformat() if cfg.finalized_at else None,
            "finalized_by": cfg.finalized_by
        },
        "records": standings["records"],
        "can_finalize": standings["can_finalize"],
        "issues": standings["issues"],
        "checklist": standings["checklist"],
        "ties_affecting_placement": standings["ties_affecting_placement"],
        "champion_team_id": standings["champion_team_id"],
        "runner_up1_team_id": standings["runner_up1_team_id"],
        "runner_up2_team_id": standings["runner_up2_team_id"]
    }

def finalize_grand_finale(db: Session, actor) -> Dict[str, Any]:
    cfg = get_or_create_finale_config(db)
    if cfg.is_finalized:
        return {"can_finalize": True, "issues": [], "finalized": True, "message": "Grand Finale has already been finalized."}

    overview = get_finale_overview(db)
    if not overview["can_finalize"]:
        return {"can_finalize": False, "issues": overview["issues"], "finalized": False, "message": "Finalization blocked by server-side safeguards."}

    records = overview["records"]
    advancing_team_ids = [overview["champion_team_id"]] if overview.get("champion_team_id") else []

    record_round_finalization(
        db=db,
        round_number=5,
        records=records,
        advancing_team_ids=advancing_team_ids,
        finalized_by=actor.id
    )

    cfg.is_finalized = True
    cfg.finalized_at = datetime.now(timezone.utc)
    cfg.finalized_by = actor.id

    log_audit_event(
        db=db,
        action="ROUND_FINALIZED",
        entity_type="FinaleConfig",
        entity_id="1",
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=5,
        details={
            "champion_team_id": overview["champion_team_id"],
            "runner_up1_team_id": overview["runner_up1_team_id"],
            "runner_up2_team_id": overview["runner_up2_team_id"]
        }
    )
    db.commit()

    return {
        "can_finalize": True,
        "issues": [],
        "finalized": True,
        "champion_team_id": overview["champion_team_id"],
        "message": "Grand Finale officially sealed. Podium champions crowned!"
    }
