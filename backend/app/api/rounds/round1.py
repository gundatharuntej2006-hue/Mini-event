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
    MiniRoundTimingResponse, GateCheckinInput, GateCheckinResponse,
    GateCheckinSummaryItem, StartRound1Response,
    ParticipantSessionRequest, ParticipantSessionResponse,
    ParticipantCurrentStateResponse, ParticipantScanRequest, ParticipantScanResponse,
    ParticipantSubmitAnswerRequest, ParticipantSubmitAnswerResponse,
    RouteAllocationMatrixResponse, LocationVolunteerItem, EnvelopePreparationItem
)
from app.services import round1_service, code_hunt_service
from app.scoring.round1_scoring import GATE_NAMES

router = APIRouter(prefix="/rounds/1", tags=["Round 1 — The ODDyssey Protocol"])

@router.post("/start", response_model=ApiResponse[StartRound1Response])
def start_round1(
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """
    Start Round 1: The ODDyssey Protocol (Organizers only).
    - Records official backend server timestamp.
    - Prevents starting Round 1 twice.
    """
    res = round1_service.start_round1(db, actor)
    return ApiResponse(data=res, message=res["message"])

@router.post("/reset", response_model=ApiResponse[Dict[str, Any]])
def reset_round1(
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """
    Reset Round 1 to initial unstarted state (Organizers only).
    - Removes all gate check-in scan records and attempts.
    - Cleans route progress while preserving assigned routes and 32 squad registrations.
    - Resets round status to Not Started and started_at to null.
    """
    res = round1_service.reset_round1_live_state(db, actor)
    return ApiResponse(data=res, message=res["message"])

@router.get("", response_model=ApiResponse[Round1OverviewResponse])
def get_round1(db: Session = Depends(get_db)):
    """Get complete Round 1 overview, live standings, and finalization status."""
    data = round1_service.get_round1_overview(db)
    return ApiResponse(data=data, message="Round 1 ODDyssey Protocol overview loaded")

@router.get("/config", response_model=ApiResponse[Round1ConfigSchema])
def get_config(db: Session = Depends(get_db)):
    """Get Round 1 configuration parameters."""
    cfg = round1_service.get_or_create_round1_config(db)
    res = Round1ConfigSchema(
        penalty_per_hint_seconds=cfg.penalty_per_hint_seconds,
        phone_penalty_seconds=600,
        separation_penalty_seconds=300,
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
        phone_penalty_seconds=600,
        separation_penalty_seconds=300,
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
    """Record or update checkpoint timing for a squad gate."""
    timing = round1_service.record_mini_round_timing(db, team_id, payload, actor)
    res = MiniRoundTimingResponse(
        mini_round_number=timing.mini_round_number,
        gate_name=GATE_NAMES.get(timing.mini_round_number, f"Gate {timing.mini_round_number}"),
        status=timing.status,
        start_time=timing.start_time.isoformat() if timing.start_time else None,
        completion_time=timing.completion_time.isoformat() if timing.completion_time else None,
        hints_used=timing.hints_used,
        hint_penalty_seconds=timing.hint_penalty_seconds,
        phone_penalties_count=getattr(timing, "phone_penalties_count", 0) or 0,
        phone_penalty_seconds=getattr(timing, "phone_penalty_seconds", 0) or 0,
        separation_penalties_count=getattr(timing, "separation_penalties_count", 0) or 0,
        separation_penalty_seconds=getattr(timing, "separation_penalty_seconds", 0) or 0,
        clue_tampering_deduction=getattr(timing, "clue_tampering_deduction", 0) or 0,
        is_disqualified=getattr(timing, "is_disqualified", False) or False,
        disqualification_reason=getattr(timing, "disqualification_reason", None),
        duration_seconds=timing.duration_seconds,
        adjusted_seconds=timing.adjusted_seconds,
        checkpoints=timing.checkpoints or []
    )
    return ApiResponse(data=res, message="Gate timing successfully recorded")

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
        gate_name=GATE_NAMES.get(timing.mini_round_number, f"Gate {timing.mini_round_number}"),
        status=timing.status,
        start_time=timing.start_time.isoformat() if timing.start_time else None,
        completion_time=timing.completion_time.isoformat() if timing.completion_time else None,
        hints_used=timing.hints_used,
        hint_penalty_seconds=timing.hint_penalty_seconds,
        phone_penalties_count=getattr(timing, "phone_penalties_count", 0) or 0,
        phone_penalty_seconds=getattr(timing, "phone_penalty_seconds", 0) or 0,
        separation_penalties_count=getattr(timing, "separation_penalties_count", 0) or 0,
        separation_penalty_seconds=getattr(timing, "separation_penalty_seconds", 0) or 0,
        clue_tampering_deduction=getattr(timing, "clue_tampering_deduction", 0) or 0,
        is_disqualified=getattr(timing, "is_disqualified", False) or False,
        disqualification_reason=getattr(timing, "disqualification_reason", None),
        duration_seconds=timing.duration_seconds,
        adjusted_seconds=timing.adjusted_seconds,
        checkpoints=timing.checkpoints or []
    )
    return ApiResponse(data=res, message="Hints updated")

@router.post("/teams/{team_id}/gates/{gate_number}/award-fragment", response_model=ApiResponse[Dict[str, Any]])
def award_gate_fragment(
    team_id: str,
    gate_number: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "marshal", "admin"]))
):
    """Awards the official Round 1 fragment: Gate 1 -> 'ODD', Gate 2 -> '42'."""
    if gate_number == 1:
        rec = code_hunt_service.record_fragment_1(db, team_id, fragment_value="ODD", actor=actor.email, overwrite=True)
        return ApiResponse(data={"team_id": team_id, "gate": 1, "fragment": "ODD", "status": rec.fragment_1_status.value}, message="Fragment 'ODD' awarded for Gate 1")
    elif gate_number == 2:
        rec = code_hunt_service.record_fragment_2(db, team_id, fragment_value="42", actor=actor.email, overwrite=True)
        return ApiResponse(data={"team_id": team_id, "gate": 2, "fragment": "42", "status": rec.fragment_2_status.value}, message="Fragment '42' awarded for Gate 2")
    else:
        raise HTTPException(status_code=400, detail="Gate number must be 1 (ODD) or 2 (42).")

