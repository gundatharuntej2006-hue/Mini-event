from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.common import ApiResponse, FinalizationResponse
from app.schemas.rounds.finale import (
    FinaleGuessingOverviewResponse,
    FinaleConfigSchema,
    UpdateFinaleConfigInput,
    SubmitTeamGuessesInput,
    TeamGuessSubmissionResponse,
    BestSecretAgentResponse,
    SubmitScorecardInput,
    SubmitAgentVerdictInput,
    FinaleTeamGuessRecordResponse,
    FinalChampionshipScoreResponse,
    ChampionshipStandingItemResponse,
    TopFourResponse,
    PodiumResponse,
    ResolveTieInput,
    RevealStageInput,
)
from app.services import finale_service, championship_service

router = APIRouter(tags=["Grand Finale & Secret Agent Unmasking"])


# ==============================================================================
# 1. OVERVIEW & CONFIGURATION
# ==============================================================================

@router.get("", response_model=ApiResponse[Dict[str, Any]])
@router.get("/overview", response_model=ApiResponse[Dict[str, Any]])
def get_finale_overview_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get complete Grand Finale overview, 8 finalist squad standings, score breakdown
    (R4 Legal Battle + Agent Guessing + 10% Black Market Wallet), and verification checklist.
    """
    data = finale_service.get_finale_overview(db, actor=current_user)
    return ApiResponse(data=data, message="Grand Finale overview loaded successfully")


@router.get("/config", response_model=ApiResponse[FinaleConfigSchema])
def get_config(db: Session = Depends(get_db)):
    """Get Grand Finale configuration, guess limits (1-5), points (+30/-20), and rule confirmation status."""
    cfg = finale_service.get_or_create_finale_config(db)
    res = FinaleConfigSchema(
        is_scoring_rules_confirmed=cfg.is_scoring_rules_confirmed,
        confirmed_at=cfg.confirmed_at.isoformat() if cfg.confirmed_at else None,
        confirmed_by=cfg.confirmed_by,
        criteria=cfg.criteria or [],
        round4_score_carried_over=cfg.round4_score_carried_over,
        round4_score_weight=cfg.round4_score_weight,
        finale_activity_weight=cfg.finale_activity_weight,
        advancing_teams_count=cfg.advancing_teams_count or 8,
        min_guesses=cfg.min_guesses,
        max_guesses=cfg.max_guesses,
        correct_guess_points=cfg.correct_guess_points,
        wrong_guess_points=cfg.wrong_guess_points,
        carryover_wallet_percent=cfg.carryover_wallet_percent,
        is_guessing_open=cfg.is_guessing_open,
        scoring_direction=cfg.scoring_direction,
        is_finalized=cfg.is_finalized,
        finalized_at=cfg.finalized_at.isoformat() if cfg.finalized_at else None,
        finalized_by=cfg.finalized_by,
        is_revealed=cfg.is_revealed,
        revealed_at=cfg.revealed_at.isoformat() if cfg.revealed_at else None,
        revealed_by=cfg.revealed_by,
    )
    return ApiResponse(data=res)


@router.put("/config", response_model=ApiResponse[FinaleConfigSchema])
def update_config(
    payload: UpdateFinaleConfigInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Update Grand Finale rules, bounds (1-5), carryover percent, or guessing status (Organizers only)."""
    cfg = finale_service.update_finale_config(db, payload.model_dump(exclude_unset=True), actor)
    res = FinaleConfigSchema(
        is_scoring_rules_confirmed=cfg.is_scoring_rules_confirmed,
        confirmed_at=cfg.confirmed_at.isoformat() if cfg.confirmed_at else None,
        confirmed_by=cfg.confirmed_by,
        criteria=cfg.criteria or [],
        round4_score_carried_over=cfg.round4_score_carried_over,
        round4_score_weight=cfg.round4_score_weight,
        finale_activity_weight=cfg.finale_activity_weight,
        advancing_teams_count=cfg.advancing_teams_count or 8,
        min_guesses=cfg.min_guesses,
        max_guesses=cfg.max_guesses,
        correct_guess_points=cfg.correct_guess_points,
        wrong_guess_points=cfg.wrong_guess_points,
        carryover_wallet_percent=cfg.carryover_wallet_percent,
        is_guessing_open=cfg.is_guessing_open,
        scoring_direction=cfg.scoring_direction,
        is_finalized=cfg.is_finalized,
        finalized_at=cfg.finalized_at.isoformat() if cfg.finalized_at else None,
        finalized_by=cfg.finalized_by,
        is_revealed=cfg.is_revealed,
        revealed_at=cfg.revealed_at.isoformat() if cfg.revealed_at else None,
        revealed_by=cfg.revealed_by,
    )
    return ApiResponse(data=res, message="Grand Finale configuration updated")


