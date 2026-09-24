"""
Championship Service for Step 15: Final Championship Scoring, Top 4, Top 3 & Best Secret Agent.
Source of Truth: Authoritative Event Documentation reconciled in Step 6B & Step 15.

Composite Final Score Formula:
    Final Score = Legal Battle Panel Score + Agent Guessing Points + 10% Remaining Black Market Wallet Points
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.constants import (
    DEFAULT_CARRYOVER_WEIGHT_PERCENT,
    R4_ADVANCING_COUNT,
    PODIUM_SIZE,
)
from app.models.team import Team
from app.models.participant import Participant
from app.models.wallet import TeamWallet
from app.models.agent import SecretAgentDossier, SecretAgentTask, AgentTaskStatus
from app.models.progression import RoundQualification, TieReview, AuditLog
from app.models.finale import (
    FinaleConfigModel,
    FinaleTeamGuessSubmissionModel,
    FinaleAgentGuessModel,
    FinaleChampionshipStandingModel,
)
from app.models.round4 import Round4ConfigModel
from app.models.round_models import RoundState
from app.scoring.championship_scoring import (
    calculate_final_championship_score,
    calculate_championship_standings,
    calculate_best_secret_agent as calc_best_agent,
)
from app.services.progression_service import (
    get_eligible_team_ids,
    is_round_finalized,
    record_round_finalization,
)
from app.services.tie_review_service import get_or_create_tie_review
from app.services.audit_service import log_audit_event


def get_or_create_finale_config(db: Session) -> FinaleConfigModel:
    """Fetches or creates the persistent Grand Finale configuration."""
    cfg = db.query(FinaleConfigModel).filter(FinaleConfigModel.id == 1).first()
    if not cfg:
        cfg = FinaleConfigModel(
            id=1,
            is_scoring_rules_confirmed=True,
            advancing_teams_count=R4_ADVANCING_COUNT,
            min_guesses=1,
            max_guesses=5,
            correct_guess_points=30.0,
            wrong_guess_points=-20.0,
            carryover_wallet_percent=DEFAULT_CARRYOVER_WEIGHT_PERCENT,
            is_guessing_open=True,
            is_finalized=False,
            is_revealed=False,
            is_top_four_revealed=False,
            is_podium_revealed=False,
            is_agents_revealed=False,
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def get_championship_standings_data(
    db: Session,
    actor=None,
    carryover_weight: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes complete Championship standings for all 8 finalist squads.
    Preserves and isolates:
    - Legal Battle panel score (max 100.0)
    - Agent Guessing net points (+30.0 / -20.0 / 0.0)
    - 10% Black Market wallet balance carryover
    """
    cfg = get_or_create_finale_config(db)
    weight = carryover_weight if carryover_weight is not None else (cfg.carryover_wallet_percent / 100.0)

    # Progression Check: Round 4 Finalized
    r4_finalized = is_round_finalized(db, 4)

    # Actor authorization check
    is_organizer = True
    if actor:
        actor_role = getattr(actor, "role", None)
        actor_role_str = actor_role.value if hasattr(actor_role, "value") else str(actor_role).upper()
        is_organizer = actor_role_str in ("ORGANIZER", "ADMIN", "LEAD_JUDGE", "MARSHAL", "SCOREKEEPER")

    # Load 8 finalist teams
    eligible_team_ids = get_eligible_team_ids(db, 5)
    if eligible_team_ids:
        teams = db.query(Team).filter(Team.id.in_(eligible_team_ids)).order_by(Team.team_number.asc()).all()
    else:
        teams = db.query(Team).order_by(Team.team_number.asc()).limit(cfg.advancing_teams_count or 8).all()

    # Load Round 4 scores from qualifications
    r4_quals = {
        q.team_id: q for q in db.query(RoundQualification).filter(RoundQualification.round_number == 4).all()
    }

    # Load Wallets for carryover calculation
    wallets = {w.team_id: w for w in db.query(TeamWallet).all()}

    # Load Guess Submissions
    submissions = {
        s.guessing_team_id: s for s in db.query(FinaleTeamGuessSubmissionModel).all()
    }

    # Guessing finalized check: all finalist squads submitted guesses or round finalized
    guessing_finalized = len(submissions) == len(teams) and len(teams) > 0

    raw_records: List[Dict[str, Any]] = []
    for team in teams:
        r4_qual = r4_quals.get(team.id)
        r4_score = r4_qual.score_snapshot if r4_qual else None

        w = wallets.get(team.id)
        w_bal = getattr(w, "current_balance", getattr(w, "balance", 1000.0)) if w else 1000.0

        sub = submissions.get(team.id)
        ag_pts = sub.total_guessing_points if sub else 0.0

        raw_records.append({
            "team_id": team.id,
            "team_number": team.team_number,
            "team_name": team.name,
            "legal_battle_score": r4_score,
            "agent_guessing_points": ag_pts,
            "remaining_black_market_points": w_bal,
        })

    standings = calculate_championship_standings(
        finalist_records=raw_records,
        carryover_weight=weight,
        expected_finalists=cfg.advancing_teams_count or 8,
        round4_finalized=r4_finalized,
        guessing_finalized=guessing_finalized,
    )

    # Check if a TieReview record exists and has been resolved
    tie_rev = db.query(TieReview).filter(TieReview.id == "tie-championship-podium").first()
    if tie_rev and tie_rev.review_status == "RESOLVED":
        standings["requires_organizer_review"] = False
        standings["podium_tie_requires_review"] = False
        standings["top_four_tie_requires_review"] = False
        standings["issues"] = [i for i in standings["issues"] if i["code"] not in ("PODIUM_TIE", "TOP_FOUR_CUTOFF_TIE")]
        standings["can_finalize"] = (len(standings["issues"]) == 0)

    # Redact sensitive scores for non-organizers before reveal
    if not is_organizer and not cfg.is_revealed:
        for rec in standings["records"]:
            bd = rec.get("score_breakdown", {})
            bd["agent_guessing_points"] = None
            bd["agent_guessing_component"] = None
            bd["final_score"] = None
            rec["agent_guessing_points"] = None
            rec["final_score"] = None

    return standings


