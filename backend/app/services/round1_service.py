import uuid
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.models.round1 import (
    Round1ConfigModel, MiniRoundTimingModel, GateCheckinModel,
    Round1RouteAllocationModel, Round1CheckpointAttemptModel, Round1ParticipantSessionModel
)
from app.models.round_models import Round1Record
from app.models.core import Team
from app.models.progression import TieReview, AuditLog
from app.models.code_hunt import FinalCodeRecord, FragmentStatus
from app.scoring.round1_scoring import process_round1_standings, compute_mini_round, GATE_NAMES
from app.services.audit_service import log_audit_event
from app.services.progression_service import record_round_finalization, get_eligible_team_ids, is_round_finalized
from app.services.tie_review_service import get_or_create_tie_review
from app.services import code_hunt_service
from app.schemas.rounds.round1 import MiniRoundTimingInput, UpdateHintsInput
from app.core.constants import (
    DEFAULT_R1_HINT_PENALTY_SECONDS,
    DEFAULT_R1_PHONE_PENALTY_SECONDS,
    DEFAULT_R1_SEPARATION_PENALTY_SECONDS,
    DEFAULT_R1_CHECKPOINTS,
    ROUND_1_NAME,
    ROUND_1_CODENAME,
    R1_QUALIFIERS,
    R1_LOCATIONS,
    R1_DEFAULT_TEAM_IDS,
    R1_QUESTION_SETS,
    R1_MAX_ATTEMPTS_PER_CHECKPOINT
)

def get_or_create_round1_config(db: Session) -> Round1ConfigModel:
    cfg = db.query(Round1ConfigModel).filter(Round1ConfigModel.id == 1).first()
    if not cfg:
        cfg = Round1ConfigModel(
            id=1,
            penalty_per_hint_seconds=DEFAULT_R1_HINT_PENALTY_SECONDS,
            checkpoint_names=list(DEFAULT_R1_CHECKPOINTS),
            is_finalized=False
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    elif not cfg.is_finalized:
        # If config is at old legacy placeholder defaults, upgrade to ODDyssey Protocol specification
        legacy_checkpoints = ["Checkpoint Alpha", "Checkpoint Bravo", "Checkpoint Charlie"]
        updated = False
        if cfg.checkpoint_names == legacy_checkpoints or not cfg.checkpoint_names:
            cfg.checkpoint_names = list(DEFAULT_R1_CHECKPOINTS)
            updated = True
        if cfg.penalty_per_hint_seconds == 120:
            cfg.penalty_per_hint_seconds = DEFAULT_R1_HINT_PENALTY_SECONDS
            updated = True
        if updated:
            db.commit()
            db.refresh(cfg)
    return cfg

def start_round1(db: Session, actor) -> Dict[str, Any]:
    """
    Start Round 1: The ODDyssey Protocol once and record official server timestamp.
    - Disables starting Round 1 twice.
    - Updates Round1ConfigModel.started_at and started_by.
    - Updates RoundState (Round 1) started_at and status.
    - Logs audit event.
    """
    cfg = get_or_create_round1_config(db)
    if cfg.is_finalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Round 1 is finalized and cannot be started."
        )
    if cfg.started_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Round 1 has already been started at {cfg.started_at.isoformat()}."
        )

    now_utc = datetime.now(timezone.utc)
    actor_id = getattr(actor, "id", None) or getattr(actor, "email", "system")
    actor_role = getattr(actor, "role", "ORGANIZER")
    if hasattr(actor_role, "value"):
        actor_role = actor_role.value

    cfg.started_at = now_utc
    cfg.started_by = str(actor_id)

    # Sync with RoundState
    from app.services.round_service import ensure_round_states_initialized
    ensure_round_states_initialized(db)
    from app.models.round_models import RoundState
    rs = db.query(RoundState).filter(RoundState.id == 1).first()
    if rs:
        rs.started_at = now_utc
        rs.status = "In Progress"

    log_audit_event(
        db=db,
        action="ROUND_STARTED",
        entity_type="Round1Config",
        entity_id="1",
        actor_id=str(actor_id),
        actor_role=str(actor_role),
        round_number=1,
        details={"started_at": now_utc.isoformat(), "started_by": str(actor_id)}
    )

    db.commit()
    db.refresh(cfg)

    return {
        "is_started": True,
        "started_at": now_utc.isoformat(),
        "started_by": str(actor_id),
        "round_number": 1,
        "message": "Round 1: The ODDyssey Protocol has officially started."
    }

def update_round1_config(db: Session, penalty_seconds: Optional[int], checkpoint_names: Optional[List[str]], actor) -> Round1ConfigModel:
    cfg = get_or_create_round1_config(db)
    if cfg.is_finalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Round 1 is finalized and cannot be reconfigured."
        )

    if penalty_seconds is not None:
        cfg.penalty_per_hint_seconds = penalty_seconds
    if checkpoint_names is not None:
        cfg.checkpoint_names = checkpoint_names

    log_audit_event(
        db=db,
        action="ROUND1_CONFIG_UPDATED",
        entity_type="Round1Config",
        entity_id="1",
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=1,
        details={"penalty_per_hint_seconds": cfg.penalty_per_hint_seconds, "checkpoint_names": cfg.checkpoint_names}
    )
    db.commit()
    db.refresh(cfg)
    return cfg

def record_mini_round_timing(db: Session, team_id: str, input_data: MiniRoundTimingInput, actor) -> MiniRoundTimingModel:
    cfg = get_or_create_round1_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Round 1 is finalized. No timing edits permitted.")

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team '{team_id}' not found.")

    timing_id = f"r1-{team_id}-{input_data.mini_round_number}"
    timing = db.query(MiniRoundTimingModel).filter(MiniRoundTimingModel.id == timing_id).first()
    if not timing:
        timing = MiniRoundTimingModel(
            id=timing_id,
            team_id=team_id,
            mini_round_number=input_data.mini_round_number
        )
        db.add(timing)

    # Process timing logic
    mr_dict = {
        "mini_round_number": input_data.mini_round_number,
        "start_time": input_data.start_time,
        "completion_time": input_data.completion_time,
        "hints_used": input_data.hints_used,
        "phone_penalties_count": input_data.phone_penalties_count,
        "separation_penalties_count": input_data.separation_penalties_count,
        "clue_tampering_deduction": input_data.clue_tampering_deduction,
        "is_disqualified": input_data.is_disqualified,
        "disqualification_reason": input_data.disqualification_reason,
        "checkpoints": [c.model_dump() for c in (input_data.checkpoints or [])]
    }
    processed = compute_mini_round(
        mr_dict,
        penalty_per_hint_seconds=cfg.penalty_per_hint_seconds,
        phone_penalty_seconds=DEFAULT_R1_PHONE_PENALTY_SECONDS,
        separation_penalty_seconds=DEFAULT_R1_SEPARATION_PENALTY_SECONDS
    )

    start_dt = datetime.fromisoformat(input_data.start_time.replace("Z", "+00:00")) if input_data.start_time else None
    comp_dt = datetime.fromisoformat(input_data.completion_time.replace("Z", "+00:00")) if input_data.completion_time else None

    timing.start_time = start_dt
    timing.completion_time = comp_dt
    timing.hints_used = processed["hints_used"]
    timing.hint_penalty_seconds = processed["hint_penalty_seconds"]
    timing.phone_penalties_count = processed["phone_penalties_count"]
    timing.phone_penalty_seconds = processed["phone_penalty_seconds"]
    timing.separation_penalties_count = processed["separation_penalties_count"]
    timing.separation_penalty_seconds = processed["separation_penalty_seconds"]
    timing.clue_tampering_deduction = processed["clue_tampering_deduction"]
    timing.is_disqualified = processed["is_disqualified"]
    timing.disqualification_reason = processed["disqualification_reason"]
    timing.duration_seconds = processed["duration_seconds"]
    timing.adjusted_seconds = processed["adjusted_seconds"]
    timing.status = processed["status"]
    timing.checkpoints = processed["checkpoints"]

    log_audit_event(
        db=db,
        action="TIMING_RECORDED",
        entity_type="MiniRoundTiming",
        entity_id=timing_id,
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=1,
        details={
            "gate": input_data.mini_round_number,
            "duration": timing.duration_seconds,
            "adjusted": timing.adjusted_seconds,
            "is_disqualified": timing.is_disqualified
        }
    )
    db.commit()
    db.refresh(timing)
    return timing

def update_hints(db: Session, team_id: str, mini_round_number: int, hints_used: int, actor) -> MiniRoundTimingModel:
    cfg = get_or_create_round1_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Round 1 is finalized.")

    timing_id = f"r1-{team_id}-{mini_round_number}"
    timing = db.query(MiniRoundTimingModel).filter(MiniRoundTimingModel.id == timing_id).first()
    if not timing:
        timing = MiniRoundTimingModel(id=timing_id, team_id=team_id, mini_round_number=mini_round_number)
        db.add(timing)

    timing.hints_used = max(0, hints_used)
    timing.hint_penalty_seconds = timing.hints_used * cfg.penalty_per_hint_seconds
    total_time_penalties = (
        timing.hint_penalty_seconds +
        (timing.phone_penalty_seconds or 0) +
        (timing.separation_penalty_seconds or 0)
    )
    if timing.duration_seconds is not None:
        timing.adjusted_seconds = timing.duration_seconds + total_time_penalties

    log_audit_event(
        db=db,
        action="HINTS_UPDATED",
        entity_type="MiniRoundTiming",
        entity_id=timing_id,
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=1,
        details={"hints_used": hints_used, "penalty": timing.hint_penalty_seconds}
    )
    db.commit()
    db.refresh(timing)
    return timing

