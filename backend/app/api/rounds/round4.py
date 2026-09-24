from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.common import ApiResponse, FinalizationResponse
from app.schemas.rounds.round4 import (
    Round4OverviewResponse, Round4ConfigSchema, UpdateRound4ConfigInput,
    CreatePairInput, AutoAssignPairsInput, UpdatePairCaseInput, UpdateStageInput,
    SubmitJudgeScoreInput, SubmitAgentGuessInput, ResourcePersonQuestionInput,
    FinalizeRound4Input, Round4PairResponse, TeamRound4RecordResponse
)
from app.services import round4_service

router = APIRouter(prefix="/rounds/4", tags=["Round 4 — The Legal Battle"])


@router.get("", response_model=ApiResponse[Round4OverviewResponse])
def get_round4(db: Session = Depends(get_db)):
    """Get complete Round 4 Moot Court overview, matchups, stages, judging, and standings."""
    data = round4_service.get_round4_overview(db)
    return ApiResponse(data=data, message="Round 4 Legal Battle overview loaded")


@router.get("/config", response_model=ApiResponse[Round4ConfigSchema])
def get_config(db: Session = Depends(get_db)):
    """Get Round 4 rubric, judging aggregation method, and formula settings."""
    cfg = round4_service.get_or_create_round4_config(db)
    res = Round4ConfigSchema(
        rubric_categories=cfg.rubric_categories or [],
        is_rubric_confirmed=cfg.is_rubric_confirmed,
        judge_aggregation=cfg.judge_aggregation,
        judges_list=cfg.judges_list or [],
        final_score_formula=cfg.final_score_formula or {},
        advancing_teams_count=cfg.advancing_teams_count or 8,
        is_finalized=cfg.is_finalized,
        finalized_at=cfg.finalized_at.isoformat() if cfg.finalized_at else None,
        finalized_by=cfg.finalized_by
    )
    return ApiResponse(data=res)


