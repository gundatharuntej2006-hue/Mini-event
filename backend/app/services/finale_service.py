import uuid
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.models.finale import (
    FinaleConfigModel,
    FinaleScorecardModel,
    FinaleAgentVerdictModel,
    FinaleTeamGuessSubmissionModel,
    FinaleAgentGuessModel,
    default_finale_criteria,
)
from app.models.team import Team
from app.models.participant import Participant
from app.models.agent import SecretAgentDossier, SecretAgentTask, AgentTaskStatus
from app.models.wallet import TeamWallet
from app.models.progression import RoundQualification, TieReview
from app.core.constants import (
    AGENT_CORRECT_GUESS,
    AGENT_WRONG_GUESS,
    AGENT_GUESS_MIN,
    AGENT_GUESS_MAX,
    DEFAULT_CARRYOVER_WEIGHT_PERCENT,
    R4_ADVANCING_COUNT,
)
from app.scoring.finale_scoring import (
    validate_team_guesses,
    evaluate_single_guess,
    calculate_team_guessing_score,
    calculate_best_secret_agent,
    calculate_overall_final_score,
    process_finale_guessing_standings,
    calculate_scorecard_total,
    calculate_finale_score_breakdown,
    process_finale_standings,
)
from app.services.audit_service import log_audit_event
from app.services.progression_service import (
    is_round_finalized,
    get_eligible_team_ids,
    record_round_finalization,
)
from app.services.tie_review_service import get_or_create_tie_review
from app.schemas.rounds.finale import (
    SubmitTeamGuessesInput,
    SubmitScorecardInput,
    SubmitAgentVerdictInput,
)


# ==============================================================================
# 1. CONFIGURATION SERVICE
# ==============================================================================