def get_team_final_score(
    db: Session,
    team_id: str,
    actor=None,
) -> Dict[str, Any]:
    """
    Retrieves a squad's individual composite championship score breakdown.
    Enforces confidentiality: team users cannot view unmasked guessing points or composite final score before reveal.
    """
    cfg = get_or_create_finale_config(db)
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team '{team_id}' not found.")

    actor_role = getattr(actor, "role", None)
    actor_role_str = actor_role.value if hasattr(actor_role, "value") else str(actor_role).upper()
    is_organizer = actor_role_str in ("ORGANIZER", "ADMIN", "LEAD_JUDGE", "MARSHAL")

    if not is_organizer and getattr(actor, "team_id", None) and getattr(actor, "team_id", None) != team_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own team's final score.")

    # Load components
    r4_qual = db.query(RoundQualification).filter(
        RoundQualification.round_number == 4,
        RoundQualification.team_id == team_id,
    ).first()
    r4_score = r4_qual.score_snapshot if r4_qual else None

    sub = db.query(FinaleTeamGuessSubmissionModel).filter(
        FinaleTeamGuessSubmissionModel.guessing_team_id == team_id
    ).first()
    ag_points = sub.total_guessing_points if sub else 0.0

    w = db.query(TeamWallet).filter(TeamWallet.team_id == team_id).first()
    w_bal = getattr(w, "current_balance", getattr(w, "balance", 1000.0)) if w else 1000.0

    breakdown = calculate_final_championship_score(
        legal_battle_score=r4_score,
        agent_guessing_points=ag_points,
        remaining_black_market_points=w_bal,
        carryover_weight=cfg.carryover_wallet_percent / 100.0,
    )
    breakdown["team_id"] = team_id

    # Mask for non-organizers before reveal
    if not is_organizer and not cfg.is_revealed:
        breakdown["agent_guessing_points"] = None
        breakdown["agent_guessing_component"] = None
        breakdown["final_score"] = None

    return breakdown


def get_top_four_data(
    db: Session,
    actor=None,
) -> Dict[str, Any]:
    """
    Returns Top 4 championship standings.
    Before reveal: Non-organizers receive masked/empty list.
    """
    cfg = get_or_create_finale_config(db)
    actor_role = getattr(actor, "role", None)
    actor_role_str = actor_role.value if hasattr(actor_role, "value") else str(actor_role).upper()
    is_organizer = actor_role_str in ("ORGANIZER", "ADMIN", "LEAD_JUDGE", "MARSHAL")

    can_view = is_organizer or cfg.is_top_four_revealed or cfg.is_revealed
    standings = get_championship_standings_data(db, actor=actor)

    top_four = standings["top_four"] if can_view else []

    return {
        "is_revealed": can_view,
        "top_four": top_four,
        "tie_requires_review": standings["top_four_tie_requires_review"],
        "tied_teams": standings["tied_top_four_teams"],
        "message": (
            "Top 4 squads officially revealed" if can_view else "Top 4 squads pending official organizer reveal"
        ),
    }


