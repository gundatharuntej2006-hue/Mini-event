from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from app.models.progression import TieReview
from app.services.audit_service import log_audit_event

def get_or_create_tie_review(
    db: Session,
    round_number: int,
    teams_involved: List[Dict[str, Any]],
    ranking_metric: str,
    cutoff_position: int,
    notes: Optional[str] = None
) -> TieReview:
    tie_id = f"tie-r{round_number}-cutoff{cutoff_position}"
    existing = db.query(TieReview).filter(TieReview.id == tie_id).first()
    if existing:
        existing.teams_involved = teams_involved
        existing.notes = notes or existing.notes
        db.commit()
        db.refresh(existing)
        return existing

    new_tie = TieReview(
        id=tie_id,
        round_number=round_number,
        teams_involved=teams_involved,
        ranking_metric=ranking_metric,
        cutoff_position=cutoff_position,
        tie_breaker_status="EXHAUSTED",
        review_status="PENDING_REVIEW",
        notes=notes
    )
    db.add(new_tie)
    db.commit()
    db.refresh(new_tie)
    return new_tie

def resolve_tie_review(
    db: Session,
    tie_id: str,
    decision: str,
    advancing_team_ids: List[str],
    eliminated_team_ids: List[str],
    decided_by: str,
    notes: Optional[str] = None
) -> TieReview:
    tie = db.query(TieReview).filter(TieReview.id == tie_id).first()
    if not tie:
        raise ValueError(f"Tie review {tie_id} not found.")

    tie.review_status = "RESOLVED"
    tie.organizer_decision = decision
    tie.advancing_team_ids = advancing_team_ids
    tie.eliminated_team_ids = eliminated_team_ids
    tie.decision_timestamp = datetime.now(timezone.utc)
    tie.decided_by = decided_by
    if notes:
        tie.notes = f"{tie.notes or ''}\nResolution note: {notes}".strip()

    log_audit_event(
        db=db,
        action="TIE_REVIEW_RESOLVED",
        entity_type="TieReview",
        entity_id=tie.id,
        actor_id=decided_by,
        actor_role="organizer",
        round_number=tie.round_number,
        details={
            "decision": decision,
            "advancing_team_ids": advancing_team_ids,
            "eliminated_team_ids": eliminated_team_ids
        }
    )
    db.commit()
    db.refresh(tie)
    return tie

def list_tie_reviews(db: Session, round_number: Optional[int] = None) -> List[TieReview]:
    query = db.query(TieReview)
    if round_number is not None:
        query = query.filter(TieReview.round_number == round_number)
    return query.order_by(TieReview.created_at.desc()).all()
