from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.common import ApiResponse, TieReviewResponse, ResolveTieRequest, AuditLogResponse
from app.services import progression_service, tie_review_service
from app.models.progression import AuditLog

router = APIRouter(tags=["Tournament Progression, Tie Reviews & Audit Trail"])

@router.get("/progression/status", response_model=ApiResponse[Dict[str, Any]])
def get_progression_status(db: Session = Depends(get_db)):
    """Get global tournament progression state across all 5 rounds."""
    summary = progression_service.get_tournament_progression_summary(db)
    return ApiResponse(data=summary, message="Progression status loaded")

@router.get("/ties/review", response_model=ApiResponse[List[TieReviewResponse]])
def get_tie_reviews(
    round: Optional[int] = Query(None, description="Filter by round number"),
    db: Session = Depends(get_db)
):
    """List all registered cutoff and placement tie reviews."""
    records = tie_review_service.list_tie_reviews(db, round)
    res = [
        TieReviewResponse(
            id=r.id,
            round_number=r.round_number,
            teams_involved=r.teams_involved or [],
            ranking_metric=r.ranking_metric,
            cutoff_position=r.cutoff_position,
            tie_breaker_status=r.tie_breaker_status,
            review_status=r.review_status,
            organizer_decision=r.organizer_decision,
            advancing_team_ids=r.advancing_team_ids,
            eliminated_team_ids=r.eliminated_team_ids,
            decision_timestamp=r.decision_timestamp.isoformat() if r.decision_timestamp else None,
            decided_by=r.decided_by,
            notes=r.notes
        )
        for r in records
    ]
    return ApiResponse(data=res)

@router.post("/ties/review/{tie_id}/resolve", response_model=ApiResponse[TieReviewResponse])
def resolve_tie(
    tie_id: str,
    payload: ResolveTieRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Record official organizer determination to resolve a cutoff tie."""
    try:
        r = tie_review_service.resolve_tie_review(
            db=db,
            tie_id=tie_id,
            decision=payload.decision,
            advancing_team_ids=payload.advancing_team_ids,
            eliminated_team_ids=payload.eliminated_team_ids,
            decided_by=actor.id,
            notes=payload.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    res = TieReviewResponse(
        id=r.id,
        round_number=r.round_number,
        teams_involved=r.teams_involved or [],
        ranking_metric=r.ranking_metric,
        cutoff_position=r.cutoff_position,
        tie_breaker_status=r.tie_breaker_status,
        review_status=r.review_status,
        organizer_decision=r.organizer_decision,
        advancing_team_ids=r.advancing_team_ids,
        eliminated_team_ids=r.eliminated_team_ids,
        decision_timestamp=r.decision_timestamp.isoformat() if r.decision_timestamp else None,
        decided_by=r.decided_by,
        notes=r.notes
    )
    return ApiResponse(data=res, message="Tie review successfully resolved")

@router.get("/audit/logs", response_model=ApiResponse[List[AuditLogResponse]])
def get_audit_logs(
    round_number: Optional[int] = Query(None, description="Filter by round number"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get immutable audit trail of tournament scoring, reversals, and finalizations."""
    query = db.query(AuditLog)
    if round_number is not None:
        query = query.filter(AuditLog.round_number == round_number)
    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    res = [
        AuditLogResponse(
            id=log.id,
            action=log.action,
            round_number=log.round_number,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            actor_id=log.actor_id,
            actor_role=log.actor_role,
            details=log.details,
            timestamp=log.timestamp.isoformat()
        )
        for log in logs
    ]
    return ApiResponse(data=res)