# ==============================================================================
# 2. SECRET AGENT GUESSING ENDPOINTS (STEP 14)
# ==============================================================================

@router.post("/guesses", response_model=ApiResponse[Dict[str, Any]])
@router.post("/guesses/submit", response_model=ApiResponse[Dict[str, Any]])
@router.post("/guesses/{team_id}", response_model=ApiResponse[Dict[str, Any]])
def submit_guesses_api(
    payload: SubmitTeamGuessesInput,
    team_id: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    """
    Submit 1 to 5 secret agent unmasking guesses for a finalist squad.
    Awards +30.0 points per correct guess, -20.0 penalty per wrong guess.
    Self-guessing and duplicate targets are rejected.
    """
    actor_role = actor.role.value if hasattr(actor.role, "value") else str(actor.role).upper()
    target_team = team_id if (team_id and team_id != "submit") else payload.guessing_team_id
    if not target_team and actor_role == "TEAM":
        target_team = getattr(actor, "team_id", None)

    if not target_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="guessing_team_id is required.",
        )

    sub = finale_service.submit_team_guesses(db, target_team, payload, actor)
    is_organizer = actor_role in ("ORGANIZER", "ADMIN", "LEAD_JUDGE", "MARSHAL")

    return ApiResponse(
        data={
            "id": sub.id,
            "guessing_team_id": sub.guessing_team_id,
            "total_guesses": sub.total_guesses,
            "correct_guesses": sub.correct_guesses if is_organizer else None,
            "wrong_guesses": sub.wrong_guesses if is_organizer else None,
            "total_guessing_points": sub.total_guessing_points if is_organizer else None,
            "is_submitted": sub.is_submitted,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        },
        message="Secret agent guesses submitted successfully"
    )


@router.get("/guesses", response_model=ApiResponse[Optional[Dict[str, Any]]])
@router.get("/guesses/{team_id}", response_model=ApiResponse[Optional[Dict[str, Any]]])
def get_team_guesses_api(
    team_id: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    """
    Retrieve secret agent guesses for a squad.
    Confidentiality Guard: Teams only see their own guesses, and correctness/points
    are masked until official reveal.
    """
    actor_role = actor.role.value if hasattr(actor.role, "value") else str(actor.role).upper()
    target_team = team_id
    if not target_team and actor_role == "TEAM":
        target_team = getattr(actor, "team_id", None)

    if not target_team and actor_role in ("ORGANIZER", "ADMIN"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="team_id is required for organizer lookup.")

    if not target_team:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="team_id is required.")

    is_organizer = actor_role in ("ORGANIZER", "ADMIN", "LEAD_JUDGE", "MARSHAL")
    if not is_organizer and getattr(actor, "team_id", None) != target_team:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view another squad's secret agent guesses.",
        )

    data = finale_service.get_team_guesses(db, target_team, is_organizer=is_organizer)
    return ApiResponse(data=data, message="Secret agent guesses loaded")


# ==============================================================================
# 3. BEST SECRET AGENT RESOLUTION (STEP 14)
# ==============================================================================