def get_round1_overview(db: Session) -> Dict[str, Any]:
    cfg = get_or_create_round1_config(db)
    teams = db.query(Team).order_by(Team.team_number.asc()).all()

    timings = db.query(MiniRoundTimingModel).all()
    timings_by_team = {}
    for t in timings:
        timings_by_team.setdefault(t.team_id, {})[t.mini_round_number] = t

    code_records = db.query(FinalCodeRecord).all()
    code_by_team = {cr.team_id: cr for cr in code_records}

    raw_records = []
    for team in teams:
        team_timings = timings_by_team.get(team.id, {})
        code_rec = code_by_team.get(team.id)

        mini_rounds = []
        for mr_num in [1, 2, 3]:
            t = team_timings.get(mr_num)
            gate_label = GATE_NAMES.get(mr_num, f"Gate {mr_num}")
            if t:
                mini_rounds.append({
                    "mini_round_number": mr_num,
                    "gate_name": gate_label,
                    "status": t.status,
                    "start_time": t.start_time.isoformat() if t.start_time else None,
                    "completion_time": t.completion_time.isoformat() if t.completion_time else None,
                    "hints_used": t.hints_used,
                    "hint_penalty_seconds": t.hint_penalty_seconds,
                    "phone_penalties_count": getattr(t, "phone_penalties_count", 0) or 0,
                    "phone_penalty_seconds": getattr(t, "phone_penalty_seconds", 0) or 0,
                    "separation_penalties_count": getattr(t, "separation_penalties_count", 0) or 0,
                    "separation_penalty_seconds": getattr(t, "separation_penalty_seconds", 0) or 0,
                    "clue_tampering_deduction": getattr(t, "clue_tampering_deduction", 0) or 0,
                    "is_disqualified": getattr(t, "is_disqualified", False) or False,
                    "disqualification_reason": getattr(t, "disqualification_reason", None),
                    "duration_seconds": t.duration_seconds,
                    "adjusted_seconds": t.adjusted_seconds,
                    "checkpoints": t.checkpoints or []
                })
            else:
                mini_rounds.append({
                    "mini_round_number": mr_num,
                    "gate_name": gate_label,
                    "status": "Not Started",
                    "start_time": None,
                    "completion_time": None,
                    "hints_used": 0,
                    "hint_penalty_seconds": 0,
                    "phone_penalties_count": 0,
                    "phone_penalty_seconds": 0,
                    "separation_penalties_count": 0,
                    "separation_penalty_seconds": 0,
                    "clue_tampering_deduction": 0,
                    "is_disqualified": False,
                    "disqualification_reason": None,
                    "duration_seconds": None,
                    "adjusted_seconds": None,
                    "checkpoints": []
                })

        raw_records.append({
            "team_id": team.id,
            "team_number": team.team_number,
            "team_name": team.name,
            "mini_rounds": mini_rounds,
            "gate_1_fragment_status": code_rec.fragment_1_status.value if code_rec else "PENDING",
            "gate_2_fragment_status": code_rec.fragment_2_status.value if code_rec else "PENDING",
            "gate_3_confirmed": getattr(code_rec, "gate_3_confirmed", False) if code_rec else False
        })

    standings = process_round1_standings(
        raw_records,
        penalty_per_hint_seconds=cfg.penalty_per_hint_seconds,
        is_finalized=cfg.is_finalized,
        phone_penalty_seconds=DEFAULT_R1_PHONE_PENALTY_SECONDS,
        separation_penalty_seconds=DEFAULT_R1_SEPARATION_PENALTY_SECONDS
    )

    # If tie affects 16th cutoff boundary, register/retrieve tie review record
    if standings.get("cutoff_boundary_tie"):
        tied_teams = [
            r for r in standings["records"]
            if r["team_id"] in standings["tied_teams_at_cutoff"]
        ]
        get_or_create_tie_review(
            db=db,
            round_number=1,
            teams_involved=tied_teams,
            ranking_metric="adjusted_total_seconds",
            cutoff_position=16,
            notes="Fastest gate tie breaker was identical. Cutoff straddles 16th and 17th place."
        )

    # Check if a tie review has been resolved
    tie_rev = db.query(TieReview).filter(TieReview.id.in_(["tie-r1-cutoff16", "tie-r1-cutoff24"])).first()
    if tie_rev and tie_rev.review_status == "RESOLVED" and standings.get("cutoff_boundary_tie"):
        standings["can_finalize"] = len([i for i in standings["issues"] if i["code"] != "CUTOFF_TIE"]) == 0
        standings["issues"] = [i for i in standings["issues"] if i["code"] != "CUTOFF_TIE"]

    from app.services.round_service import ensure_round_states_initialized
    ensure_round_states_initialized(db)
    from app.models.round_models import RoundState
    rs = db.query(RoundState).filter(RoundState.id == 1).first()
    config_json = rs.config_json if rs else {}

    # Enhance each record with gate_1_seconds, gate_2_seconds, gate_3_seconds
    for rec in standings["records"]:
        mrs = {mr["mini_round_number"]: mr for mr in rec.get("mini_rounds", [])}
        rec["gate_1_seconds"] = mrs.get(1, {}).get("duration_seconds")
        rec["gate_2_seconds"] = mrs.get(2, {}).get("duration_seconds")
        rec["gate_3_seconds"] = mrs.get(3, {}).get("duration_seconds")

    return {
        "id": 1,
        "name": ROUND_1_NAME,
        "codename": ROUND_1_CODENAME,
        "status": "Completed" if (cfg.is_finalized or (rs.is_finalized if rs else False)) else ("In Progress" if cfg.started_at else "Not Started"),
        "isFinalized": cfg.is_finalized or (rs.is_finalized if rs else False),
        "started_at": cfg.started_at.isoformat() if cfg.started_at else None,
        "is_started": bool(cfg.started_at),
        "config_json": config_json,
        "configJson": config_json,
        "config": {
            "penalty_per_hint_seconds": cfg.penalty_per_hint_seconds,
            "phone_penalty_seconds": DEFAULT_R1_PHONE_PENALTY_SECONDS,
            "separation_penalty_seconds": DEFAULT_R1_SEPARATION_PENALTY_SECONDS,
            "checkpoint_names": cfg.checkpoint_names or [],
            "is_finalized": cfg.is_finalized,
            "finalized_at": cfg.finalized_at.isoformat() if cfg.finalized_at else None,
            "finalized_by": cfg.finalized_by,
            "started_at": cfg.started_at.isoformat() if cfg.started_at else None,
            "started_by": cfg.started_by,
            "is_started": bool(cfg.started_at)
        },
        "records": standings["records"],
        "can_finalize": standings["can_finalize"],
        "issues": standings["issues"],
        "completed_count": standings["completed_count"],
        "incomplete_count": standings["incomplete_count"],
        "disqualified_count": standings.get("disqualified_count", 0),
        "top16_cutoff_time": standings["top16_cutoff_time"],
        "top24_cutoff_time": standings["top24_cutoff_time"]
    }

def finalize_round1(db: Session, actor, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = get_or_create_round1_config(db)
    if cfg.is_finalized:
        eligible = get_eligible_team_ids(db, 2)
        return {
            "can_finalize": True,
            "issues": [],
            "finalized": True,
            "advancing_team_ids": eligible,
            "message": "Round 1 is already finalized.",
            "success": True,
            "round_number": 1,
            "roundNumber": 1,
            "qualified_team_ids": eligible,
            "qualifiedTeamIds": eligible,
            "total_eligible": len(eligible) if eligible else R1_QUALIFIERS,
            "totalEligible": len(eligible) if eligible else R1_QUALIFIERS,
        }

    overview = get_round1_overview(db)
    override = bool(payload and (payload.get("overrideDiscrepancy") or payload.get("override_discrepancy")))
    if not overview["can_finalize"] and not override:
        return {
            "can_finalize": False,
            "issues": overview["issues"],
            "finalized": False,
            "message": "Finalization blocked by server-side safeguards.",
            "success": False,
            "round_number": 1,
            "roundNumber": 1,
            "qualified_team_ids": [],
            "qualifiedTeamIds": [],
            "total_eligible": 0,
            "totalEligible": 0,
        }

    records = overview["records"]
    # Top 16 advance (must not be disqualified)
    advancing_team_ids = [
        r["team_id"] for r in records
        if r.get("rank") and r["rank"] <= R1_QUALIFIERS and not r.get("is_disqualified")
    ]

    # Handle tie review if resolved
    tie_rev = db.query(TieReview).filter(TieReview.id.in_(["tie-r1-cutoff16", "tie-r1-cutoff24"])).first()
    if tie_rev and tie_rev.review_status == "RESOLVED" and tie_rev.advancing_team_ids:
        resolved_adv = set(tie_rev.advancing_team_ids)
        advancing_team_ids = [
            r["team_id"] for r in records
            if (r.get("rank") and r["rank"] < R1_QUALIFIERS and not r.get("is_disqualified")) or (r["team_id"] in resolved_adv)
        ]

    if not advancing_team_ids and override:
        all_teams = db.query(Team).order_by(Team.team_number.asc()).limit(R1_QUALIFIERS).all()
        advancing_team_ids = [t.id for t in all_teams]

    record_round_finalization(
        db=db,
        round_number=1,
        records=records,
        advancing_team_ids=advancing_team_ids,
        finalized_by=actor.id
    )

    cfg.is_finalized = True
    cfg.finalized_at = datetime.now(timezone.utc)
    cfg.finalized_by = actor.id

    from app.services.round_service import ensure_round_states_initialized
    ensure_round_states_initialized(db)
    from app.models.round_models import RoundState
    rs = db.query(RoundState).filter(RoundState.id == 1).first()
    if rs:
        rs.is_finalized = True
        rs.finalized_at = cfg.finalized_at
        rs.finalized_by = actor.id
        rs.status = "Completed"
        cfg_dict = dict(rs.config_json or {})
        cfg_dict["finalizationAudit"] = {
            "finalizedBy": actor.id,
            "finalizedAt": cfg.finalized_at.isoformat(),
            "overrideDiscrepancy": override,
            "discrepancyOverridden": override,
            "notes": payload.get("notes") if payload else None
        }
        rs.config_json = cfg_dict

    log_audit_event(
        db=db,
        action="ROUND_FINALIZED",
        entity_type="Round1Config",
        entity_id="1",
        actor_id=actor.id,
        actor_role=actor.role,
        round_number=1,
        details={"advancing_team_ids": advancing_team_ids, "advancing_count": len(advancing_team_ids)}
    )
    db.commit()

    return {
        "can_finalize": True,
        "issues": [],
        "finalized": True,
        "advancing_team_ids": advancing_team_ids,
        "message": f"Round 1 successfully finalized. {len(advancing_team_ids)} squads advance to Round 2: Cabo.",
        "success": True,
        "round_number": 1,
        "roundNumber": 1,
        "qualified_team_ids": advancing_team_ids,
        "qualifiedTeamIds": advancing_team_ids,
        "total_eligible": len(advancing_team_ids),
        "totalEligible": len(advancing_team_ids),
    }

def get_public_teams_list(db: Session) -> List[Dict[str, Any]]:
    """Get active registered teams list for public QR gate selection."""
    teams = db.query(Team).order_by(Team.team_number.asc()).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "team_number": t.team_number
        }
        for t in teams
    ]