@router.post("/teams/{team_id}/gate-3/confirm", response_model=ApiResponse[Dict[str, Any]])
def confirm_gate_3(
    team_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "marshal", "admin"]))
):
    """Confirms both fragments ('ODD' and '42') for Gate 3 qualification readiness."""
    try:
        rec = code_hunt_service.confirm_gate_3_fragments(db, team_id, actor=actor.email)
        return ApiResponse(data={"team_id": team_id, "gate_3_confirmed": rec.gate_3_confirmed}, message="Gate 3 confirmed: ODD and 42 validated.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/teams/public-list", response_model=ApiResponse[List[Dict[str, Any]]])
def get_public_teams(db: Session = Depends(get_db)):
    """Get registered squad list for public QR gate selection (no auth required)."""
    teams = round1_service.get_public_teams_list(db)
    return ApiResponse(data=teams, message=f"Loaded {len(teams)} registered squads")

@router.post("/gates/{gate_number}/checkin", response_model=ApiResponse[GateCheckinResponse])
def checkin_gate_checkpoint(
    gate_number: int,
    payload: GateCheckinInput,
    db: Session = Depends(get_db)
):
    """
    Public participant QR check-in endpoint for Gate 1, 2, or 3.
    - Validates squad existence in database.
    - Records server-side UTC timestamp (never client device clock).
    - Preserves official first timestamp if duplicate scans occur.
    - Updates official checkpoint completion time.
    - Unlocks official navigation payload.
    """
    res = round1_service.record_gate_checkin(
        db=db,
        gate_number=gate_number,
        team_name=payload.team_name,
        team_id=payload.team_id,
        team_identifier=payload.team_identifier
    )
    return ApiResponse(
        data=res,
        message="Gate checkpoint check-in verified. Navigation parameters revealed."
    )

