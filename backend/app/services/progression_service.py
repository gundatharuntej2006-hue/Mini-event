from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.models.progression import RoundQualification
from app.models.round1 import Round1ConfigModel
from app.models.round2 import CaboConfigModel
from app.models.round3 import BlackMarketConfigModel
from app.models.round4 import Round4ConfigModel
from app.models.finale import FinaleConfigModel
from app.models.round_models import RoundState
from app.models.core import Team

def is_round_finalized(db: Session, round_number: int) -> bool:
    rs = db.query(RoundState).filter(RoundState.id == round_number).first()
    if rs and rs.is_finalized:
        return True
    if round_number == 1:
        cfg = db.query(Round1ConfigModel).filter(Round1ConfigModel.id == 1).first()
        return bool(cfg and cfg.is_finalized)
    elif round_number == 2:
        cfg = db.query(CaboConfigModel).filter(CaboConfigModel.id == 1).first()
        return bool(cfg and cfg.is_finalized)
    elif round_number == 3:
        cfg = db.query(BlackMarketConfigModel).filter(BlackMarketConfigModel.id == 1).first()
        return bool(cfg and cfg.is_finalized)
    elif round_number == 4:
        cfg = db.query(Round4ConfigModel).filter(Round4ConfigModel.id == 1).first()
        return bool(cfg and cfg.is_finalized)
    elif round_number == 5:
        cfg = db.query(FinaleConfigModel).filter(FinaleConfigModel.id == 1).first()
        return bool(cfg and cfg.is_finalized)
    return False

def get_eligible_team_ids(db: Session, target_round: int) -> List[str]:
    """
    CRITICAL: Eligibility MUST come from finalized qualification records,
    NEVER calculated simply from current provisional leaderboard.
    """
    if target_round == 1:
        # All registered teams in field
        return [t.id for t in db.query(Team).order_by(Team.team_number.asc()).all()]

    previous_round = target_round - 1
    if not is_round_finalized(db, previous_round):
        return []

    advancing = (
        db.query(RoundQualification)
        .filter(
            RoundQualification.round_number == previous_round,
            RoundQualification.is_advancing == True
        )
        .order_by(RoundQualification.rank.asc())
        .all()
    )
    return [q.team_id for q in advancing]

def record_round_finalization(
    db: Session,
    round_number: int,
    records: List[Dict[str, Any]],
    advancing_team_ids: List[str],
    finalized_by: str
):
    """
    Saves immutable qualification records for all participating squads in the round.
    """
    # Remove any existing provisional qualifications for this round if re-running in controlled workflow
    db.query(RoundQualification).filter(RoundQualification.round_number == round_number).delete()

    adv_set = set(advancing_team_ids)
    now = datetime.now(timezone.utc)

    for r in records:
        team_id = r["team_id"]
        rank = r.get("rank")
        is_adv = team_id in adv_set
        score_snap = (
            r.get("adjusted_total_seconds") or
            r.get("total_points") or
            r.get("final_score") or
            r.get("final_score_breakdown", {}).get("final_score") or
            r.get("score_breakdown", {}).get("total_finale_score") or
            r.get("panel_score")
        )

        qual = RoundQualification(
            id=f"qual-r{round_number}-{team_id}",
            round_number=round_number,
            team_id=team_id,
            rank=rank,
            status="Finalized Qualified" if is_adv else "Finalized Eliminated",
            score_snapshot=float(score_snap) if score_snap is not None else None,
            is_advancing=is_adv,
            finalized_at=now,
            finalized_by=finalized_by
        )
        db.add(qual)

    rs = db.query(RoundState).filter(RoundState.id == round_number).first()
    if rs:
        rs.is_finalized = True
        rs.finalized_at = now
        rs.finalized_by = finalized_by
        rs.status = "Completed"

    db.commit()

def get_tournament_progression_summary(db: Session) -> Dict[str, Any]:
    return {
        "round1_finalized": is_round_finalized(db, 1),
        "round2_finalized": is_round_finalized(db, 2),
        "round3_finalized": is_round_finalized(db, 3),
        "round4_finalized": is_round_finalized(db, 4),
        "finale_finalized": is_round_finalized(db, 5),
        "round2_eligible_count": len(get_eligible_team_ids(db, 2)),
        "round3_eligible_count": len(get_eligible_team_ids(db, 3)),
        "round4_eligible_count": len(get_eligible_team_ids(db, 4)),
        "finale_eligible_count": len(get_eligible_team_ids(db, 5)),
    }