def get_podium_data(
    db: Session,
    actor=None,
) -> Dict[str, Any]:
    """
    Returns Top 3 podium standings (Grand Champion, 1st Runner Up, 2nd Runner Up).
    Before reveal: Non-organizers receive masked/empty list.
    """
    cfg = get_or_create_finale_config(db)
    actor_role = getattr(actor, "role", None)
    actor_role_str = actor_role.value if hasattr(actor_role, "value") else str(actor_role).upper()
    is_organizer = actor_role_str in ("ORGANIZER", "ADMIN", "LEAD_JUDGE", "MARSHAL")

    can_view = is_organizer or cfg.is_podium_revealed or cfg.is_revealed
    standings = get_championship_standings_data(db, actor=actor)

    podium_list = standings["top_three"] if can_view else []
    champ = podium_list[0] if len(podium_list) > 0 and not standings["podium_tie_requires_review"] else None
    r1 = podium_list[1] if len(podium_list) > 1 and not standings["podium_tie_requires_review"] else None
    r2 = podium_list[2] if len(podium_list) > 2 and not standings["podium_tie_requires_review"] else None

    return {
        "is_revealed": can_view,
        "podium": podium_list,
        "champion": champ,
        "runner_up1": r1,
        "runner_up2": r2,
        "tie_requires_review": standings["podium_tie_requires_review"],
        "tied_teams": standings["tied_podium_teams"],
        "message": (
            "Championship podium officially revealed" if can_view else "Championship podium pending official organizer reveal"
        ),
    }


def get_best_secret_agent_data(
    db: Session,
    actor=None,
) -> Dict[str, Any]:
    """
    Resolves Best Secret Agent:
    1. Most verified tasks completed (descending).
    2. Fewest correct unmasking guesses received (ascending).
    3. Ties flagged for organizer review.
    Masks confidential participant identities for non-organizers before reveal.
    """
    cfg = get_or_create_finale_config(db)
    actor_role = getattr(actor, "role", None)
    actor_role_str = actor_role.value if hasattr(actor_role, "value") else str(actor_role).upper()
    is_organizer = actor_role_str in ("ORGANIZER", "ADMIN", "LEAD_JUDGE", "MARSHAL")
    can_view_unmasked = is_organizer or cfg.is_agents_revealed or cfg.is_revealed

    dossiers = db.query(SecretAgentDossier).all()
    all_guesses = db.query(FinaleAgentGuessModel).all()

    dossier_data_list: List[Dict[str, Any]] = []
    for d in dossiers:
        t = db.query(Team).filter(Team.id == d.team_id).first()
        p = db.query(Participant).filter(Participant.id == d.participant_id).first()

        verified_tasks_count = db.query(SecretAgentTask).filter(
            SecretAgentTask.dossier_id == d.id,
            SecretAgentTask.status == AgentTaskStatus.VERIFIED,
        ).count()

        dossier_data_list.append({
            "id": d.id,
            "team_id": d.team_id,
            "team_number": t.team_number if t else 999,
            "team_name": t.name if t else "Unknown Squad",
            "participant_id": d.participant_id,
            "participant_name": p.name if p else "Secret Agent",
            "codename": d.codename,
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            "verified_tasks_count": verified_tasks_count,
        })

    all_evaluated = [
        {"target_team_id": g.target_team_id, "is_correct": g.is_correct}
        for g in all_guesses
    ]

    result = calc_best_agent(dossier_data_list, all_evaluated)

    if not can_view_unmasked:
        for r in result.get("rankings", []):
            r["participant_name"] = "CONFIDENTIAL"
            r["codename"] = "CONFIDENTIAL"
            r["participant_id"] = "CONFIDENTIAL"
        if result.get("best_agent"):
            result["best_agent"]["participant_name"] = "CONFIDENTIAL"
            result["best_agent"]["codename"] = "CONFIDENTIAL"
            result["best_agent"]["participant_id"] = "CONFIDENTIAL"

    return result