@router.get("/checkins", response_model=ApiResponse[List[GateCheckinSummaryItem]])
def get_checkins_feed(
    gate: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Organizer feed of real-time physical QR gate check-in events."""
    checkins = round1_service.get_gate_checkins(db, gate_number=gate)
    return ApiResponse(data=checkins, message=f"Loaded {len(checkins)} check-in records")

@router.get("/gates/{gate_number}/public", response_model=ApiResponse[Dict[str, Any]])
def get_public_gate_checkpoint(gate_number: int):
    """Public digital checkpoint page data for Gate 1, 2, 3 (no auth required)."""
    if gate_number == 1:
        return ApiResponse(data={
            "gate": 1,
            "title": "Gate 1 — The Signal Scramble",
            "system_status": "CORRUPTED",
            "fragment_recovered": "ODD",
            "access_key": "42",
            "instructions": "Map data partially recovered — proceed to the marked region for Gate 2."
        })
    elif gate_number == 2:
        return ApiResponse(data={
            "gate": 2,
            "title": "Gate 2 — The Route Riddle",
            "system_status": "CORRUPTED",
            "fragment_confirmed": "42",
            "protocol_status": "ODD · 42",
            "instructions": "Proceed to the marked region for Gate 3."
        })
    elif gate_number == 3:
        return ApiResponse(data={
            "gate": 3,
            "title": "Gate 3 — The Logic Lockdown",
            "system_status": "PARTIALLY RESTORED",
            "protocol_status": "ODD — 42 (Both fragments recovered)",
            "instructions": "THE REAL ODDYSSEY BEGINS NOW. Proceed to Round 2."
        })
    else:
        raise HTTPException(status_code=404, detail="Invalid gate number. Choose 1, 2, or 3.")

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
    """Check Round 1 qualification readiness, top 16 cutoff, and tie flags."""
    overview = round1_service.get_round1_overview(db)
    return ApiResponse(data={
        "can_finalize": overview["can_finalize"],
        "issues": overview["issues"],
        "completed_count": overview["completed_count"],
        "incomplete_count": overview["incomplete_count"],
        "top16_cutoff_time": overview.get("top16_cutoff_time"),
        "top24_cutoff_time": overview.get("top24_cutoff_time")
    })

@router.post("/finalize", response_model=ApiResponse[FinalizationResponse])
def finalize_round1(
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Officially seal Round 1 results and advance 16 squads to Round 2."""
    res = round1_service.finalize_round1(db, actor, payload)
    return ApiResponse(data=res, message=res.get("message"))


# ==============================================================================
# Round 1 Final Spec Endpoints — Participant & Organizer Routes
# ==============================================================================

@router.post("/participant/session", response_model=ApiResponse[ParticipantSessionResponse])
def participant_create_session(
    payload: ParticipantSessionRequest,
    db: Session = Depends(get_db)
):
    """
    Public participant endpoint: authenticate device session via 4-digit Team ID.
    No username/password required.
    """
    res = round1_service.create_or_resume_participant_session(db, payload.team_identifier)
    return ApiResponse(data=res, message="Participant session established.")

@router.get("/participant/current", response_model=ApiResponse[ParticipantCurrentStateResponse])
def participant_get_current_state(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Public participant endpoint: retrieve ONLY current checkpoint location riddle and attempt status.
    Strictly omits future locations, answers, leaderboards, and other teams.
    """
    res = round1_service.get_participant_current_state(db, token)
    return ApiResponse(data=res)

@router.post("/participant/scan", response_model=ApiResponse[ParticipantScanResponse])
def participant_scan_location(
    token: str,
    payload: ParticipantScanRequest,
    db: Session = Depends(get_db)
):
    """
    Public participant QR scan endpoint (/round1/scan?location=X).
    Validates if scanned location matches team's assigned location for current checkpoint.
    """
    res = round1_service.record_participant_location_scan(db, token, payload.location)
    return ApiResponse(data=res, message=res["message"])

@router.post("/participant/submit", response_model=ApiResponse[ParticipantSubmitAnswerResponse])
def participant_submit_answer(
    token: str,
    payload: ParticipantSubmitAnswerRequest,
    db: Session = Depends(get_db)
):
    """
    Public participant answer submission endpoint (max 3 attempts per checkpoint).
    Advances to next checkpoint upon correct code/answer.
    """
    res = round1_service.submit_participant_checkpoint_answer(db, token, payload.answer)
    return ApiResponse(data=res, message=res["message"])

@router.get("/public/qualified", response_model=ApiResponse[Dict[str, Any]])
def get_public_qualified_teams(db: Session = Depends(get_db)):
    """
    Public participant post-finalization view: returns ONLY the 16 qualified Team IDs.
    Zero times, zero points, zero individual rankings.
    """
    res = round1_service.get_public_qualified_teams(db)
    return ApiResponse(data=res, message=res["message"])

@router.get("/allocations", response_model=ApiResponse[RouteAllocationMatrixResponse])
def get_allocations_matrix(
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin", "marshal"]))
):
    """Organizer view: complete 32-team schedule and constraint validation matrix."""
    res = round1_service.get_allocations_matrix(db)
    return ApiResponse(data=res, message="Round 1 allocation matrix loaded.")

@router.post("/allocations/generate", response_model=ApiResponse[RouteAllocationMatrixResponse])
def generate_allocations_matrix(
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Organizer action: compute & freeze valid 32-team allocation matrix."""
    round1_service.get_or_create_route_allocations(db, force_regenerate=True)
    res = round1_service.get_allocations_matrix(db)
    return ApiResponse(data=res, message="Round 1 allocation matrix generated and verified.")

@router.get("/volunteer/view", response_model=ApiResponse[LocationVolunteerItem])
def get_volunteer_location_view(
    checkpoint: int,
    location: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin", "marshal"]))
):
    """Station volunteer view: shows the 4 expected squads and their assigned envelope sets."""
    res = round1_service.get_location_volunteer_view(db, checkpoint_number=checkpoint, location_number=location)
    return ApiResponse(data=res, message="Location volunteer station roster loaded.")

@router.get("/envelope-sheet", response_model=ApiResponse[List[EnvelopePreparationItem]])
def get_envelope_prep_sheet(
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Organizer export: complete 96-assignment sheet for physical envelope preparation."""
    res = round1_service.get_envelope_preparation_sheet(db)
    return ApiResponse(data=res, message=f"Loaded {len(res)} envelope preparation assignments.")

@router.get("/teams/{team_identifier}/details", response_model=ApiResponse[Dict[str, Any]])
def get_team_audit_details(
    team_identifier: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(["organizer", "admin"]))
):
    """Organizer detailed inspection: view all attempts, timestamps, and invalid scans for a squad."""
    res = round1_service.get_team_audit_details(db, team_identifier)
    return ApiResponse(data=res, message="Team audit details loaded.")