def record_gate_checkin(
    db: Session,
    gate_number: int,
    team_name: Optional[str] = None,
    team_id: Optional[str] = None,
    team_identifier: Optional[str] = None
) -> Dict[str, Any]:
    """
    Record an official QR checkpoint scan for Round 1: The ODDyssey Protocol.
    - Requires Round 1 to be started by organizer.
    - Validates team exists in registered roster (by team_identifier, team_id, or team_name).
    - Enforces gate sequence (Gate 2 requires Gate 1; Gate 3 requires Gate 2).
    - Generates authoritative server-side UTC timestamp (never trusts client clock).
    - Preserves initial scan timestamp if repeat scans occur (handles duplicates safely).
    - Calculates splits: Gate 1 = T1 - T_start; Gate 2 = T2 - T1; Gate 3 = T3 - T2. Total = T3 - T_start.
    - Updates official MiniRoundTiming record with server completion time.
    - Automatically awards fragment (ODD for Gate 1, 42 for Gate 2, confirmation for Gate 3).
    - Returns navigation payload with split info only after check-in record is successfully committed.
    """
    if gate_number not in (1, 2, 3):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid gate number {gate_number}. The ODDyssey Protocol uses Gates 1, 2, and 3."
        )

    # 1. Verify Round 1 has been started
    cfg = get_or_create_round1_config(db)
    if not cfg.started_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Round 1 has not been started by the organizers yet. Please wait for the official start signal."
        )
    round_start_utc = cfg.started_at.replace(tzinfo=timezone.utc) if cfg.started_at.tzinfo is None else cfg.started_at

    # 2. Validate team existence
    team: Optional[Team] = None
    # 2a. Match by 4-digit code or numeric team_identifier (e.g. "1024", "0001", "1")
    identifier_query = (team_identifier or "").strip()
    if identifier_query:
        # Check if matches team.id directly
        team = db.query(Team).filter(Team.id == identifier_query).first()
        if not team:
            # Try integer parsing for team_number (e.g. "0001" -> 1, "1024" -> 1024)
            try:
                num_val = int(identifier_query)
                team = db.query(Team).filter(Team.team_number == num_val).first()
            except ValueError:
                pass
        if not team:
            # Case-insensitive match on name
            team = db.query(Team).filter(func.lower(Team.name) == identifier_query.lower()).first()

    if not team and team_id:
        team = db.query(Team).filter(Team.id == team_id).first()

    if not team and team_name:
        clean_name = team_name.strip()
        # Also check if user typed number into team_name field
        try:
            num_val = int(clean_name)
            team = db.query(Team).filter(Team.team_number == num_val).first()
        except ValueError:
            pass

        if not team:
            team = db.query(Team).filter(func.lower(Team.name) == clean_name.lower()).first()
            if not team:
                # Try case-insensitive substring match
                team = db.query(Team).filter(Team.name.ilike(f"%{clean_name}%")).first()

    if not team:
        searched_term = identifier_query or team_id or team_name or "Unknown"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team '{searched_term}' was not found in the tournament roster. Please ensure your squad is registered in EVENT HQ."
        )

    # 3. Server-side authoritative timestamp
    now_utc = datetime.now(timezone.utc)
    if now_utc < round_start_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scan timestamp cannot precede Round 1 start time."
        )

    # 4. Enforce strict gate sequence for first-time scans
    # Gate 2 requires Gate 1 completed; Gate 3 requires Gate 2 completed
    timing1 = db.query(MiniRoundTimingModel).filter(
        MiniRoundTimingModel.team_id == team.id,
        MiniRoundTimingModel.mini_round_number == 1
    ).first()
    timing2 = db.query(MiniRoundTimingModel).filter(
        MiniRoundTimingModel.team_id == team.id,
        MiniRoundTimingModel.mini_round_number == 2
    ).first()

    if gate_number == 2:
        if not timing1 or not timing1.completion_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid gate sequence: Gate 1 must be scanned before Gate 2."
            )
    elif gate_number == 3:
        if not timing2 or not timing2.completion_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid gate sequence: Gate 2 must be scanned before Gate 3."
            )

    # 5. Check for previous check-ins at this gate
    existing_checkins = db.query(GateCheckinModel).filter(
        GateCheckinModel.team_id == team.id,
        GateCheckinModel.round_number == 1,
        GateCheckinModel.gate_number == gate_number
    ).order_by(GateCheckinModel.scanned_at.asc()).all()

    timing_id = f"r1-{team.id}-{gate_number}"
    timing = db.query(MiniRoundTimingModel).filter(MiniRoundTimingModel.id == timing_id).first()

    split_seconds = None
    if existing_checkins:
        is_duplicate = True
        attempt_number = len(existing_checkins) + 1
        first_checkin = existing_checkins[0]
        official_scanned_at = first_checkin.scanned_at
        checkin_status = "DUPLICATE"
        notes = f"Repeat scan #{attempt_number}. Official first timestamp preserved: {first_checkin.scanned_at.strftime('%H:%M:%S UTC')}"
        if timing and timing.duration_seconds is not None:
            split_seconds = timing.duration_seconds
    else:
        is_duplicate = False
        attempt_number = 1
        official_scanned_at = now_utc
        checkin_status = "VERIFIED"
        notes = f"Official Gate {gate_number} checkpoint scan recorded."

        # Determine start_time for this gate
        if gate_number == 1:
            gate_start_dt = round_start_utc
        elif gate_number == 2:
            t1_end = timing1.completion_time
            gate_start_dt = t1_end.replace(tzinfo=timezone.utc) if t1_end.tzinfo is None else t1_end
        else:  # gate_number == 3
            t2_end = timing2.completion_time
            gate_start_dt = t2_end.replace(tzinfo=timezone.utc) if t2_end.tzinfo is None else t2_end

        t_diff = int((now_utc - gate_start_dt).total_seconds())
        if t_diff < 0:
            t_diff = 0
        split_seconds = t_diff

        # Update official checkpoint timing in round1_timings for this team & gate
        if not timing:
            timing = MiniRoundTimingModel(
                id=timing_id,
                team_id=team.id,
                mini_round_number=gate_number,
                start_time=gate_start_dt,
                completion_time=now_utc,
                hints_used=0,
                hint_penalty_seconds=0,
                phone_penalties_count=0,
                phone_penalty_seconds=0,
                separation_penalties_count=0,
                separation_penalty_seconds=0,
                clue_tampering_deduction=0,
                duration_seconds=t_diff,
                adjusted_seconds=t_diff,
                status="Completed"
            )
            db.add(timing)
        else:
            timing.status = "Completed"
            timing.start_time = gate_start_dt
            timing.completion_time = now_utc
            timing.duration_seconds = t_diff
            h_used = timing.hints_used or 0
            p_used = timing.phone_penalties_count or 0
            s_used = timing.separation_penalties_count or 0
            timing.adjusted_seconds = t_diff + (h_used * 300) + (p_used * 600) + (s_used * 300)

        # Automatically record fragments per ODDyssey protocol spec
        if gate_number == 1:
            try:
                code_hunt_service.record_fragment_1(db, team.id, fragment_value="ODD", actor="SYSTEM_QR_GATE_1", overwrite=True)
            except Exception:
                pass
        elif gate_number == 2:
            try:
                code_hunt_service.record_fragment_2(db, team.id, fragment_value="42", actor="SYSTEM_QR_GATE_2", overwrite=True)
            except Exception:
                pass
        elif gate_number == 3:
            try:
                code_hunt_service.confirm_gate_3_fragments(db, team.id, actor="SYSTEM_QR_GATE_3")
            except Exception:
                pass

    # 6. Save new check-in record
    checkin_id = f"chk-{uuid.uuid4().hex[:10]}"
    checkin = GateCheckinModel(
        id=checkin_id,
        team_id=team.id,
        team_name=team.name,
        round_number=1,
        gate_number=gate_number,
        scanned_at=now_utc,
        is_duplicate=is_duplicate,
        attempt_number=attempt_number,
        status=checkin_status,
        notes=notes,
        created_at=now_utc
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)

    # 5. Build official navigation payload
    if gate_number == 1:
        navigation = {
            "raw_text": "ODDYSSEY NAVIGATION SYSTEM | SYSTEM STATUS: CORRUPTED | FRAGMENT 01 RECOVERED: ODD | ACCESS KEY: 42 | MAP DATA PARTIALLY RECOVERED - proceed to the marked region of the campus map to find Gate 2.",
            "system_status": "CORRUPTED",
            "fragment_info": "FRAGMENT 01 RECOVERED: ODD",
            "access_key": "42",
            "protocol_status": "ODD",
            "instructions": "MAP DATA PARTIALLY RECOVERED - proceed to the marked region of the campus map to find Gate 2.",
            "fallback_instructions": "If mobile network fails or battery is low, request an Official Yellow Gate 1 Marshal Physical Slip with ink stamp."
        }
    elif gate_number == 2:
        navigation = {
            "raw_text": "ODDYSSEY NAVIGATION SYSTEM | SYSTEM STATUS: CORRUPTED | FRAGMENT 02 RECOVERED: 42 | PROTOCOL STATUS: ODD · 42 | MAP DATA PARTIALLY RECOVERED - proceed to the marked region of the campus map to find Gate 3.",
            "system_status": "CORRUPTED",
            "fragment_info": "FRAGMENT 02 RECOVERED: 42",
            "access_key": None,
            "protocol_status": "ODD · 42",
            "instructions": "Proceed to the marked region of the campus map to find Gate 3.",
            "fallback_instructions": "Physical campus grid cards and backup route maps are available with roving marshals wearing hi-vis bands."
        }
    else:  # gate 3
        navigation = {
            "raw_text": "ODDYSSEY NAVIGATION SYSTEM | SYSTEM STATUS: PARTIALLY RESTORED | FRAGMENTS VALIDATED: ODD — 42 (Both fragments recovered) | THE REAL ODDYSSEY BEGINS NOW. Proceed to Round 2.",
            "system_status": "PARTIALLY RESTORED",
            "fragment_info": "ODD — 42 (Both fragments recovered)",
            "access_key": None,
            "protocol_status": "ODD — 42 COMPLETE",
            "instructions": "THE REAL ODDYSSEY BEGINS NOW. Proceed to Round 2.",
            "fallback_instructions": "In case of digital sync delays, obtain an Official Gate 3 Progression Pass signed by the Chief Marshal."
        }

    def _to_iso(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    def _fmt_seconds(sec):
        if sec is None:
            return None
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    return {
        "checkin_id": checkin.id,
        "team_id": team.id,
        "team_name": team.name,
        "team_number": team.team_number,
        "round_number": 1,
        "gate_number": gate_number,
        "scanned_at": _to_iso(checkin.scanned_at),
        "official_scanned_at": _to_iso(official_scanned_at),
        "is_duplicate": is_duplicate,
        "attempt_number": attempt_number,
        "status": checkin.status,
        "notes": checkin.notes,
        "split_seconds": split_seconds,
        "split_time_formatted": _fmt_seconds(split_seconds),
        "navigation": navigation
    }

def get_gate_checkins(db: Session, gate_number: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieve all recorded QR gate check-ins for Round 1 (sorted latest first).
    Only includes scans from the current active round session (scanned_at >= started_at).
    If Round 1 has not started, returns an empty list so old test scans never leak into live feed.
    """
    cfg = get_or_create_round1_config(db)
    if not cfg.started_at:
        return []

    started_at_utc = cfg.started_at.replace(tzinfo=timezone.utc) if cfg.started_at.tzinfo is None else cfg.started_at

    def _to_iso(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    query = db.query(GateCheckinModel).filter(
        GateCheckinModel.round_number == 1,
        GateCheckinModel.scanned_at >= started_at_utc
    )
    if gate_number is not None:
        query = query.filter(GateCheckinModel.gate_number == gate_number)
    checkins = query.order_by(GateCheckinModel.scanned_at.desc()).all()
    return [
        {
            "id": c.id,
            "team_id": c.team_id,
            "team_name": c.team_name,
            "round_number": c.round_number,
            "gate_number": c.gate_number,
            "scanned_at": _to_iso(c.scanned_at),
            "is_duplicate": c.is_duplicate,
            "attempt_number": c.attempt_number,
            "status": c.status,
            "notes": c.notes,
            "created_at": _to_iso(c.created_at)
        }
        for c in checkins
    ]

# ==============================================================================
# Round 1 Final Spec — Question Answers, Route Allocation & Participant Sessions
# ==============================================================================

# 4 Question Sets (A, B, C, D) Master Answer Keys
# Note: Set A -> Gate 2 -> Q3 inconsistency flagged for organizer in validation payload.
R1_QUESTION_KEY: Dict[str, Dict[str, str]] = {
    # Expected final codes/answers for Set A, B, C, D
    # Case-insensitive whitespace-normalized match
    "A": {
        "1": "ODD",
        "2": "42",
        "3": "ENIGMA"
    },
    "B": {
        "1": "ECHO",
        "2": "PRIME",
        "3": "NEXUS"
    },
    "C": {
        "1": "CIPHER",
        "2": "VECTOR",
        "3": "APEX"
    },
    "D": {
        "1": "MATRIX",
        "2": "QUANTUM",
        "3": "ZENITH"
    }
}

ORGANIZER_NOTES_SET_A_GATE2_Q3 = (
    "NOTICE: Inconsistency identified in source document for Set A -> Gate 2 -> Q3. "
    "Accepted authoritative answer is configured as '42' or 'ENIGMA' for automatic verification."
)

def compute_deterministic_allocations() -> List[Dict[str, Any]]:
    """
    Computes a mathematically sound 32-team schedule satisfying all constraints:
    - 32 teams (indices 0..31 -> IDs 1001..1032)
    - 8 locations (1..8)
    - Checkpoint 1 (R1.1): exactly 4 teams per location
    - Checkpoint 2 (R1.2): exactly 4 teams per location
    - Checkpoint 3 (R1.3): exactly 4 teams per location
    - Every team gets 3 distinct locations
    - At every location and checkpoint, the 4 teams receive exactly one of A, B, C, D
    - Every team receives 3 unique sets across R1.1, R1.2, R1.3
    """
    c1 = [(i // 4) for i in range(32)]
    c2 = [((i // 4) + 1 + (i % 4)) % 8 for i in range(32)]
    c3 = [((i // 4) + 2 + (i % 4)) % 8 for i in range(32)]

    # Verified zero-conflict set arrays satisfying all constraints
    # (exact one A, B, C, D per location per checkpoint, and 3 distinct sets per team)
    cp1_sets = ['A', 'B', 'C', 'D', 'A', 'B', 'C', 'D', 'A', 'B', 'C', 'D', 'A', 'B', 'C', 'D', 'A', 'B', 'C', 'D', 'A', 'B', 'C', 'D', 'A', 'B', 'C', 'D', 'A', 'B', 'C', 'D']
    cp2_sets = ['D', 'A', 'A', 'C', 'B', 'D', 'D', 'B', 'C', 'A', 'A', 'A', 'B', 'C', 'B', 'B', 'D', 'C', 'D', 'A', 'D', 'A', 'B', 'C', 'C', 'D', 'B', 'C', 'C', 'A', 'D', 'B']
    cp3_sets = ['C', 'D', 'B', 'A', 'C', 'A', 'B', 'A', 'D', 'C', 'B', 'B', 'D', 'D', 'D', 'A', 'C', 'A', 'B', 'C', 'C', 'C', 'D', 'B', 'D', 'A', 'A', 'A', 'B', 'D', 'B', 'C']

    results = []
    for i in range(32):
        team_num_str = str(1001 + i)
        results.append({
            "team_identifier": team_num_str,
            "team_number": 1001 + i,
            "cp1_location": c1[i] + 1,  # 1-indexed (1..8)
            "cp1_set": cp1_sets[i],
            "cp2_location": c2[i] + 1,  # 1-indexed (1..8)
            "cp2_set": cp2_sets[i],
            "cp3_location": c3[i] + 1,  # 1-indexed (1..8)
            "cp3_set": cp3_sets[i],
        })
    return results

def validate_route_allocations(allocations: List[Any]) -> Dict[str, Any]:
    """
    Validates the 8 core constraints required for Round 1:
    1. Exactly 32 teams
    2. Exactly 8 locations
    3. Exactly 4 teams per location in R1.1
    4. Exactly 4 teams per location in R1.2
    5. Exactly 4 teams per location in R1.3
    6. 3 unique locations per team
    7. Exactly one A/B/C/D per location per checkpoint
    8. No missing or duplicate teams
    """
    errors = []
    if len(allocations) != 32:
        errors.append(f"Expected 32 teams, found {len(allocations)}.")

    def _get(a, key):
        if hasattr(a, key):
            return getattr(a, key)
        return a[key]

    team_ids = [_get(a, "team_identifier") for a in allocations]
    if len(set(team_ids)) != len(team_ids):
        errors.append("Duplicate team identifiers found in allocation.")

    # Location distribution counts
    for cp_num in [1, 2, 3]:
        loc_key = f"cp{cp_num}_location"
        set_key = f"cp{cp_num}_set"
        loc_counts = {loc: 0 for loc in range(1, 9)}
        loc_sets = {loc: [] for loc in range(1, 9)}

        for a in allocations:
            loc = _get(a, loc_key)
            s = _get(a, set_key)
            if loc not in loc_counts:
                errors.append(f"Invalid location {loc} at Checkpoint {cp_num}.")
            else:
                loc_counts[loc] += 1
                loc_sets[loc].append(s)

        for loc, count in loc_counts.items():
            if count != 4:
                errors.append(f"Checkpoint {cp_num} Location {loc} has {count} teams (expected exactly 4).")
        for loc, s_list in loc_sets.items():
            if sorted(s_list) != ["A", "B", "C", "D"]:
                errors.append(f"Checkpoint {cp_num} Location {loc} sets are {s_list} (expected exactly one A, B, C, D).")

    # Team distinct locations
    for a in allocations:
        locs = [_get(a, "cp1_location"), _get(a, "cp2_location"), _get(a, "cp3_location")]
        if len(set(locs)) != 3:
            errors.append(f"Team {_get(a, 'team_identifier')} does not have 3 distinct locations: {locs}.")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "summary": {
            "total_teams": len(allocations),
            "organizer_note": ORGANIZER_NOTES_SET_A_GATE2_Q3,
        },
        "organizer_note": ORGANIZER_NOTES_SET_A_GATE2_Q3
    }

def get_or_create_route_allocations(db: Session, force_regenerate: bool = False) -> List[Round1RouteAllocationModel]:
    """Retrieve existing allocations or initialize standard 32-team schedule."""
    existing = db.query(Round1RouteAllocationModel).order_by(Round1RouteAllocationModel.team_identifier.asc()).all()
    if existing and not force_regenerate:
        return existing

    if existing and force_regenerate:
        db.query(Round1RouteAllocationModel).delete()
        db.commit()

    generated = compute_deterministic_allocations()
    models = []
    # Match with existing teams in DB if available
    teams = db.query(Team).all()
    team_by_num = {str(t.team_number): t for t in teams}
    team_by_id = {t.id: t for t in teams}
    team_by_name = {t.name.lower(): t for t in teams}

    for g in generated:
        tid = g["team_identifier"]
        # Find matched team model if any: check exact, int, or 1000+ offset (e.g. 1002 -> 2)
        matched_team = team_by_num.get(tid) or team_by_id.get(f"team-{tid}")
        if not matched_team:
            try:
                num = int(tid)
                matched_team = team_by_num.get(str(num))
                if not matched_team and num > 1000:
                    matched_team = team_by_num.get(str(num - 1000)) or team_by_id.get(f"team-{num - 1000}")
            except ValueError:
                pass
        model = Round1RouteAllocationModel(
            id=f"alloc-{tid}",
            team_identifier=tid,
            team_id=matched_team.id if matched_team else None,
            team_name=matched_team.name if matched_team else f"Team {tid}",
            cp1_location=g["cp1_location"],
            cp1_set=g["cp1_set"],
            cp2_location=g["cp2_location"],
            cp2_set=g["cp2_set"],
            cp3_location=g["cp3_location"],
            cp3_set=g["cp3_set"],
            is_frozen=False
        )
        db.add(model)
        models.append(model)

    db.commit()
    for m in models:
        db.refresh(m)
    return models

def get_allocations_matrix(db: Session) -> Dict[str, Any]:
    """Return complete allocation matrix, validation report, and summary."""
    allocs = get_or_create_route_allocations(db)
    raw_dicts = [
        {
            "team_identifier": a.team_identifier,
            "cp1_location": a.cp1_location,
            "cp1_set": a.cp1_set,
            "cp2_location": a.cp2_location,
            "cp2_set": a.cp2_set,
            "cp3_location": a.cp3_location,
            "cp3_set": a.cp3_set,
        }
        for a in allocs
    ]
    val_report = validate_route_allocations(raw_dicts)

    items = []
    cfg = get_or_create_round1_config(db)
    start_utc = cfg.started_at

    for a in allocs:
        # Calculate completion & duration
        total_sec = None
        if a.cp3_completed and a.cp3_completed_at and start_utc:
            s_dt = start_utc.replace(tzinfo=timezone.utc) if start_utc.tzinfo is None else start_utc
            c_dt = a.cp3_completed_at.replace(tzinfo=timezone.utc) if a.cp3_completed_at.tzinfo is None else a.cp3_completed_at
            total_sec = max(0, round((c_dt - s_dt).total_seconds()))

        def _iso(dt):
            return dt.isoformat() if dt else None

        items.append({
            "team_identifier": a.team_identifier,
            "team_id": a.team_id,
            "team_name": a.team_name or f"Team {a.team_identifier}",
            "cp1_location": a.cp1_location,
            "cp1_set": a.cp1_set,
            "cp1_completed": a.cp1_completed,
            "cp1_completed_at": _iso(a.cp1_completed_at),
            "cp2_location": a.cp2_location,
            "cp2_set": a.cp2_set,
            "cp2_completed": a.cp2_completed,
            "cp2_completed_at": _iso(a.cp2_completed_at),
            "cp3_location": a.cp3_location,
            "cp3_set": a.cp3_set,
            "cp3_completed": a.cp3_completed,
            "cp3_completed_at": _iso(a.cp3_completed_at),
            "total_time_seconds": total_sec,
            "rank": None,
            "is_qualified": False
        })

    # Sort completed teams by total_time_seconds or cp3_completed_at
    completed = [i for i in items if i["cp3_completed"] and i["total_time_seconds"] is not None]
    completed.sort(key=lambda x: (x["total_time_seconds"], x["cp3_completed_at"]))
    for r_idx, c in enumerate(completed):
        c["rank"] = r_idx + 1
        c["is_qualified"] = (r_idx + 1) <= R1_QUALIFIERS

    return {
        "allocations": items,
        "is_valid": val_report["is_valid"],
        "validation_errors": val_report["errors"],
        "is_frozen": any(a.is_frozen for a in allocs),
        "summary": {
            "total_teams": len(items),
            "cp1_completed": sum(1 for i in items if i["cp1_completed"]),
            "cp2_completed": sum(1 for i in items if i["cp2_completed"]),
            "cp3_completed": sum(1 for i in items if i["cp3_completed"]),
            "qualified_count": sum(1 for i in items if i["is_qualified"]),
            "organizer_note": val_report["organizer_note"]
        }
    }

def create_or_resume_participant_session(db: Session, team_identifier: str) -> Dict[str, Any]:
    """
    Authenticate a participant with their 4-digit Team ID.
    Returns session token and current state.
    """
    clean_id = str(team_identifier).strip()
    alloc = db.query(Round1RouteAllocationModel).filter(Round1RouteAllocationModel.team_identifier == clean_id).first()
    if not alloc:
        # Check if allocations table is not yet populated
        if db.query(Round1RouteAllocationModel).count() == 0:
            get_or_create_route_allocations(db)
            alloc = db.query(Round1RouteAllocationModel).filter(Round1RouteAllocationModel.team_identifier == clean_id).first()

    if not alloc:
        # Also try matching integer padding
        try:
            num = int(clean_id)
            alloc = db.query(Round1RouteAllocationModel).filter(Round1RouteAllocationModel.team_identifier == str(num)).first()
        except ValueError:
            pass

    if not alloc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team ID '{clean_id}' is not registered in Round 1. Please check your 4-digit number."
        )

    # Check or create session token
    sess = db.query(Round1ParticipantSessionModel).filter(
        Round1ParticipantSessionModel.team_identifier == alloc.team_identifier,
        Round1ParticipantSessionModel.is_active == True
    ).first()

    if not sess:
        token = str(uuid.uuid4())
        sess = Round1ParticipantSessionModel(
            id=f"sess-{uuid.uuid4().hex[:12]}",
            session_token=token,
            team_identifier=alloc.team_identifier,
            team_id=alloc.team_id,
            is_active=True
        )
        db.add(sess)
        db.commit()
        db.refresh(sess)

    # Determine current checkpoint
    current_cp = 1
    if alloc.cp1_completed:
        current_cp = 2
    if alloc.cp2_completed:
        current_cp = 3
    if alloc.cp3_completed:
        current_cp = 4  # All 3 completed

    cfg = get_or_create_round1_config(db)
    is_active = bool(cfg.started_at) and not cfg.is_finalized

    return {
        "session_token": sess.session_token,
        "team_identifier": alloc.team_identifier,
        "team_name": alloc.team_name or f"Team {alloc.team_identifier}",
        "current_checkpoint": current_cp,
        "is_round_active": is_active,
        "is_complete": alloc.cp3_completed
    }

def get_participant_current_state(db: Session, session_token: str) -> Dict[str, Any]:
    """
    Returns ONLY the current location clue, attempts left, and status for the authenticated team.
    Future locations are strictly omitted from the API response.
    """
    sess = db.query(Round1ParticipantSessionModel).filter(
        Round1ParticipantSessionModel.session_token == session_token,
        Round1ParticipantSessionModel.is_active == True
    ).first()
    if not sess:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired participant session.")

    alloc = db.query(Round1RouteAllocationModel).filter(
        Round1RouteAllocationModel.team_identifier == sess.team_identifier
    ).first()
    if not alloc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team allocation not found.")

    cfg = get_or_create_round1_config(db)
    is_active = bool(cfg.started_at) and not cfg.is_finalized

    # Determine current checkpoint
    if not alloc.cp1_completed:
        current_cp = 1
        loc_num = alloc.cp1_location
        attempts_used = alloc.cp1_attempts
    elif not alloc.cp2_completed:
        current_cp = 2
        loc_num = alloc.cp2_location
        attempts_used = alloc.cp2_attempts
    elif not alloc.cp3_completed:
        current_cp = 3
        loc_num = alloc.cp3_location
        attempts_used = alloc.cp3_attempts
    else:
        current_cp = 4
        loc_num = None
        attempts_used = 0

    is_complete = (current_cp == 4)
    is_locked = (attempts_used >= R1_MAX_ATTEMPTS_PER_CHECKPOINT) and not is_complete
    attempts_remaining = max(0, R1_MAX_ATTEMPTS_PER_CHECKPOINT - attempts_used)

    qr_scanned = False
    if loc_num:
        tid_to_check = alloc.team_id or f"team-{sess.team_identifier}"
        chk = db.query(GateCheckinModel).filter(
            (GateCheckinModel.team_id == tid_to_check) | (GateCheckinModel.team_id == alloc.team_id),
            GateCheckinModel.gate_number == loc_num
        ).first()
        qr_scanned = bool(chk)

    # Get location clue
    loc_meta = R1_LOCATIONS.get(loc_num) if loc_num else None

    if is_complete:
        msg = "ROUND 1 COMPLETE — RETURN TO BASE POINT"
    elif not is_active:
        msg = "Awaiting organizer start signal."
    elif is_locked:
        msg = "Maximum attempts reached. Please contact an organizer or marshal."
    else:
        msg = f"Checkpoint R1.{current_cp} in progress."

    return {
        "team_identifier": alloc.team_identifier,
        "team_name": alloc.team_name or f"Team {alloc.team_identifier}",
        "current_checkpoint": current_cp,
        "current_location_number": loc_num,
        "location_name": loc_meta["name"] if loc_meta else None,
        "location_riddle": loc_meta["riddle"] if loc_meta else None,
        "location_target": loc_meta["target"] if loc_meta else None,
        "qr_scanned": qr_scanned,
        "attempts_used": attempts_used,
        "attempts_remaining": attempts_remaining,
        "is_locked": is_locked,
        "is_round_active": is_active,
        "is_complete": is_complete,
        "status_message": msg
    }

def record_participant_location_scan(db: Session, session_token: str, location_number: int) -> Dict[str, Any]:
    """
    Validates QR scan against the team's currently assigned location.
    Rejects wrong locations with 'This is not your current assigned location.' without revealing true location.
    Logs invalid scan in audit.
    """
    state = get_participant_current_state(db, session_token)
    team_ident = state["team_identifier"]
    current_loc = state["current_location_number"]

    if state["is_complete"]:
        return {
            "valid": False,
            "location": location_number,
            "message": "You have already completed Round 1. Return to Base Point."
        }

    if not state["is_round_active"]:
        return {
            "valid": False,
            "location": location_number,
            "message": "Round 1 has not officially started yet."
        }

    alloc = db.query(Round1RouteAllocationModel).filter(Round1RouteAllocationModel.team_identifier == team_ident).first()

    # Determine assigned question set
    cp = state["current_checkpoint"]
    assigned_set = None
    if cp == 1:
        assigned_set = alloc.cp1_set
    elif cp == 2:
        assigned_set = alloc.cp2_set
    elif cp == 3:
        assigned_set = alloc.cp3_set

    if location_number != current_loc:
        # Invalid location scan: log audit and reject cleanly
        log_audit_event(
            db=db,
            action="INVALID_LOCATION_SCAN",
            entity_type="Round1RouteAllocation",
            entity_id=alloc.id,
            actor_id=team_ident,
            actor_role="PARTICIPANT",
            round_number=1,
            details={
                "scanned_location": location_number,
                "expected_location": current_loc,
                "checkpoint": cp
            }
        )
        db.commit()
        return {
            "valid": False,
            "location": location_number,
            "message": "This is not your current assigned location."
        }

    # Check if this location was already verified for this team to avoid duplicate records
    team_db_id = alloc.team_id or f"team-{team_ident}"
    team_disp_name = alloc.team_name or f"Team {team_ident}"
    existing_scan = db.query(GateCheckinModel).filter(
        GateCheckinModel.team_id == team_db_id,
        GateCheckinModel.round_number == 1,
        GateCheckinModel.gate_number == location_number,
        GateCheckinModel.status == "VERIFIED"
    ).first()

    if existing_scan:
        return {
            "valid": True,
            "location": location_number,
            "message": f"Location {location_number} already verified! Please collect your Set {assigned_set} envelope from the marshal.",
            "question_set": assigned_set,
            "is_duplicate": True
        }

    # Valid new location scan: log in GateCheckinModel
    now_utc = datetime.now(timezone.utc)
    chk_id = f"scan-{uuid.uuid4().hex[:12]}"
    chk = GateCheckinModel(
        id=chk_id,
        team_id=team_db_id,
        team_name=team_disp_name,
        round_number=1,
        gate_number=location_number,
        scanned_at=now_utc,
        is_duplicate=False,
        attempt_number=1,
        status="VERIFIED",
        notes=f"Checkpoint R1.{cp} Location {location_number} scan verified."
    )
    db.add(chk)
    db.commit()

    return {
        "valid": True,
        "location": location_number,
        "message": f"Location {location_number} verified! Please collect your Set {assigned_set} envelope from the marshal.",
        "question_set": assigned_set
    }

def sync_participant_checkpoint_to_official_timing(
    db: Session,
    alloc: Round1RouteAllocationModel,
    checkpoint_num: int,
    completed_at: datetime
) -> None:
    """
    Synchronizes participant portal checkpoint completion into official tournament timing:
    1. round1_timings (MiniRoundTimingModel) - powers organizer live leaderboard.
    2. round1_records (Round1Record) - powers public scoreboard and official rankings.
    3. final_code_records (FinalCodeRecord) - awards Fragment 1 ('ODD') for CP1, Fragment 2 ('42') for CP2, and confirms Gate 3 for CP3.
    """
    team_db_id = alloc.team_id
    if not team_db_id:
        # Resolve against Team table
        team = db.query(Team).filter(Team.id == f"team-{alloc.team_identifier}").first()
        if not team:
            try:
                num = int(alloc.team_identifier)
                team = db.query(Team).filter(Team.team_number == num).first()
                if not team and num > 1000:
                    team = db.query(Team).filter(Team.team_number == (num - 1000)).first()
            except ValueError:
                pass
        if team:
            team_db_id = team.id
            alloc.team_id = team.id
        else:
            team_db_id = f"team-{alloc.team_identifier}"

    cfg = get_or_create_round1_config(db)

    # Determine start timestamp for this checkpoint mini-round
    if checkpoint_num == 1:
        # CP1 starts when Round 1 started globally, or fallback to allocation creation time
        start_dt = cfg.started_at or alloc.created_at or completed_at
    elif checkpoint_num == 2:
        # CP2 starts when CP1 completed
        start_dt = alloc.cp1_completed_at or completed_at
    elif checkpoint_num == 3:
        # CP3 starts when CP2 completed
        start_dt = alloc.cp2_completed_at or completed_at
    else:
        start_dt = completed_at

    # Normalize to timezone-aware UTC
    if start_dt and start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if completed_at and completed_at.tzinfo is None:
        completed_at = completed_at.replace(tzinfo=timezone.utc)

    duration_sec = max(0.0, (completed_at - start_dt).total_seconds())

    # 1. Update / Create MiniRoundTimingModel
    timing_id = f"r1-{team_db_id}-{checkpoint_num}"
    timing = db.query(MiniRoundTimingModel).filter(MiniRoundTimingModel.id == timing_id).first()
    if not timing:
        timing = MiniRoundTimingModel(
            id=timing_id,
            team_id=team_db_id,
            mini_round_number=checkpoint_num
        )
        db.add(timing)

    hints_used = timing.hints_used or 0
    hint_pen = timing.hint_penalty_seconds or 0
    phone_pen = timing.phone_penalty_seconds or 0
    sep_pen = timing.separation_penalty_seconds or 0
    clue_tamp = timing.clue_tampering_deduction or 0
    total_time_penalties = hint_pen + phone_pen + sep_pen - clue_tamp

    timing.start_time = start_dt
    timing.completion_time = completed_at
    timing.duration_seconds = round(duration_sec, 2)
    timing.adjusted_seconds = round(duration_sec + total_time_penalties, 2)
    timing.status = "Completed"

    # 2. Update Round1Record (mini_rounds_json)
    r1_rec = db.query(Round1Record).filter(Round1Record.team_id == team_db_id).first()
    if not r1_rec:
        r1_rec = Round1Record(
            team_id=team_db_id,
            mini_rounds_json=[
                {"roundNumber": 1, "hintsUsed": 0, "hintPenaltySeconds": 0, "isCompleted": False},
                {"roundNumber": 2, "hintsUsed": 0, "hintPenaltySeconds": 0, "isCompleted": False},
                {"roundNumber": 3, "hintsUsed": 0, "hintPenaltySeconds": 0, "isCompleted": False},
            ],
            qualification_status="Incomplete"
        )
        db.add(r1_rec)

    # Deep copy / ensure mini_rounds list is up to date
    mr_list = list(r1_rec.mini_rounds_json or [])
    while len(mr_list) < 3:
        mr_list.append({
            "roundNumber": len(mr_list) + 1,
            "hintsUsed": 0,
            "hintPenaltySeconds": 0,
            "isCompleted": False
        })

    target_idx = checkpoint_num - 1
    mr_entry = dict(mr_list[target_idx])
    mr_entry["isCompleted"] = True
    mr_entry["startTime"] = start_dt.isoformat()
    mr_entry["completionTime"] = completed_at.isoformat()
    mr_entry["durationSeconds"] = round(duration_sec, 2)
    mr_entry["hintsUsed"] = hints_used
    mr_entry["hintPenaltySeconds"] = hint_pen
    mr_list[target_idx] = mr_entry

    r1_rec.mini_rounds_json = mr_list
    # Recalculate totals across all 3 mini rounds
    from app.services.round_service import calculate_round1_record_scores
    calculate_round1_record_scores(r1_rec, penalty_per_hint=cfg.penalty_per_hint_seconds or 120.0)

    # 3. Synchronize Code Hunt Fragments
    try:
        if checkpoint_num == 1:
            code_hunt_service.record_fragment_1(db=db, team_id=team_db_id, fragment_value="ODD", actor="r1_portal")
        elif checkpoint_num == 2:
            code_hunt_service.record_fragment_2(db=db, team_id=team_db_id, fragment_value="42", actor="r1_portal")
        elif checkpoint_num == 3:
            code_hunt_rec = code_hunt_service.get_or_create_final_code_record(db, team_db_id)
            code_hunt_rec.gate_3_confirmed = True
            code_hunt_rec.gate_3_confirmed_at = completed_at
    except Exception:
        # Non-fatal if code hunt record already recorded
        pass

def submit_participant_checkpoint_answer(db: Session, session_token: str, submitted_answer: str) -> Dict[str, Any]:
    """
    Verifies answer against the team's assigned question set.
    Max 3 attempts per checkpoint.
    Advances checkpoint upon correct answer.
    """
    state = get_participant_current_state(db, session_token)
    if state["is_complete"]:
        return {
            "is_correct": False,
            "attempt_number": 0,
            "attempts_remaining": 0,
            "is_complete": True,
            "is_locked": True,
            "message": "Round 1 is already complete. Return to Base Point."
        }

    if state["is_locked"]:
        return {
            "is_correct": False,
            "attempt_number": state["attempts_used"],
            "attempts_remaining": 0,
            "is_complete": False,
            "is_locked": True,
            "message": "Maximum attempts reached. Please contact an organizer or marshal."
        }

    team_ident = state["team_identifier"]
    alloc = db.query(Round1RouteAllocationModel).filter(Round1RouteAllocationModel.team_identifier == team_ident).first()
    cp = state["current_checkpoint"]
    loc_num = state["current_location_number"]

    # Determine assigned set and expected answer
    if cp == 1:
        q_set = alloc.cp1_set
        attempts_used = alloc.cp1_attempts
    elif cp == 2:
        q_set = alloc.cp2_set
        attempts_used = alloc.cp2_attempts
    elif cp == 3:
        q_set = alloc.cp3_set
        attempts_used = alloc.cp3_attempts
    else:
        raise HTTPException(status_code=400, detail="Invalid checkpoint.")

    new_attempt_num = attempts_used + 1
    clean_sub = submitted_answer.strip().upper()
    expected_ans = R1_QUESTION_KEY.get(q_set, {}).get(str(cp), "").upper()

    # Special handling for Set A Gate 2 Q3 inconsistency: accept both "42" and "ENIGMA"
    is_correct = (clean_sub == expected_ans)
    if q_set == "A" and cp == 2 and clean_sub in ("42", "ENIGMA", "42-ENIGMA"):
        is_correct = True

    now_utc = datetime.now(timezone.utc)

    # Log attempt model
    att_model = Round1CheckpointAttemptModel(
        id=f"att-{uuid.uuid4().hex[:12]}",
        team_identifier=team_ident,
        team_id=alloc.team_id,
        checkpoint_number=cp,
        location_number=loc_num,
        question_set=q_set,
        attempt_number=new_attempt_num,
        submitted_answer=submitted_answer.strip(),
        is_correct=is_correct,
        created_at=now_utc
    )
    db.add(att_model)

    # Update allocation record
    if cp == 1:
        alloc.cp1_attempts = new_attempt_num
        if is_correct:
            alloc.cp1_completed = True
            alloc.cp1_completed_at = now_utc
    elif cp == 2:
        alloc.cp2_attempts = new_attempt_num
        if is_correct:
            alloc.cp2_completed = True
            alloc.cp2_completed_at = now_utc
    elif cp == 3:
        alloc.cp3_attempts = new_attempt_num
        if is_correct:
            alloc.cp3_completed = True
            alloc.cp3_completed_at = now_utc

    # Sync to official tournament timing and leaderboards if correct
    if is_correct:
        sync_participant_checkpoint_to_official_timing(db, alloc, cp, now_utc)

    db.commit()
    db.refresh(alloc)

    attempts_left = max(0, R1_MAX_ATTEMPTS_PER_CHECKPOINT - new_attempt_num)
    is_now_locked = (attempts_left == 0 and not is_correct)

    if is_correct:
        next_cp = cp + 1
        if next_cp <= 3:
            next_loc = alloc.cp2_location if next_cp == 2 else alloc.cp3_location
            next_clue = R1_LOCATIONS.get(next_loc, {}).get("riddle")
            msg = f"CORRECT! Checkpoint R1.{cp} verified. Next location unlocked."
        else:
            next_loc = None
            next_clue = None
            msg = "CORRECT! ROUND 1 COMPLETE — RETURN TO BASE POINT"

        return {
            "is_correct": True,
            "attempt_number": new_attempt_num,
            "attempts_remaining": attempts_left,
            "is_complete": (next_cp > 3),
            "is_locked": False,
            "message": msg,
            "next_checkpoint": next_cp if next_cp <= 3 else None,
            "next_location_clue": next_clue
        }
    else:
        if is_now_locked:
            msg = "Incorrect. Maximum attempts reached. Please contact an organizer or marshal."
        else:
            msg = f"Incorrect. {attempts_left} attempt{'s' if attempts_left > 1 else ''} remaining."

        return {
            "is_correct": False,
            "attempt_number": new_attempt_num,
            "attempts_remaining": attempts_left,
            "is_complete": False,
            "is_locked": is_now_locked,
            "message": msg,
            "next_checkpoint": None,
            "next_location_clue": None
        }

def get_location_volunteer_view(db: Session, checkpoint_number: int, location_number: int) -> Dict[str, Any]:
    """
    Shows the 4 expected teams at a specific location & checkpoint and their assigned envelope sets.
    Used by station volunteers to hand out the physical envelopes.
    """
    allocs = get_or_create_route_allocations(db)
    loc_meta = R1_LOCATIONS.get(location_number, {})

    expected = []
    for a in allocs:
        team_loc = getattr(a, f"cp{checkpoint_number}_location", None)
        team_set = getattr(a, f"cp{checkpoint_number}_set", None)
        team_done = getattr(a, f"cp{checkpoint_number}_completed", False)
        if team_loc == location_number:
            expected.append({
                "team_identifier": a.team_identifier,
                "team_name": a.team_name or f"Team {a.team_identifier}",
                "assigned_set": team_set,
                "is_completed": team_done
            })

    return {
        "checkpoint_number": checkpoint_number,
        "location_number": location_number,
        "location_name": loc_meta.get("name", f"Location {location_number}"),
        "expected_teams": expected
    }

def get_envelope_preparation_sheet(db: Session) -> List[Dict[str, Any]]:
    """
    Returns full list of 96 checkpoint-location-team assignments for physical envelope preparation.
    """
    allocs = get_or_create_route_allocations(db)
    sheet = []
    for cp in [1, 2, 3]:
        for a in allocs:
            loc = getattr(a, f"cp{cp}_location")
            s = getattr(a, f"cp{cp}_set")
            sheet.append({
                "checkpoint": cp,
                "location": loc,
                "team_identifier": a.team_identifier,
                "team_name": a.team_name or f"Team {a.team_identifier}",
                "question_set": s
            })
    sheet.sort(key=lambda x: (x["checkpoint"], x["location"], x["question_set"]))
    return sheet

def get_team_audit_details(db: Session, team_identifier: str) -> Dict[str, Any]:
    """
    Full organizer inspection of team route, sets, QR scans, attempts history, and audit events.
    """
    alloc = db.query(Round1RouteAllocationModel).filter(
        Round1RouteAllocationModel.team_identifier == str(team_identifier)
    ).first()
    if not alloc:
        raise HTTPException(status_code=404, detail=f"Team '{team_identifier}' not found in allocation.")

    attempts = db.query(Round1CheckpointAttemptModel).filter(
        Round1CheckpointAttemptModel.team_identifier == str(team_identifier)
    ).order_by(Round1CheckpointAttemptModel.created_at.asc()).all()

    def _iso(dt):
        return dt.isoformat() if dt else None

    # Query scan checkins and invalid scan audits
    checkins = db.query(GateCheckinModel).filter(
        (GateCheckinModel.team_id == alloc.team_id) | (GateCheckinModel.team_id == f"team-{team_identifier}")
    ).order_by(GateCheckinModel.scanned_at.asc()).all()

    invalid_audits = db.query(AuditLog).filter(
        AuditLog.actor_id == str(team_identifier),
        AuditLog.action == "INVALID_LOCATION_SCAN"
    ).order_by(AuditLog.timestamp.asc()).all()

    scans = []
    for c in checkins:
        scans.append({
            "checkpoint_number": 1,
            "location_number": c.gate_number,
            "is_valid_location": True,
            "scanned_at": _iso(c.scanned_at)
        })
    for a in invalid_audits:
        det = a.details or {}
        scans.append({
            "checkpoint_number": det.get("checkpoint", 1),
            "location_number": det.get("scanned_location", 0),
            "is_valid_location": False,
            "scanned_at": _iso(a.timestamp)
        })

    allocations_map = {
        "cp1": {
            "location": alloc.cp1_location,
            "location_name": R1_LOCATIONS.get(alloc.cp1_location, {}).get("name", f"Location {alloc.cp1_location}"),
            "set": alloc.cp1_set,
            "completed": alloc.cp1_completed,
            "completed_at": _iso(alloc.cp1_completed_at)
        },
        "cp2": {
            "location": alloc.cp2_location,
            "location_name": R1_LOCATIONS.get(alloc.cp2_location, {}).get("name", f"Location {alloc.cp2_location}"),
            "set": alloc.cp2_set,
            "completed": alloc.cp2_completed,
            "completed_at": _iso(alloc.cp2_completed_at)
        },
        "cp3": {
            "location": alloc.cp3_location,
            "location_name": R1_LOCATIONS.get(alloc.cp3_location, {}).get("name", f"Location {alloc.cp3_location}"),
            "set": alloc.cp3_set,
            "completed": alloc.cp3_completed,
            "completed_at": _iso(alloc.cp3_completed_at)
        },
    }

    cfg = get_or_create_round1_config(db)
    start_utc = cfg.started_at
    total_time_seconds = None
    if alloc.cp3_completed and alloc.cp3_completed_at and start_utc:
        s_dt = start_utc.replace(tzinfo=timezone.utc) if start_utc.tzinfo is None else start_utc
        c_dt = alloc.cp3_completed_at.replace(tzinfo=timezone.utc) if alloc.cp3_completed_at.tzinfo is None else alloc.cp3_completed_at
        total_time_seconds = max(0, round((c_dt - s_dt).total_seconds()))

    return {
        "team_identifier": alloc.team_identifier,
        "team_name": alloc.team_name,
        "current_checkpoint": 4 if alloc.cp3_completed else (3 if alloc.cp2_completed else (2 if alloc.cp1_completed else 1)),
        "is_completed": alloc.cp3_completed,
        "is_locked": alloc.cp1_attempts >= 3 and not alloc.cp1_completed or alloc.cp2_attempts >= 3 and not alloc.cp2_completed or alloc.cp3_attempts >= 3 and not alloc.cp3_completed,
        "total_time_seconds": total_time_seconds,
        "route": {
            "cp1": {"location": alloc.cp1_location, "set": alloc.cp1_set, "completed": alloc.cp1_completed, "completed_at": _iso(alloc.cp1_completed_at)},
            "cp2": {"location": alloc.cp2_location, "set": alloc.cp2_set, "completed": alloc.cp2_completed, "completed_at": _iso(alloc.cp2_completed_at)},
            "cp3": {"location": alloc.cp3_location, "set": alloc.cp3_set, "completed": alloc.cp3_completed, "completed_at": _iso(alloc.cp3_completed_at)},
        },
        "allocations": allocations_map,
        "scans": scans,
        "attempts": [
            {
                "checkpoint": att.checkpoint_number,
                "checkpoint_number": att.checkpoint_number,
                "location": att.location_number,
                "set": att.question_set,
                "attempt_number": att.attempt_number,
                "submitted_answer": att.submitted_answer,
                "is_correct": att.is_correct,
                "timestamp": _iso(att.created_at),
                "created_at": _iso(att.created_at)
            }
            for att in attempts
        ]
    }

def get_public_qualified_teams(db: Session) -> Dict[str, Any]:
    """
    Public participant view: reveals ONLY the 16 qualified Team IDs after Round 1 finalization.
    Zero scores, zero times, zero points.
    """
    cfg = get_or_create_round1_config(db)
    if not cfg.is_finalized:
        return {
            "is_finalized": False,
            "qualified_teams": [],
            "message": "Round 1 qualification has not been finalized by the organizers yet."
        }

    matrix = get_allocations_matrix(db)
    qualified = [a["team_identifier"] for a in matrix["allocations"] if a["is_qualified"]]
    return {
        "is_finalized": True,
        "qualified_teams": qualified,
        "message": f"{len(qualified)} squads qualified for Round 2."
    }


def reset_round1_live_state(db: Session, actor=None) -> Dict[str, Any]:
    """
    Resets Round 1 to a clean initial unstarted state:
    1. Removes all Round 1 gate check-in scan records (GateCheckinModel).
    2. Removes all Round 1 checkpoint attempts (Round1CheckpointAttemptModel).
    3. Resets all Round 1 route allocations progress (cp1/cp2/cp3 attempts=0, completed=False, completed_at=None).
    4. Resets all MiniRoundTimingModel timings for Round 1.
    5. Resets Round1Record mini-rounds and qualification status to Incomplete.
    6. Resets FinalCodeRecord fragments (Fragment 1 ODD, Fragment 2 42, gate 3 confirmation).
    7. Resets Round1ConfigModel: started_at=None, started_by=None, is_finalized=False, finalized_at=None, finalized_by=None.
    8. Resets RoundState(id=1): started_at=None, status="Not Started".
    PRESERVES:
    - All 32 teams and participants
    - Route allocations (cp locations & assigned sets)
    - Organizer accounts and credentials
    - Other rounds configuration and data
    """
    from app.models.round_models import RoundState

    # 1. Delete gate checkins for Round 1
    deleted_checkins = db.query(GateCheckinModel).filter(GateCheckinModel.round_number == 1).delete(synchronize_session=False)

    # 2. Delete checkpoint attempts
    deleted_attempts = db.query(Round1CheckpointAttemptModel).delete(synchronize_session=False)

    # 3. Reset route allocations progress (preserving route assignments)
    allocations = db.query(Round1RouteAllocationModel).all()
    for alloc in allocations:
        alloc.cp1_completed = False
        alloc.cp1_completed_at = None
        alloc.cp1_attempts = 0
        alloc.cp2_completed = False
        alloc.cp2_completed_at = None
        alloc.cp2_attempts = 0
        alloc.cp3_completed = False
        alloc.cp3_completed_at = None
        alloc.cp3_attempts = 0

    # 4. Reset mini round timings for Round 1
    timings = db.query(MiniRoundTimingModel).filter(MiniRoundTimingModel.mini_round_number.in_([1, 2, 3])).all()
    for t in timings:
        t.status = "Not Started"
        t.start_time = None
        t.completion_time = None
        t.duration_seconds = None
        t.adjusted_seconds = None
        t.hints_used = 0
        t.hint_penalty_seconds = 0
        t.phone_penalties_count = 0
        t.phone_penalty_seconds = 0
        t.separation_penalties_count = 0
        t.separation_penalty_seconds = 0
        t.clue_tampering_deduction = 0
        t.is_disqualified = False
        t.disqualification_reason = None
        t.checkpoints = []

    # 5. Reset Round1Record objects to pristine baseline
    r1_records = db.query(Round1Record).all()
    for r in r1_records:
        r.mini_rounds_json = [
            {"roundNumber": 1, "hintsUsed": 0, "hintPenaltySeconds": 0, "isCompleted": False},
            {"roundNumber": 2, "hintsUsed": 0, "hintPenaltySeconds": 0, "isCompleted": False},
            {"roundNumber": 3, "hintsUsed": 0, "hintPenaltySeconds": 0, "isCompleted": False},
        ]
        r.raw_total_seconds = None
        r.total_penalty_seconds = 0
        r.adjusted_total_seconds = None
        r.fastest_mini_round_seconds = None
        r.rank = None
        r.qualification_status = "Incomplete"
        r.tie_requires_review = False
        r.tie_reason = None
        r.is_complete = False

    # 6. Reset FinalCodeRecord fragment statuses awarded during Round 1
    code_records = db.query(FinalCodeRecord).all()
    for cr in code_records:
        cr.fragment_1_status = FragmentStatus.PENDING
        cr.fragment_1_discovered_at = None
        cr.fragment_1_discovered_round = None
        cr.fragment_1_discovered_by = None
        cr.fragment_2_status = FragmentStatus.PENDING
        cr.fragment_2_discovered_at = None
        cr.fragment_2_discovered_round = None
        cr.fragment_2_discovered_by = None
        cr.gate_3_confirmed = False
        cr.gate_3_confirmed_at = None
        cr.status = "IN_PROGRESS"
        cr.verification_status = "PENDING"
        cr.verified_at = None
        cr.verified_by = None

    # 7. Reset Round1ConfigModel
    cfg = get_or_create_round1_config(db)
    cfg.started_at = None
    cfg.started_by = None
    cfg.is_finalized = False
    cfg.finalized_at = None
    cfg.finalized_by = None

    # 8. Reset RoundState (id=1)
    from app.services.round_service import ensure_round_states_initialized
    ensure_round_states_initialized(db)
    rs = db.query(RoundState).filter(RoundState.id == 1).first()
    if rs:
        rs.started_at = None
        rs.completed_at = None
        rs.status = "Not Started"

    actor_id = getattr(actor, "id", None) or getattr(actor, "email", "system") if actor else "system"
    actor_role = getattr(actor, "role", "ORGANIZER") if actor else "ORGANIZER"
    if hasattr(actor_role, "value"):
        actor_role = actor_role.value

    log_audit_event(
        db=db,
        action="ROUND1_RESET_TO_INITIAL",
        entity_type="Round1Config",
        entity_id="1",
        actor_id=str(actor_id),
        actor_role=str(actor_role),
        round_number=1,
        details={
            "deleted_checkins": deleted_checkins,
            "deleted_attempts": deleted_attempts,
            "allocations_reset": len(allocations),
            "timings_reset": len(timings),
            "records_reset": len(r1_records),
        }
    )

    db.commit()

    return {
        "success": True,
        "is_started": False,
        "started_at": None,
        "deleted_checkins": deleted_checkins,
        "deleted_attempts": deleted_attempts,
        "message": "Round 1 state has been cleanly reset to initial unstarted state. 32 teams and allocations preserved."
    }