def reveal_championship_stage(
    db: Session,
    stage: str,
    actor,
) -> Dict[str, Any]:
    """
    Organizer-controlled progressive reveal of championship outcomes:
    - 'top_four': Reveals the 4 highest final-score squads.
    - 'podium': Reveals the Top 3 prize positions (Grand Champion, 1st & 2nd Runner Up).
    - 'secret_agents': Reveals all secret agent identities and unmasked dossiers.
    - 'all': Unlocks all results event-wide.
    """
    cfg = get_or_create_finale_config(db)
    actor_id = getattr(actor, "id", str(actor))
    now = datetime.now(timezone.utc)

    stage_lower = stage.lower()
    if stage_lower == "top_four":
        cfg.is_top_four_revealed = True
        cfg.top_four_revealed_at = now
        cfg.top_four_revealed_by = actor_id
        message = "Top 4 squads officially revealed to participants."
    elif stage_lower == "podium":
        cfg.is_podium_revealed = True
        cfg.podium_revealed_at = now
        cfg.podium_revealed_by = actor_id
        message = "Championship podium officially revealed to participants."
    elif stage_lower in ("secret_agents", "agents"):
        cfg.is_agents_revealed = True
        cfg.agents_revealed_at = now
        cfg.agents_revealed_by = actor_id
        message = "Secret Agent identities officially revealed to participants."
    elif stage_lower in ("all", "full"):
        cfg.is_revealed = True
        cfg.revealed_at = now
        cfg.revealed_by = actor_id
        cfg.is_top_four_revealed = True
        cfg.is_podium_revealed = True
        cfg.is_agents_revealed = True
        message = "Grand Finale championship results fully revealed event-wide."
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reveal stage '{stage}'. Choose from 'top_four', 'podium', 'secret_agents', or 'all'.",
        )

    log_audit_event(
        db=db,
        action=f"FINALE_REVEAL_{stage_lower.upper()}",
        entity_type="FinaleConfig",
        entity_id="1",
        actor_id=actor_id,
        actor_role="ORGANIZER",
        round_number=5,
        details={"stage": stage_lower, "revealed_at": now.isoformat()},
    )
    db.commit()
    db.refresh(cfg)

    return {
        "success": True,
        "stage": stage_lower,
        "is_top_four_revealed": cfg.is_top_four_revealed,
        "is_podium_revealed": cfg.is_podium_revealed,
        "is_agents_revealed": cfg.is_agents_revealed,
        "is_revealed": cfg.is_revealed,
        "message": message,
    }