@router.get("/best-secret-agent", response_model=ApiResponse[BestSecretAgentResponse])
def get_best_secret_agent_api(
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    """
    Determine the Best Secret Agent:
    1. Most verified tasks completed (descending).
    2. Fewest correct unmasking guesses received (ascending).
    Flags tie_requires_review = True if tied on both criteria.
    """
    actor_role = actor.role.value if hasattr(actor.role, "value") else str(actor.role).upper()
    is_organizer = actor_role in ("ORGANIZER", "ADMIN", "LEAD_JUDGE", "MARSHAL")
    data = finale_service.get_best_secret_agent_data(db, is_organizer=is_organizer)
    return ApiResponse(data=data, message="Best Secret Agent standings calculated")


# ==============================================================================
# 4. STEP 15 CHAMPIONSHIP LEADERBOARD, TOP 4, PODIUM & FINALIZATION
# ==============================================================================

@router.get("/final-score", response_model=ApiResponse[FinalChampionshipScoreResponse])
@router.get("/final-score/{team_id}", response_model=ApiResponse[FinalChampionshipScoreResponse])
def get_final_score_api(
    team_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get individual composite championship score breakdown:
    Final Score = Legal Battle Panel Score + Agent Guessing Points + 10% of Remaining Black Market Wallet Points.
    """
    actor_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role).upper()
    target_team = team_id
    if not target_team and actor_role == "TEAM":
        target_team = getattr(current_user, "team_id", None)
    if not target_team and actor_role in ("ORGANIZER", "ADMIN", "LEAD_JUDGE", "MARSHAL"):
        # If no team_id specified by organizer, pick first finalist
        standings = championship_service.get_championship_standings_data(db, actor=current_user)
        if standings["records"]:
            target_team = standings["records"][0]["team_id"]
    if not target_team:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="team_id is required.")

    data = championship_service.get_team_final_score(db, target_team, actor=current_user)
    return ApiResponse(data=data, message="Final championship score loaded")


@router.get("/leaderboard", response_model=ApiResponse[List[Dict[str, Any]]])
@router.get("/standings", response_model=ApiResponse[List[Dict[str, Any]]])
def get_leaderboard_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get server-side calculated overall Grand Finale championship standings for all 8 finalists."""
    standings = championship_service.get_championship_standings_data(db, actor=current_user)
    return ApiResponse(data=standings["records"])


@router.get("/top-four", response_model=ApiResponse[TopFourResponse])
def get_top_four_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Top 4 championship squads (masked for participants before official reveal)."""
    data = championship_service.get_top_four_data(db, actor=current_user)
    return ApiResponse(data=data, message=data.get("message"))


@router.get("/podium", response_model=ApiResponse[PodiumResponse])
def get_podium_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Top 3 championship podium squads (Grand Champion, 1st & 2nd Runner Up)."""
    data = championship_service.get_podium_data(db, actor=current_user)
    return ApiResponse(data=data, message=data.get("message"))


@router.get("/qualification", response_model=ApiResponse[Dict[str, Any]])
def get_qualification_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check Grand Finale readiness, checklist items, and tie safeguards."""
    standings = championship_service.get_championship_standings_data(db, actor=current_user)
    return ApiResponse(data={
        "can_finalize": standings["can_finalize"],
        "issues": standings["issues"],
        "checklist": standings["checklist"],
        "requires_organizer_review": standings["requires_organizer_review"],
        "top_four_tie_requires_review": standings["top_four_tie_requires_review"],
        "podium_tie_requires_review": standings["podium_tie_requires_review"],
        "champion_team_id": standings["champion_team_id"],
        "runner_up1_team_id": standings["runner_up1_team_id"],
        "runner_up2_team_id": standings["runner_up2_team_id"],
    })


@router.post("/finalize", response_model=ApiResponse[FinalizationResponse])
@router.post("/finalize-championship", response_model=ApiResponse[FinalizationResponse])
def finalize_finale_api(
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"])),
):
    """
    Officially seal the Grand Finale and Tournament Championship.
    Calculates all 8 composite scores, stores final standings, awards podium titles, and advances champions.
    Idempotent.
    """
    override = bool(payload and (payload.get("override_discrepancy") or payload.get("overrideDiscrepancy")))
    res = championship_service.finalize_championship(db, actor, override_discrepancy=override)
    return ApiResponse(data=res, message=res.get("message"))


@router.post("/reveal", response_model=ApiResponse[Dict[str, Any]])
def reveal_finale_results_api(
    payload: Optional[RevealStageInput] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"])),
):
    """
    Progressively or fully reveal championship outcomes to participants:
    - 'top_four': Reveals Top 4 squads
    - 'podium': Reveals Top 3 podium winners
    - 'secret_agents': Reveals secret agent identities
    - 'all': Fully reveals all tournament outcomes
    """
    stage = payload.stage if payload and payload.stage else "all"
    res = championship_service.reveal_championship_stage(db, stage=stage, actor=actor)
    return ApiResponse(data=res, message=res.get("message"))


@router.post("/resolve-tie", response_model=ApiResponse[Dict[str, Any]])
def resolve_tie_api(
    payload: ResolveTieInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"])),
):
    """
    Record organizer manual tie determination for Top 4 cutoff or podium positions.
    """
    res = championship_service.resolve_championship_tie(
        db=db,
        tie_type=payload.tie_type,
        decisions=payload.decisions,
        actor=actor,
        notes=payload.notes,
    )
    return ApiResponse(data=res, message=res.get("message"))



# ==============================================================================
# 5. LEGACY SCORECARD & VERDICT COMPATIBILITY
# ==============================================================================

@router.post("/scorecards/{team_id}", response_model=ApiResponse[Dict[str, Any]])
def submit_scorecard_api(
    team_id: str,
    payload: SubmitScorecardInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["judge", "lead_judge", "organizer", "admin"]))
):
    """Submit rubric scorecard for a finalist squad."""
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