def get_or_create_finale_config(db: Session) -> FinaleConfigModel:
    """Fetches or initializes the Grand Finale configuration record."""
    cfg = db.query(FinaleConfigModel).filter(FinaleConfigModel.id == 1).first()
    if not cfg:
        cfg = FinaleConfigModel(
            id=1,
            is_scoring_rules_confirmed=True,
            criteria=default_finale_criteria(),
            round4_score_carried_over=True,
            round4_score_weight=1.0,
            finale_activity_weight=1.0,
            advancing_teams_count=R4_ADVANCING_COUNT,
            min_guesses=AGENT_GUESS_MIN,
            max_guesses=AGENT_GUESS_MAX,
            correct_guess_points=AGENT_CORRECT_GUESS,
            wrong_guess_points=AGENT_WRONG_GUESS,
            carryover_wallet_percent=DEFAULT_CARRYOVER_WEIGHT_PERCENT,
            is_guessing_open=True,
            scoring_direction="higher_wins",
            is_finalized=False,
            is_revealed=False,
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def update_finale_config(db: Session, updates: Dict[str, Any], actor) -> FinaleConfigModel:
    """Updates Grand Finale configuration settings (Organizers only)."""
    cfg = get_or_create_finale_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grand Finale is finalized. Configuration locked.")

    if "is_scoring_rules_confirmed" in updates and updates["is_scoring_rules_confirmed"] is not None:
        cfg.is_scoring_rules_confirmed = bool(updates["is_scoring_rules_confirmed"])
        if cfg.is_scoring_rules_confirmed and not cfg.confirmed_at:
            cfg.confirmed_at = datetime.now(timezone.utc)
            cfg.confirmed_by = getattr(actor, "id", str(actor))

    if "criteria" in updates and updates["criteria"]:
        cfg.criteria = updates["criteria"]
    if "round4_score_carried_over" in updates and updates["round4_score_carried_over"] is not None:
        cfg.round4_score_carried_over = bool(updates["round4_score_carried_over"])
    if "round4_score_weight" in updates and updates["round4_score_weight"] is not None:
        cfg.round4_score_weight = float(updates["round4_score_weight"])
    if "finale_activity_weight" in updates and updates["finale_activity_weight"] is not None:
        cfg.finale_activity_weight = float(updates["finale_activity_weight"])
    if "advancing_teams_count" in updates and updates["advancing_teams_count"] is not None:
        cfg.advancing_teams_count = int(updates["advancing_teams_count"])
    if "min_guesses" in updates and updates["min_guesses"] is not None:
        cfg.min_guesses = int(updates["min_guesses"])
    if "max_guesses" in updates and updates["max_guesses"] is not None:
        cfg.max_guesses = int(updates["max_guesses"])
    if "correct_guess_points" in updates and updates["correct_guess_points"] is not None:
        cfg.correct_guess_points = float(updates["correct_guess_points"])
    if "wrong_guess_points" in updates and updates["wrong_guess_points"] is not None:
        cfg.wrong_guess_points = float(updates["wrong_guess_points"])
    if "carryover_wallet_percent" in updates and updates["carryover_wallet_percent"] is not None:
        cfg.carryover_wallet_percent = float(updates["carryover_wallet_percent"])
    if "is_guessing_open" in updates and updates["is_guessing_open"] is not None:
        cfg.is_guessing_open = bool(updates["is_guessing_open"])
    if "scoring_direction" in updates and updates["scoring_direction"]:
        cfg.scoring_direction = updates["scoring_direction"]

    log_audit_event(
        db=db,
        action="FINALE_CONFIG_UPDATED",
        entity_type="FinaleConfig",
        entity_id="1",
        actor_id=getattr(actor, "id", str(actor)),
        actor_role=getattr(actor, "role", "ORGANIZER"),
        round_number=5,
        details={"is_scoring_rules_confirmed": cfg.is_scoring_rules_confirmed},
    )
    db.commit()
    db.refresh(cfg)
    return cfg


# ==============================================================================
# 2. SECRET AGENT GUESS SUBMISSION & RETRIEVAL (STEP 14)
# ==============================================================================

def submit_team_guesses(
    db: Session,
    guessing_team_id: str,
    input_data: SubmitTeamGuessesInput,
    actor,
) -> FinaleTeamGuessSubmissionModel:
    """
    Submits and evaluates secret agent guesses for a finalist squad (1 to 5 guesses).
    Evaluates against active dossiers with +30.0 / -20.0 points.
    Enforces security, confidentiality, and bounds checks.
    """
    cfg = get_or_create_finale_config(db)
    if cfg.is_finalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Grand Finale is already finalized. Guess submissions are closed.",
        )
    if not cfg.is_guessing_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Secret Agent guessing is currently closed by tournament organizers.",
        )

    # Progression Gate: Round 4 must be finalized
    if not is_round_finalized(db, 4):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Round 4: The Legal Battle must be finalized before Grand Finale guesses can be submitted.",
        )

    eligible_team_ids = get_eligible_team_ids(db, 5)
    if not eligible_team_ids:
        # Fallback to registered teams if progression not populated
        eligible_team_ids = [t.id for t in db.query(Team).limit(cfg.advancing_teams_count or 8).all()]

    if eligible_team_ids and guessing_team_id not in eligible_team_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team '{guessing_team_id}' is not an official qualified finalist squad from Round 4.",
        )

    # Actor authorization check: TEAM users can only submit for their own squad
    actor_role = getattr(actor, "role", None)
    actor_role_str = actor_role.value if hasattr(actor_role, "value") else str(actor_role).upper()
    if actor_role_str == "TEAM":
        actor_team_id = getattr(actor, "team_id", None)
        if actor_team_id and actor_team_id != guessing_team_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Squads cannot submit secret agent guesses on behalf of other teams.",
            )

    # Validate guesses using scoring rules engine
    raw_guesses = [g.model_dump(by_alias=True) for g in input_data.guesses]
    val_res = validate_team_guesses(
        guessing_team_id=guessing_team_id,
        guesses=raw_guesses,
        finalist_team_ids=eligible_team_ids,
        min_guesses=cfg.min_guesses,
        max_guesses=cfg.max_guesses,
    )
    if not val_res["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(val_res["errors"]),
        )

    # Build dossier lookup map for unmasking evaluation
    all_dossiers = db.query(SecretAgentDossier).all()
    dossier_map: Dict[str, Dict[str, Any]] = {}
    for d in all_dossiers:
        p = db.query(Participant).filter(Participant.id == d.participant_id).first()
        dossier_map[d.team_id] = {
            "participant_id": d.participant_id,
            "codename": d.codename,
            "participant_name": p.name if p else "",
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
        }

    # Evaluate each guess
    evaluated_guesses: List[Dict[str, Any]] = []
    for g in input_data.guesses:
        g_dict = g.model_dump()
        evaluated = evaluate_single_guess(
            guess=g_dict,
            dossier_map=dossier_map,
            correct_points=cfg.correct_guess_points,
            wrong_points=cfg.wrong_guess_points,
        )
        evaluated_guesses.append(evaluated)

    # Compute aggregate team score
    summary = calculate_team_guessing_score(guessing_team_id, evaluated_guesses)

    submission_id = f"fg-sub-{guessing_team_id}"
    now = datetime.now(timezone.utc)
    actor_id = getattr(actor, "id", str(actor))

    submission = db.query(FinaleTeamGuessSubmissionModel).filter(
        FinaleTeamGuessSubmissionModel.id == submission_id
    ).first()

    if not submission:
        submission = FinaleTeamGuessSubmissionModel(
            id=submission_id,
            guessing_team_id=guessing_team_id,
            total_guesses=summary["total_guesses"],
            correct_guesses=summary["correct_guesses"],
            wrong_guesses=summary["wrong_guesses"],
            total_guessing_points=summary["total_guessing_points"],
            is_submitted=True,
            submitted_at=now,
            submitted_by=actor_id,
        )
        db.add(submission)
        db.flush()
    else:
        submission.total_guesses = summary["total_guesses"]
        submission.correct_guesses = summary["correct_guesses"]
        submission.wrong_guesses = summary["wrong_guesses"]
        submission.total_guessing_points = summary["total_guessing_points"]
        submission.is_submitted = True
        submission.submitted_at = now
        submission.submitted_by = actor_id

    # Replace guess items
    db.query(FinaleAgentGuessModel).filter(
        FinaleAgentGuessModel.submission_id == submission_id
    ).delete()

    for eg in evaluated_guesses:
        guess_rec = FinaleAgentGuessModel(
            id=f"fag-{uuid.uuid4().hex[:8]}",
            submission_id=submission_id,
            guessing_team_id=guessing_team_id,
            target_team_id=eg["target_team_id"],
            suspected_participant_id=eg.get("suspected_participant_id"),
            suspected_agent_name=eg.get("suspected_agent_name"),
            is_resolved=True,
            is_correct=eg["is_correct"],
            points_awarded=eg["points_awarded"],
            notes=eg.get("notes"),
            created_at=now,
        )
        db.add(guess_rec)

    log_audit_event(
        db=db,
        action="FINALE_GUESSES_SUBMITTED",
        entity_type="FinaleTeamGuessSubmission",
        entity_id=submission_id,
        actor_id=actor_id,
        actor_role=actor_role_str,
        round_number=5,
        details={
            "guessing_team_id": guessing_team_id,
            "total_guesses": summary["total_guesses"],
            "correct_guesses": summary["correct_guesses"],
            "wrong_guesses": summary["wrong_guesses"],
            "total_guessing_points": summary["total_guessing_points"],
        },
    )
    db.commit()
    db.refresh(submission)
    return submission