def resolve_championship_tie(
    db: Session,
    tie_type: str,
    decisions: Dict[str, Any],
    actor,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Handles organizer determination of a tied placement cutoff or podium position.
    Preserves audit history and determinism.
    """
    actor_id = getattr(actor, "id", str(actor))
    actor_role = getattr(actor, "role", "ORGANIZER")
    actor_role_str = actor_role.value if hasattr(actor_role, "value") else str(actor_role).upper()

    tie_rev = get_or_create_tie_review(
        db=db,
        round_number=5,
        teams_involved=[],
        ranking_metric="total_final_score",
        cutoff_position=1 if tie_type == "podium" else 4,
        notes=notes or f"Manual organizer resolution of {tie_type} tie.",
    )
    tie_rev.review_status = "RESOLVED"
    tie_rev.notes = f"{tie_rev.notes or ''}\nResolved by {actor_id}: {decisions}".strip()

    log_audit_event(
        db=db,
        action="CHAMPIONSHIP_TIE_RESOLVED",
        entity_type="TieReview",
        entity_id=tie_rev.id,
        actor_id=actor_id,
        actor_role=actor_role_str,
        round_number=5,
        details={"tie_type": tie_type, "decisions": decisions, "notes": notes},
    )
    db.commit()

    return {
        "success": True,
        "tie_type": tie_type,
        "status": "RESOLVED",
        "message": f"Championship {tie_type} tie successfully resolved by organizer.",
    }


def finalize_championship(
    db: Session,
    actor,
    override_discrepancy: bool = False,
) -> Dict[str, Any]:
    """
    Officially seals the Tournament Grand Championship.

    Verifies:
    1. Exactly 8 finalists.
    2. Round 4 finalized.
    3. All 8 Legal Battle scores available.
    4. Finale Guessing finalized.
    5. All 8 Agent Guessing scores available.
    6. Remaining wallet balances available.
    7. No unresolved podium / cutoff ties (unless overridden).

    Idempotent: Subsequent calls return successful sealed state without duplicate DB writes.
    Does NOT mutate underlying wallet balances or Round 4 scores.
    """
    cfg = get_or_create_finale_config(db)
    if cfg.is_finalized:
        return {
            "can_finalize": True,
            "issues": [],
            "finalized": True,
            "message": "Tournament Championship has already been officially finalized.",
        }

    standings = get_championship_standings_data(db, actor=actor)
    can_fin = standings["can_finalize"] or override_discrepancy
    if not can_fin:
        return {
            "can_finalize": False,
            "issues": standings["issues"],
            "finalized": False,
            "message": "Championship finalization blocked by server-side safeguards.",
        }

    records = standings["records"]
    now = datetime.now(timezone.utc)
    actor_id = getattr(actor, "id", str(actor))
    actor_role = getattr(actor, "role", "ORGANIZER")
    actor_role_str = actor_role.value if hasattr(actor_role, "value") else str(actor_role).upper()

    # Persist final standings into FinaleChampionshipStandingModel
    for rec in records:
        bd = rec["score_breakdown"]
        rec_id = f"fcs-{rec['team_id']}"
        standing = db.query(FinaleChampionshipStandingModel).filter(
            FinaleChampionshipStandingModel.id == rec_id
        ).first()

        if not standing:
            standing = FinaleChampionshipStandingModel(
                id=rec_id,
                team_id=rec["team_id"],
                team_number=rec["team_number"],
                team_name=rec["team_name"],
                legal_battle_score=bd["legal_battle_score"],
                agent_guessing_points=bd["agent_guessing_points"],
                remaining_black_market_points=bd["remaining_black_market_points"],
                black_market_carryover_points=bd["black_market_component"],
                final_score=bd["final_score"],
                rank=rec["rank"],
                is_top_four=rec["is_top_four"],
                podium_position=rec.get("podium_position"),
                placement_title=rec.get("placement_title"),
                tie_requires_review=rec.get("tie_requires_review", False),
                tie_reason=rec.get("tie_reason"),
                is_tie_resolved=True,
                resolved_by=actor_id,
                resolved_at=now,
                created_at=now,
                updated_at=now,
            )
            db.add(standing)
        else:
            standing.legal_battle_score = bd["legal_battle_score"]
            standing.agent_guessing_points = bd["agent_guessing_points"]
            standing.remaining_black_market_points = bd["remaining_black_market_points"]
            standing.black_market_carryover_points = bd["black_market_component"]
            standing.final_score = bd["final_score"]
            standing.rank = rec["rank"]
            standing.is_top_four = rec["is_top_four"]
            standing.podium_position = rec.get("podium_position")
            standing.placement_title = rec.get("placement_title")
            standing.is_tie_resolved = True
            standing.resolved_by = actor_id
            standing.resolved_at = now
            standing.updated_at = now

    # Record RoundQualification for Round 5 (Podium advancement snapshots)
    advancing_team_ids = [r["team_id"] for r in records if r.get("podium_position") is not None]
    record_round_finalization(
        db=db,
        round_number=5,
        records=records,
        advancing_team_ids=advancing_team_ids,
        finalized_by=actor_id,
    )

    # Seal Finale configuration
    cfg.is_finalized = True
    cfg.finalized_at = now
    cfg.finalized_by = actor_id
    cfg.is_guessing_open = False

    # Seal RoundState model
    r5_state = db.query(RoundState).filter(RoundState.id == 5).first()
    if r5_state:
        r5_state.is_finalized = True
        r5_state.status = "Completed"

    log_audit_event(
        db=db,
        action="CHAMPIONSHIP_FINALIZED",
        entity_type="FinaleConfig",
        entity_id="1",
        actor_id=actor_id,
        actor_role=actor_role_str,
        round_number=5,
        details={
            "champion_team_id": standings.get("champion_team_id"),
            "runner_up1_team_id": standings.get("runner_up1_team_id"),
            "runner_up2_team_id": standings.get("runner_up2_team_id"),
            "override_discrepancy": override_discrepancy,
        },
    )
    db.commit()
    db.refresh(cfg)

    return {
        "can_finalize": True,
        "issues": [],
        "finalized": True,
        "champion_team_id": standings.get("champion_team_id"),
        "runner_up1_team_id": standings.get("runner_up1_team_id"),
        "runner_up2_team_id": standings.get("runner_up2_team_id"),
        "message": "Tournament Grand Championship successfully finalized.",
    }