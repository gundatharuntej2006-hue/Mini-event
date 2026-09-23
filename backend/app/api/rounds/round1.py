from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.common import ApiResponse, FinalizationResponse
from app.schemas.rounds.round1 import (
    Round1OverviewResponse, Round1ConfigSchema, UpdateRound1ConfigInput,
    MiniRoundTimingInput, UpdateHintsInput, TeamRound1RecordResponse,
    MiniRoundTimingResponse
)
from app.services import round1_service

router = APIRouter(prefix="/rounds/1", tags=["Round 1 — The Great Expedition"])

@router.get("", response_model=ApiResponse[Round1OverviewResponse])
def get_round1(db: Session = Depends(get_db)):
    """Get complete Round 1 overview, live standings, and finalization status."""
    data = round1_service.get_round1_overview(db)
    return ApiResponse(data=data, message="Round 1 expedition overview loaded")

@router.get("/config", response_model=ApiResponse[Round1ConfigSchema])
def get_config(db: Session = Depends(get_db)):
    """Get Round 1 configuration parameters."""
    cfg = round1_service.get_or_create_round1_config(db)
    res = Round1ConfigSchema(
        penalty_per_hint_seconds=cfg.penalty_per_hint_seconds,
        checkpoint_names=cfg.checkpoint_names or [],
        is_finalized=cfg.is_finalized,
        finalized_at=cfg.finalized_at.isoformat() if cfg.finalized_at else None,
        finalized_by=cfg.finalized_by
    )
    return ApiResponse(data=res)

@router.put("/config", response_model=ApiResponse[Round1ConfigSchema])
def update_config(
    payload: UpdateRound1ConfigInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Update hint penalties or checkpoint definitions (Organizers only)."""
    cfg = round1_service.update_round1_config(
        db=db,
        penalty_seconds=payload.penalty_per_hint_seconds,
        checkpoint_names=payload.checkpoint_names,
        actor=actor
    )
    res = Round1ConfigSchema(
        penalty_per_hint_seconds=cfg.penalty_per_hint_seconds,
        checkpoint_names=cfg.checkpoint_names or [],
        is_finalized=cfg.is_finalized,
        finalized_at=cfg.finalized_at.isoformat() if cfg.finalized_at else None,
        finalized_by=cfg.finalized_by
    )
    return ApiResponse(data=res, message="Round 1 configuration updated")

@router.get("/teams", response_model=ApiResponse[List[TeamRound1RecordResponse]])
def get_teams(db: Session = Depends(get_db)):
    """Get all 32 squad records for Round 1."""
    overview = round1_service.get_round1_overview(db)
    return ApiResponse(data=overview["records"])

@router.get("/leaderboard", response_model=ApiResponse[List[TeamRound1RecordResponse]])
def get_leaderboard(db: Session = Depends(get_db)):
    """Get official server-side ranked leaderboard for Round 1."""
    overview = round1_service.get_round1_overview(db)
    return ApiResponse(data=overview["records"])

@router.post("/teams/{team_id}/timings", response_model=ApiResponse[MiniRoundTimingResponse])
@router.put("/teams/{team_id}/timings", response_model=ApiResponse[MiniRoundTimingResponse])
def record_timing(
    team_id: str,
    payload: MiniRoundTimingInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "marshal", "scorekeeper", "admin"]))
):
    """Record or update checkpoint timing for a squad mini-round."""
    timing = round1_service.record_mini_round_timing(db, team_id, payload, actor)
    res = MiniRoundTimingResponse(
        mini_round_number=timing.mini_round_number,
        status=timing.status,
        start_time=timing.start_time.isoformat() if timing.start_time else None,
        completion_time=timing.completion_time.isoformat() if timing.completion_time else None,
        hints_used=timing.hints_used,
        hint_penalty_seconds=timing.hint_penalty_seconds,
        duration_seconds=timing.duration_seconds,
        adjusted_seconds=timing.adjusted_seconds,
        checkpoints=timing.checkpoints or []
    )
    return ApiResponse(data=res, message="Mini-round timing successfully recorded")

@router.post("/teams/{team_id}/hints", response_model=ApiResponse[MiniRoundTimingResponse])
def record_hints(
    team_id: str,
    payload: UpdateHintsInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "marshal", "scorekeeper", "admin"]))
):
    """Update hint count taken by a squad."""
    timing = round1_service.update_hints(db, team_id, payload.mini_round_number, payload.hints_used, actor)
    res = MiniRoundTimingResponse(
        mini_round_number=timing.mini_round_number,
        status=timing.status,
        start_time=timing.start_time.isoformat() if timing.start_time else None,
        completion_time=timing.completion_time.isoformat() if timing.completion_time else None,
        hints_used=timing.hints_used,
        hint_penalty_seconds=timing.hint_penalty_seconds,
        duration_seconds=timing.duration_seconds,
        adjusted_seconds=timing.adjusted_seconds,
        checkpoints=timing.checkpoints or []
    )
    return ApiResponse(data=res, message="Hints updated")

@router.get("/teams/{team_id}/result", response_model=ApiResponse[TeamRound1RecordResponse])
def get_team_result(team_id: str, db: Session = Depends(get_db)):
    """Get single squad result and qualification status in Round 1."""
    overview = round1_service.get_round1_overview(db)
    rec = next((r for r in overview["records"] if r["team_id"] == team_id), None)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team '{team_id}' not found in Round 1.")
    return ApiResponse(data=rec)

@router.get("/qualification", response_model=ApiResponse[Dict[str, Any]])
def get_qualification(db: Session = Depends(get_db)):
    """Check Round 1 qualification readiness, top 24 cutoff, and tie flags."""
    overview = round1_service.get_round1_overview(db)
    return ApiResponse(data={
        "can_finalize": overview["can_finalize"],
        "issues": overview["issues"],
        "completed_count": overview["completed_count"],
        "incomplete_count": overview["incomplete_count"],
        "top24_cutoff_time": overview["top24_cutoff_time"]
    })

@router.post("/finalize", response_model=ApiResponse[FinalizationResponse])
def finalize_round1(
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Officially seal Round 1 results and advance 24 squads to Round 2."""
    res = round1_service.finalize_round1(db, actor, payload)
    return ApiResponse(data=res, message=res.get("message"))
