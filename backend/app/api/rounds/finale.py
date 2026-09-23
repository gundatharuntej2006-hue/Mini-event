from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.common import ApiResponse, FinalizationResponse
from app.schemas.rounds.finale import (
    FinaleOverviewResponse, FinaleConfigSchema, UpdateFinaleConfigInput,
    SubmitScorecardInput, SubmitAgentVerdictInput, TeamFinaleRecordResponse
)
from app.services import finale_service

router = APIRouter(prefix="/rounds/finale", tags=["Grand Finale & Championship"])

@router.get("", response_model=ApiResponse[FinaleOverviewResponse])
def get_finale(db: Session = Depends(get_db)):
    """Get Grand Finale championship overview, finalist scorecards, and podium standings."""
    data = finale_service.get_finale_overview(db)
    return ApiResponse(data=data, message="Grand Finale overview loaded")

@router.get("/config", response_model=ApiResponse[FinaleConfigSchema])
def get_config(db: Session = Depends(get_db)):
    """Get Grand Finale configuration, weights, criteria, and official confirmation status."""
    cfg = finale_service.get_or_create_finale_config(db)
    res = FinaleConfigSchema(
        is_scoring_rules_confirmed=cfg.is_scoring_rules_confirmed,
        confirmed_at=cfg.confirmed_at.isoformat() if cfg.confirmed_at else None,
        confirmed_by=cfg.confirmed_by,
        criteria=cfg.criteria or [],
        round4_score_carried_over=cfg.round4_score_carried_over,
        round4_score_weight=cfg.round4_score_weight,
        finale_activity_weight=cfg.finale_activity_weight,
        agent_bonus_points_for_correct=cfg.agent_bonus_points_for_correct,
        agent_penalty_points_for_incorrect=cfg.agent_penalty_points_for_incorrect,
        scoring_direction=cfg.scoring_direction,
        is_finalized=cfg.is_finalized,
        finalized_at=cfg.finalized_at.isoformat() if cfg.finalized_at else None,
        finalized_by=cfg.finalized_by
    )
    return ApiResponse(data=res)

@router.put("/config", response_model=ApiResponse[FinaleConfigSchema])
def update_config(
    payload: UpdateFinaleConfigInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Update criteria or officially confirm Grand Finale scoring rules (Organizers only)."""
    cfg = finale_service.update_finale_config(db, payload.model_dump(exclude_unset=True), actor)
    res = FinaleConfigSchema(
        is_scoring_rules_confirmed=cfg.is_scoring_rules_confirmed,
        confirmed_at=cfg.confirmed_at.isoformat() if cfg.confirmed_at else None,
        confirmed_by=cfg.confirmed_by,
        criteria=cfg.criteria or [],
        round4_score_carried_over=cfg.round4_score_carried_over,
        round4_score_weight=cfg.round4_score_weight,
        finale_activity_weight=cfg.finale_activity_weight,
        agent_bonus_points_for_correct=cfg.agent_bonus_points_for_correct,
        agent_penalty_points_for_incorrect=cfg.agent_penalty_points_for_incorrect,
        scoring_direction=cfg.scoring_direction,
        is_finalized=cfg.is_finalized,
        finalized_at=cfg.finalized_at.isoformat() if cfg.finalized_at else None,
        finalized_by=cfg.finalized_by
    )
    return ApiResponse(data=res, message="Grand Finale configuration updated")

@router.get("/teams", response_model=ApiResponse[List[TeamFinaleRecordResponse]])
def get_teams(db: Session = Depends(get_db)):
    """Get all 3 finalist squads for the Grand Finale."""
    overview = finale_service.get_finale_overview(db)
    return ApiResponse(data=overview["records"])

@router.get("/leaderboard", response_model=ApiResponse[List[TeamFinaleRecordResponse]])
def get_leaderboard(db: Session = Depends(get_db)):
    """Get official server-side podium standings for the Grand Finale."""
    overview = finale_service.get_finale_overview(db)
    return ApiResponse(data=overview["records"])

@router.post("/scorecards/{team_id}", response_model=ApiResponse[Dict[str, Any]])
def submit_scorecard_api(
    team_id: str,
    payload: SubmitScorecardInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["judge", "lead_judge", "organizer", "admin"]))
):
    """Submit Grand Tribunal rubric scorecard for a finalist squad."""
    sc = finale_service.submit_scorecard(db, team_id, payload, actor)
    return ApiResponse(data={"team_id": team_id, "total_score": sc.total_score, "is_complete": sc.is_complete}, message="Scorecard saved")

@router.post("/agent-verdicts/{team_id}", response_model=ApiResponse[Dict[str, Any]])
def submit_agent_verdict_api(
    team_id: str,
    payload: SubmitAgentVerdictInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Submit unmasked secret agent verdict and verification."""
    v = finale_service.submit_agent_verdict(db, team_id, payload, actor)
    return ApiResponse(data={"team_id": team_id, "is_correct": v.is_correct}, message="Verdict verified")

@router.get("/qualification", response_model=ApiResponse[Dict[str, Any]])
def get_qualification(db: Session = Depends(get_db)):
    """Check Grand Finale readiness, checklist items, and tie safeguards."""
    overview = finale_service.get_finale_overview(db)
    return ApiResponse(data={
        "can_finalize": overview["can_finalize"],
        "issues": overview["issues"],
        "checklist": overview["checklist"],
        "ties_affecting_placement": overview["ties_affecting_placement"],
        "champion_team_id": overview["champion_team_id"]
    })

@router.post("/finalize", response_model=ApiResponse[FinalizationResponse])
def finalize_finale(
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Officially seal Grand Finale and crown Champion, 1st Runner Up, and 2nd Runner Up."""
    res = finale_service.finalize_grand_finale(db, actor)
    return ApiResponse(data=res, message=res.get("message"))