def get_team_guesses(
    db: Session,
    team_id: str,
    is_organizer: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Fetches guess submission for a specific squad.
    Confidentiality Guard: If viewer is not an organizer and results have not been revealed,
    masks correctness and points.
    """
    cfg = get_or_create_finale_config(db)
    submission_id = f"fg-sub-{team_id}"
    submission = db.query(FinaleTeamGuessSubmissionModel).filter(
        FinaleTeamGuessSubmissionModel.id == submission_id
    ).first()

    if not submission:
        return None

    team = db.query(Team).filter(Team.id == team_id).first()
    is_revealed = bool(cfg.is_revealed)
    can_view_unmasked = is_organizer or is_revealed

    guesses_res = []
    for g in (submission.guesses or []):
        target_t = db.query(Team).filter(Team.id == g.target_team_id).first()
        guesses_res.append({
            "id": g.id,
            "guessing_team_id": g.guessing_team_id,
            "target_team_id": g.target_team_id,
            "target_team_name": target_t.name if target_t else None,
            "suspected_participant_id": g.suspected_participant_id,
            "suspected_agent_name": g.suspected_agent_name,
            "is_resolved": g.is_resolved if can_view_unmasked else False,
            "is_correct": g.is_correct if can_view_unmasked else None,
            "points_awarded": g.points_awarded if can_view_unmasked else None,
            "notes": g.notes,
            "created_at": g.created_at.isoformat() if g.created_at else None,
        })

    return {
        "id": submission.id,
        "guessing_team_id": submission.guessing_team_id,
        "guessing_team_name": team.name if team else None,
        "total_guesses": submission.total_guesses,
        "correct_guesses": submission.correct_guesses if can_view_unmasked else None,
        "wrong_guesses": submission.wrong_guesses if can_view_unmasked else None,
        "total_guessing_points": submission.total_guessing_points if can_view_unmasked else None,
        "is_submitted": submission.is_submitted,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "submitted_by": submission.submitted_by if can_view_unmasked else None,
        "guesses": guesses_res,
    }


# ==============================================================================
# 3. BEST SECRET AGENT RESOLUTION (STEP 14)
# ==============================================================================

def get_best_secret_agent_data(
    db: Session,
    is_organizer: bool = False,
) -> Dict[str, Any]:
    """
    Computes Best Secret Agent ranking across all active agents.
    Sorts by:
    1. Most verified Secret Agent tasks (descending).
    2. Fewest correct guesses received (ascending).
    Flags tie_requires_review = True if tied on both criteria.
    """
    cfg = get_or_create_finale_config(db)
    is_revealed = bool(cfg.is_revealed) or bool(getattr(cfg, "is_agents_revealed", False))
    can_view_unmasked = is_organizer or is_revealed

    dossiers = db.query(SecretAgentDossier).all()
    all_guesses = db.query(FinaleAgentGuessModel).all()

    dossier_data_list: List[Dict[str, Any]] = []
    for d in dossiers:
        t = db.query(Team).filter(Team.id == d.team_id).first()
        p = db.query(Participant).filter(Participant.id == d.participant_id).first()

        # Count verified tasks for this agent
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
        {
            "target_team_id": g.target_team_id,
            "is_correct": g.is_correct,
        }
        for g in all_guesses
    ]

    result = calculate_best_secret_agent(dossier_data_list, all_evaluated)

    # If non-organizer before reveal, mask confidential identities
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


# ==============================================================================
# 4. FINALE OVERVIEW & STANDINGS ENGINE (STEP 14)
# ==============================================================================

def get_finale_overview(db: Session, actor=None) -> Dict[str, Any]:
    """
    Aggregates complete Grand Finale standings, scoring breakdowns, checklist items,
    and safeguards for all 8 finalist squads.
    Overall Score = R4 Legal Battle + Agent Guessing Points + 10% Black Market Wallet.
    """
    cfg = get_or_create_finale_config(db)
    r4_finalized = is_round_finalized(db, 4)

    is_organizer = True
    if actor:
        actor_role = getattr(actor, "role", None)
        actor_role_str = actor_role.value if hasattr(actor_role, "value") else str(actor_role).upper()
        is_organizer = actor_role_str in ("ORGANIZER", "ADMIN", "LEAD_JUDGE", "MARSHAL", "SCOREKEEPER")

    eligible_team_ids = get_eligible_team_ids(db, 5)
    if eligible_team_ids:
        teams = db.query(Team).filter(Team.id.in_(eligible_team_ids)).order_by(Team.team_number.asc()).all()
    else:
        teams = db.query(Team).order_by(Team.team_number.asc()).limit(cfg.advancing_teams_count or 8).all()

    # Load Round 4 carried scores from qualification records
    r4_quals = {
        q.team_id: q for q in db.query(RoundQualification).filter(RoundQualification.round_number == 4).all()
    }

    # Load Team Wallets for 10% carryover
    wallets = {w.team_id: w for w in db.query(TeamWallet).all()}

    # Load guess submissions
    submissions = {
        s.guessing_team_id: s for s in db.query(FinaleTeamGuessSubmissionModel).all()
    }

    # Load scorecards for legacy activity support
    scorecards = {sc.team_id: sc for sc in db.query(FinaleScorecardModel).all()}

    raw_records = []
    for team in teams:
        r4_qual = r4_quals.get(team.id)
        r4_score = r4_qual.score_snapshot if r4_qual else None

        wallet = wallets.get(team.id)
        wallet_balance = getattr(wallet, "current_balance", getattr(wallet, "balance", 1000.0)) if wallet else 1000.0

        sub = submissions.get(team.id)
        guessing_points = sub.total_guessing_points if sub else 0.0

        # Overall final score calculation
        breakdown = calculate_overall_final_score(
            round4_score=r4_score,
            guessing_points=guessing_points,
            wallet_balance=wallet_balance,
            carryover_percent=cfg.carryover_wallet_percent,
        )

        sub_dto = get_team_guesses(db, team.id, is_organizer=is_organizer)

        sc = scorecards.get(team.id)
        sc_dict = {
            "team_id": team.id,
            "judge_name": sc.judge_name if sc else "Faculty Panel",
            "scores": sc.scores if sc else {},
            "total_score": sc.total_score if sc else None,
            "is_complete": sc.is_complete if sc else False,
            "submitted_at": sc.submitted_at.isoformat() if sc and sc.submitted_at else None,
            "comments": sc.comments if sc else None,
        }

        # Mask guessing points in score breakdown for teams before reveal
        if not is_organizer and not cfg.is_revealed:
            breakdown["agent_guessing_points"] = None
            breakdown["total_final_score"] = None

        has_submitted = sub.is_submitted if sub else False
        raw_records.append({
            "team_id": team.id,
            "team_number": team.team_number,
            "team_name": team.name,
            "submission": sub_dto,
            "guesses_submitted": has_submitted,
            "scorecard": sc_dict,
            "score_breakdown": breakdown,
            "review_status": "Guesses Submitted" if has_submitted else "Pending Guesses",
        })

    standings = process_finale_guessing_standings(
        records=raw_records,
        config={
            "is_scoring_rules_confirmed": cfg.is_scoring_rules_confirmed,
            "advancing_teams_count": cfg.advancing_teams_count or R4_ADVANCING_COUNT,
            "scoring_direction": cfg.scoring_direction,
        },
        round4_finalized=r4_finalized,
    )

    # Tie Review Safeguard for Podium Ties
    if standings.get("ties_affecting_placement"):
        tied_team_recs = [r for r in standings["records"] if r["team_id"] in standings["tied_teams"]]
        get_or_create_tie_review(
            db=db,
            round_number=5,
            teams_involved=tied_team_recs,
            ranking_metric="total_final_score",
            cutoff_position=1,
            notes="Podium placement tie for championship honors requires explicit manual marshal determination.",
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
            "advancing_teams_count": cfg.advancing_teams_count or R4_ADVANCING_COUNT,
            "min_guesses": cfg.min_guesses,
            "max_guesses": cfg.max_guesses,
            "correct_guess_points": cfg.correct_guess_points,
            "wrong_guess_points": cfg.wrong_guess_points,
            "carryover_wallet_percent": cfg.carryover_wallet_percent,
            "is_guessing_open": cfg.is_guessing_open,
            "scoring_direction": cfg.scoring_direction,
            "is_finalized": cfg.is_finalized,
            "finalized_at": cfg.finalized_at.isoformat() if cfg.finalized_at else None,
            "finalized_by": cfg.finalized_by,
            "is_revealed": cfg.is_revealed,
            "revealed_at": cfg.revealed_at.isoformat() if cfg.revealed_at else None,
            "revealed_by": cfg.revealed_by,
        },
        "records": standings["records"],
        "can_finalize": standings["can_finalize"],
        "issues": standings["issues"],
        "checklist": standings["checklist"],
        "ties_affecting_placement": standings["ties_affecting_placement"],
        "is_revealed": cfg.is_revealed,
        "champion_team_id": standings["champion_team_id"],
        "runner_up1_team_id": standings["runner_up1_team_id"],
        "runner_up2_team_id": standings["runner_up2_team_id"],
    }


# ==============================================================================
# 5. FINALIZATION & REVEAL WORKFLOW
# ==============================================================================

def finalize_grand_finale(
    db: Session,
    actor,
    override_discrepancy: bool = False,
) -> Dict[str, Any]:
    """
    Officially seals the Grand Finale / Secret Agent Guessing round.
    Idempotent: Subsequent calls return successful sealed state without duplicate mutation.
    """
    cfg = get_or_create_finale_config(db)
    if cfg.is_finalized:
        return {
            "can_finalize": True,
            "issues": [],
            "finalized": True,
            "message": "Grand Finale has already been officially finalized.",
        }

    overview = get_finale_overview(db, actor=actor)
    can_fin = overview["can_finalize"] or override_discrepancy
    if not can_fin:
        return {
            "can_finalize": False,
            "issues": overview["issues"],
            "finalized": False,
            "message": "Finalization blocked by server-side safeguards.",
        }

    records = overview["records"]
    advancing_team_ids = [overview["champion_team_id"]] if overview.get("champion_team_id") else []
    actor_id = getattr(actor, "id", str(actor))
    actor_role = getattr(actor, "role", "ORGANIZER")
    actor_role_str = actor_role.value if hasattr(actor_role, "value") else str(actor_role).upper()

    record_round_finalization(
        db=db,
        round_number=5,
        records=records,
        advancing_team_ids=advancing_team_ids,
        finalized_by=actor_id,
    )

    now = datetime.now(timezone.utc)
    cfg.is_finalized = True
    cfg.finalized_at = now
    cfg.finalized_by = actor_id
    cfg.is_guessing_open = False

    log_audit_event(
        db=db,
        action="ROUND_FINALIZED",
        entity_type="FinaleConfig",
        entity_id="1",
        actor_id=actor_id,
        actor_role=actor_role_str,
        round_number=5,
        details={
            "champion_team_id": overview["champion_team_id"],
            "runner_up1_team_id": overview["runner_up1_team_id"],
            "runner_up2_team_id": overview["runner_up2_team_id"],
            "override_discrepancy": override_discrepancy,
        },
    )
    db.commit()

    return {
        "can_finalize": True,
        "issues": [],
        "finalized": True,
        "champion_team_id": overview["champion_team_id"],
        "message": "Grand Finale officially sealed. Secret Agent Guessing and Championship standings locked.",
    }


def reveal_finale_results(db: Session, actor) -> Dict[str, Any]:
    """
    Unveils unmasked Secret Agents and Guessing scores to all participants.
    """
    cfg = get_or_create_finale_config(db)
    actor_id = getattr(actor, "id", str(actor))
    actor_role = getattr(actor, "role", "ORGANIZER")
    actor_role_str = actor_role.value if hasattr(actor_role, "value") else str(actor_role).upper()

    now = datetime.now(timezone.utc)
    cfg.is_revealed = True
    cfg.revealed_at = now
    cfg.revealed_by = actor_id

    log_audit_event(
        db=db,
        action="FINALE_RESULTS_REVEALED",
        entity_type="FinaleConfig",
        entity_id="1",
        actor_id=actor_id,
        actor_role=actor_role_str,
        round_number=5,
        details={"revealed_by": actor_id},
    )
    db.commit()

    return {
        "is_revealed": True,
        "revealed_at": now.isoformat(),
        "message": "Grand Finale unmasking results and scores officially revealed!",
    }


# ==============================================================================
# 6. LEGACY SCORECARD & VERDICT COMPATIBILITY
# ==============================================================================

def submit_scorecard(db: Session, team_id: str, input_data: SubmitScorecardInput, actor) -> FinaleScorecardModel:
    cfg = get_or_create_finale_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Grand Finale is finalized.")

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
            comments=input_data.comments,
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
        actor_id=getattr(actor, "id", str(actor)),
        actor_role=getattr(actor, "role", "JUDGE"),
        round_number=5,
        details={"team_id": team_id, "total_score": sc.total_score, "is_complete": sc.is_complete},
    )
    db.commit()
    db.refresh(sc)
    return sc


def submit_agent_verdict(db: Session, team_id: str, input_data: SubmitAgentVerdictInput, actor) -> FinaleAgentVerdictModel:
    v = db.query(FinaleAgentVerdictModel).filter(FinaleAgentVerdictModel.team_id == team_id).first()
    now = datetime.now(timezone.utc)
    actor_id = getattr(actor, "id", str(actor))
    if not v:
        v = FinaleAgentVerdictModel(
            team_id=team_id,
            suspected_agent=input_data.suspected_agent,
            actual_agent=input_data.actual_agent,
            is_correct=input_data.is_correct,
            bonus_points=input_data.bonus_points,
            penalty_points=input_data.penalty_points,
            is_verified=True,
            verified_by=actor_id,
            verified_at=now,
            notes=input_data.notes,
        )
        db.add(v)
    else:
        v.suspected_agent = input_data.suspected_agent
        v.actual_agent = input_data.actual_agent
        v.is_correct = input_data.is_correct
        v.bonus_points = input_data.bonus_points
        v.penalty_points = input_data.penalty_points
        v.is_verified = True
        v.verified_by = actor_id
        v.verified_at = now
        v.notes = input_data.notes

    log_audit_event(
        db=db,
        action="FINALE_AGENT_VERDICT_SUBMITTED",
        entity_type="FinaleAgentVerdict",
        entity_id=team_id,
        actor_id=actor_id,
        actor_role=getattr(actor, "role", "ORGANIZER"),
        round_number=5,
        details={"team_id": team_id, "is_correct": v.is_correct},
    )
    db.commit()
    db.refresh(v)
    return v