@router.put("/config", response_model=ApiResponse[Round4ConfigSchema])
def update_config(
    payload: UpdateRound4ConfigInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Update rubric or officially confirm scoring formula (Organizers only)."""
    cfg = round4_service.update_round4_config(db, payload.model_dump(exclude_unset=True), actor)
    res = Round4ConfigSchema(
        rubric_categories=cfg.rubric_categories or [],
        is_rubric_confirmed=cfg.is_rubric_confirmed,
        judge_aggregation=cfg.judge_aggregation,
        judges_list=cfg.judges_list or [],
        final_score_formula=cfg.final_score_formula or {},
        advancing_teams_count=cfg.advancing_teams_count or 8,
        is_finalized=cfg.is_finalized,
        finalized_at=cfg.finalized_at.isoformat() if cfg.finalized_at else None,
        finalized_by=cfg.finalized_by
    )
    return ApiResponse(data=res, message="Round 4 configuration updated")


@router.get("/pairs", response_model=ApiResponse[List[Round4PairResponse]])
def get_pairs(db: Session = Depends(get_db)):
    """Get all 4 moot court matchups with stage timings and legal file status."""
    overview = round4_service.get_round4_overview(db)
    return ApiResponse(data=overview["pairs"])


@router.post("/pairs", response_model=ApiResponse[Dict[str, Any]])
def update_pair_api(
    payload: CreatePairInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Assign squads to a head-to-head matchup pairing (1 to 4)."""
    p = round4_service.update_pair(
        db=db,
        pair_number=payload.pair_number,
        team_a_id=payload.team_a_id,
        team_b_id=payload.team_b_id,
        case_name=payload.case_name,
        team_a_side=payload.team_a_side,
        team_b_side=payload.team_b_side,
        actor=actor
    )
    return ApiResponse(data={"pair_id": p.id, "pair_number": p.pair_number}, message="Pairing assigned")


@router.post("/pairs/auto", response_model=ApiResponse[List[Round4PairResponse]])
def auto_pair_api(
    payload: Optional[AutoAssignPairsInput] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Automatically pair the 8 finalist squads into 4 head-to-head courtroom matchups."""
    seed = payload.seed if payload else None
    confirm = payload.confirm if payload else True
    round4_service.auto_pair_round4_teams(db, actor=actor, seed=seed, confirm=confirm)
    overview = round4_service.get_round4_overview(db)
    return ApiResponse(data=overview["pairs"], message="4 head-to-head matchups generated for Round 4")


@router.post("/pairs/confirm", response_model=ApiResponse[Dict[str, Any]])
def confirm_pairs(
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Lock and confirm all 4 matchup pairings for trial arguments."""
    round4_service.confirm_pairings(db, actor)
    return ApiResponse(data={"confirmed": True}, message="All 4 pairings officially confirmed and locked")


@router.post("/pairs/unlock", response_model=ApiResponse[Dict[str, Any]])
def unlock_pairs(
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Unlock pairings for organizer adjustments prior to finalization."""
    round4_service.unlock_pairings(db, actor)
    return ApiResponse(data={"confirmed": False}, message="Pairings unlocked")


@router.put("/cases/{pair_id}", response_model=ApiResponse[Dict[str, Any]])
@router.put("/pairs/{pair_id}", response_model=ApiResponse[Dict[str, Any]])
def update_case_api(
    pair_id: str,
    payload: UpdatePairCaseInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "marshal", "admin"]))
):
    """Assign legal case title, sides, and discovery file distribution status."""
    p = round4_service.update_pair_case(db, pair_id, payload, actor)
    return ApiResponse(
        data={
            "pair_id": p.id,
            "pairId": p.id,
            "pairNumber": p.pair_number,
            "caseId": p.case_id,
            "caseName": p.case_name,
            "teamASide": p.team_a_side,
            "teamBSide": p.team_b_side,
            "teamAHasCaseFile": p.team_a_has_case_file,
            "teamBHasCaseFile": p.team_b_has_case_file,
            "resourcePersonName": p.resource_person_name,
            "resourcePersonQuestions": p.resource_person_questions_json or [],
            "isConfirmed": p.is_confirmed,
        },
        message="Case parameters updated"
    )


@router.post("/pairs/{pair_id}/questions", response_model=ApiResponse[Dict[str, Any]])
def record_question_api(
    pair_id: str,
    payload: ResourcePersonQuestionInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "marshal", "scorekeeper", "admin"]))
):
    """Record a question and answer session with the resource person."""
    p = round4_service.record_resource_person_question(db, pair_id, payload, actor)
    return ApiResponse(
        data={"pair_id": p.id, "questions_count": len(p.resource_person_questions_json or [])},
        message="Resource person question logged"
    )


@router.put("/stages/{pair_id}/{stage_id}", response_model=ApiResponse[Dict[str, Any]])
def update_stage_api(
    pair_id: str,
    stage_id: str,
    payload: UpdateStageInput,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "marshal", "scorekeeper", "admin"]))
):
    """Log courtroom stage status (prep_1, hearing_1, file_exchange, prep_2, hearing_2)."""
    round4_service.update_stage_timing(
        db=db,
        pair_id=pair_id,
        stage_id=stage_id,
        status_val=payload.status,
        duration=payload.actual_duration_seconds,
        notes=payload.notes,
        actor=actor
    )
    return ApiResponse(data={"pair_id": pair_id, "stage_id": stage_id, "status": payload.status}, message="Stage logged")


@router.get("/judging/{team_id}", response_model=ApiResponse[Dict[str, Any]])
def get_judging_for_team(team_id: str, db: Session = Depends(get_db)):
    """Get judge scorecards and panel aggregation for a team."""
    overview = round4_service.get_round4_overview(db)
    team_rec = next((r for r in overview["records"] if r["team_id"] == team_id), None)
    if not team_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team '{team_id}' not found in Round 4.")
    return ApiResponse(data=team_rec)


@router.post("/judging/{team_id}/scores", response_model=ApiResponse[Dict[str, Any]])
@router.post("/scores", response_model=ApiResponse[Dict[str, Any]])
def submit_judge_scores(
    payload: SubmitJudgeScoreInput,
    team_id: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["judge", "lead_judge", "organizer", "marshal", "admin"]))
):
    """Submit faculty judge rubric scorecard for a squad. Validates 0 <= score <= maxMarks."""
    target_team = team_id or payload.team_id
    if not target_team:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="team_id is required.")

    sc = round4_service.submit_judge_score(db, target_team, payload, actor)
    return ApiResponse(
        data={
            "id": sc.id,
            "team_id": target_team,
            "teamId": target_team,
            "judgeId": sc.judge_id,
            "judgeName": sc.judge_name,
            "scores": sc.scores,
            "total_score": sc.total_score,
            "totalScore": sc.total_score,
            "isSubmitted": sc.is_submitted,
        },
        message="Judge scorecard submitted successfully"
    )


@router.post("/teams/{team_id}/agent-guess", response_model=ApiResponse[Dict[str, Any]])
@router.post("/agent-guess", response_model=ApiResponse[Dict[str, Any]])
def submit_agent_guess_api(
    payload: SubmitAgentGuessInput,
    team_id: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "marshal", "judge", "admin"]))
):
    """Record secret agent deduction outcome and verification."""
    target_team = team_id or payload.team_id
    if not target_team:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="team_id is required.")

    ag = round4_service.submit_agent_guess(db, target_team, payload, actor)
    return ApiResponse(
        data={
            "id": ag.id,
            "team_id": target_team,
            "teamId": target_team,
            "outcome": ag.outcome,
            "points": ag.points_awarded,
            "pointsAwarded": ag.points_awarded,
            "isVerified": ag.is_verified,
        },
        message="Agent guess saved"
    )


@router.get("/leaderboard", response_model=ApiResponse[List[TeamRound4RecordResponse]])
@router.get("/standings", response_model=ApiResponse[List[Any]])
def get_leaderboard(db: Session = Depends(get_db)):
    """Get server-side calculated moot court final standings."""
    overview = round4_service.get_round4_overview(db)
    # Add legacy-friendly fields for standings endpoint
    records = overview["records"]
    for r in records:
        r["teamId"] = r.get("team_id")
        r["teamName"] = r.get("team_name")
        jury_sc = r.get("panel_score") or 0.0
        r["juryScore"] = jury_sc
        r["agentGuessPoints"] = None  # Agent guessing scored in Finale (Step 14)
        fs = r.get("final_score_breakdown", {}).get("final_score")
        r["totalScore"] = fs if fs is not None else jury_sc
    return ApiResponse(data=records)


@router.get("/qualification", response_model=ApiResponse[Dict[str, Any]])
def get_qualification(db: Session = Depends(get_db)):
    """Check Round 4 advancement checklist, cutoff ties, and readiness to seal."""
    overview = round4_service.get_round4_overview(db)
    return ApiResponse(data={
        "can_finalize": overview["can_finalize"],
        "issues": overview["issues"],
        "checklist": overview["checklist"],
        "ties_affecting_cutoff": overview["ties_affecting_cutoff"]
    })


@router.post("/finalize", response_model=ApiResponse[FinalizationResponse])
def finalize_round4(
    payload: Optional[FinalizeRound4Input] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Officially seal Round 4 results and advance all 8 finalist squads to the Grand Finale."""
    override = payload.override_discrepancy if payload else False
    res = round4_service.finalize_round4(db, actor, override_discrepancy=override)
    return ApiResponse(data=res, message=res.get("message"))


@router.get("/eligibility/{team_id}", response_model=ApiResponse[Dict[str, Any]])
def check_round4_eligibility(
    team_id: str,
    db: Session = Depends(get_db),
):
    """Check if squad has verified Final Code to enter Round 4."""
    from app.services.code_hunt_service import can_enter_round4
    is_eligible = can_enter_round4(db, team_id)
    msg = (
        "Team has verified their Final Code and is eligible for Round 4."
        if is_eligible
        else "Team has NOT verified their Final Code and cannot enter Round 4."
    )
    return ApiResponse(
        data={
            "team_id": team_id,
            "teamId": team_id,
            "is_eligible": is_eligible,
            "isEligible": is_eligible,
            "final_code_verified": is_eligible,
            "finalCodeVerified": is_eligible,
            "message": msg,
        },
        message=msg
    )
