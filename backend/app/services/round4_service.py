import random
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from fastapi import HTTPException, status
from app.models.round4 import (
    Round4ConfigModel, Round4PairModel, Round4StageTimingModel,
    Round4JudgeScoreModel, Round4AgentGuessModel,
    default_round4_rubric, default_final_score_formula
)
from app.models.core import Team, TeamStatus
from app.models.progression import TieReview
from app.scoring.round4_scoring import (
    calculate_panel_score, calculate_final_score_breakdown, process_round4_standings,
    validate_rubric_scores, calculate_legal_battle_score
)
from app.services.audit_service import log_audit_event
from app.services.progression_service import is_round_finalized, get_eligible_team_ids, record_round_finalization
from app.services.tie_review_service import get_or_create_tie_review
from app.services.round3_service import get_team_transactions, compute_team_ledger, get_or_create_black_market_config
from app.schemas.rounds.round4 import (
    UpdatePairCaseInput, SubmitJudgeScoreInput, SubmitAgentGuessInput,
    ResourcePersonQuestionInput
)
from app.core.constants import (
    R4_FINALISTS,
    R4_ADVANCING_COUNT,
    AGENT_CORRECT_GUESS,
    AGENT_WRONG_GUESS,
)

STAGE_IDS = ["prep_1", "hearing_1", "file_exchange", "prep_2", "hearing_2"]

# Default internal case templates for moot court pairing (customizable by organizers)
DEFAULT_R4_CASE_TEMPLATES = [
    {
        "id": "case-1",
        "name": "State vs. Apex Cybernetics",
        "details": "AI Trade Secret Theft, Autonomous Algorithm Sabotage, and Corporate Espionage",
    },
    {
        "id": "case-2",
        "name": "BioHealth Corp vs. Dr. Vance",
        "details": "Unauthorized Genetic Algorithmic Trials, Bio-Data Exploitation, and Ethical Breaches",
    },
    {
        "id": "case-3",
        "name": "City of Solitude vs. Quantum Grid",
        "details": "Critical Infrastructure Power Diversion, Smart-Grid Malfeasance, and Public Endangerment",
    },
    {
        "id": "case-4",
        "name": "AeroDynamics vs. Sentinel Security",
        "details": "Autonomous Drone Swarm Airspace Collision, Black-Box Data Tampering, and Liability Dispute",
    },
]

# Backward-compatible alias (internal templates/placeholders)
OFFICIAL_R4_CASES = DEFAULT_R4_CASE_TEMPLATES


def get_or_create_round4_config(db: Session) -> Round4ConfigModel:
    cfg = db.query(Round4ConfigModel).filter(Round4ConfigModel.id == 1).first()
    if not cfg:
        cfg = Round4ConfigModel(
            id=1,
            rubric_categories=default_round4_rubric(),
            is_rubric_confirmed=False,
            judge_aggregation="average",
            judges_list=[{"id": "judge-1", "name": "Faculty Judge 1"}, {"id": "judge-2", "name": "Faculty Judge 2"}],
            final_score_formula=default_final_score_formula(),
            advancing_teams_count=R4_ADVANCING_COUNT,
            is_finalized=False
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def ensure_round4_pairs(db: Session):
    for i in range(1, 5):
        p = db.query(Round4PairModel).filter(
            (Round4PairModel.pair_number == i) | (Round4PairModel.id == f"pair-{i}")
        ).first()
        if not p:
            case_data = OFFICIAL_R4_CASES[(i - 1) % len(OFFICIAL_R4_CASES)]
            p = Round4PairModel(
                id=f"pair-{i}",
                pair_number=i,
                case_id=case_data["id"],
                case_name=case_data["name"],
                case_details=case_data["details"],
                team_a_side="Prosecution / Plaintiff",
                team_b_side="Defense / Respondent"
            )
            db.add(p)
            db.commit()

        # Ensure stages exist
        for s_id in STAGE_IDS:
            stid = f"r4-{p.id}-{s_id}"
            st = db.query(Round4StageTimingModel).filter(Round4StageTimingModel.id == stid).first()
            if not st:
                st = Round4StageTimingModel(id=stid, pair_id=p.id, stage_id=s_id, status="not_started")
                db.add(st)
    db.commit()


def update_round4_config(db: Session, updates: Dict[str, Any], actor) -> Round4ConfigModel:
    cfg = get_or_create_round4_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Round 4 is finalized.")

    if "is_rubric_confirmed" in updates and updates["is_rubric_confirmed"] is not None:
        cfg.is_rubric_confirmed = bool(updates["is_rubric_confirmed"])
    if "isRubricConfirmed" in updates and updates["isRubricConfirmed"] is not None:
        cfg.is_rubric_confirmed = bool(updates["isRubricConfirmed"])
    if "rubric_categories" in updates and updates["rubric_categories"]:
        cfg.rubric_categories = updates["rubric_categories"]
    if "rubricCategories" in updates and updates["rubricCategories"]:
        cfg.rubric_categories = updates["rubricCategories"]
    if "judge_aggregation" in updates and updates["judge_aggregation"]:
        cfg.judge_aggregation = updates["judge_aggregation"]
    if "judgeAggregation" in updates and updates["judgeAggregation"]:
        cfg.judge_aggregation = updates["judgeAggregation"]
    if "final_score_formula" in updates and updates["final_score_formula"]:
        cfg.final_score_formula = updates["final_score_formula"]
    if "finalScoreFormula" in updates and updates["finalScoreFormula"]:
        cfg.final_score_formula = updates["finalScoreFormula"]
    if "advancing_teams_count" in updates and updates["advancing_teams_count"] is not None:
        cfg.advancing_teams_count = int(updates["advancing_teams_count"])
    if "advancingTeamsCount" in updates and updates["advancingTeamsCount"] is not None:
        cfg.advancing_teams_count = int(updates["advancingTeamsCount"])

    log_audit_event(
        db=db,
        action="ROUND4_CONFIG_UPDATED",
        entity_type="Round4Config",
        entity_id="1",
        actor_id=getattr(actor, "id", str(actor)),
        actor_role=getattr(actor, "role", "organizer"),
        round_number=4,
        details=updates
    )
    db.commit()
    db.refresh(cfg)
    return cfg


def auto_pair_round4_teams(
    db: Session,
    actor=None,
    seed: Optional[int] = None,
    confirm: bool = True
) -> List[Round4PairModel]:
    """
    Pairs the 8 qualified teams from Round 3 into 4 matchups with official cases.
    """
    cfg = get_or_create_round4_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Round 4 is finalized.")

    ensure_round4_pairs(db)
    eligible = get_eligible_team_ids(db, 4)
    if not eligible or len(eligible) < 8:
        # Fallback to all active squads in dev/testing
        active_teams = db.query(Team).filter(Team.status != TeamStatus.DISQUALIFIED).limit(8).all()
        eligible = [t.id for t in active_teams]

    squads = list(eligible[:8])
    if seed is not None:
        rng = random.Random(seed)
        rng.shuffle(squads)

    now = datetime.now(timezone.utc)
    pairs = db.query(Round4PairModel).order_by(Round4PairModel.pair_number.asc()).all()

    for i in range(4):
        pair = pairs[i] if i < len(pairs) else None
        if not pair:
            pair = Round4PairModel(id=f"pair-{i+1}", pair_number=i+1)
            db.add(pair)

        t_a = squads[i * 2] if len(squads) > i * 2 else None
        t_b = squads[i * 2 + 1] if len(squads) > i * 2 + 1 else None
        case_data = OFFICIAL_R4_CASES[i % len(OFFICIAL_R4_CASES)]

        pair.team_a_id = t_a
        pair.team_b_id = t_b
        pair.case_id = case_data["id"]
        pair.case_name = case_data["name"]
        pair.case_details = case_data["details"]
        pair.team_a_side = "Prosecution / Plaintiff"
        pair.team_b_side = "Defense / Respondent"

        if confirm and t_a and t_b:
            pair.is_confirmed = True
            pair.confirmed_at = now
            pair.confirmed_by = getattr(actor, "id", "system") if actor else "system"

    log_audit_event(
        db=db,
        action="ROUND4_AUTO_PAIRINGS_GENERATED",
        entity_type="Round4Pairs",
        entity_id="all",
        actor_id=getattr(actor, "id", "system") if actor else "system",
        actor_role=getattr(actor, "role", "organizer") if actor else "organizer",
        round_number=4,
        details={"seed": seed, "confirm": confirm, "paired_squads": len(squads)}
    )
    db.commit()
    return db.query(Round4PairModel).order_by(Round4PairModel.pair_number.asc()).all()


def update_pair(
    db: Session,
    pair_number: int,
    team_a_id: str,
    team_b_id: str,
    case_name: Optional[str] = None,
    team_a_side: Optional[str] = None,
    team_b_side: Optional[str] = None,
    actor = None
) -> Round4PairModel:
    ensure_round4_pairs(db)
    p = db.query(Round4PairModel).filter(
        (Round4PairModel.pair_number == pair_number) | (Round4PairModel.id == f"pair-{pair_number}")
    ).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pair {pair_number} not found.")

    if p.is_confirmed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pairing is confirmed/locked. Unlock first to modify.")

    r3_finalized = is_round_finalized(db, 3)
    if r3_finalized:
        eligible = set(get_eligible_team_ids(db, 4))
        if team_a_id not in eligible or team_b_id not in eligible:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Teams must be officially qualified from Round 3.")

    p.team_a_id = team_a_id
    p.team_b_id = team_b_id
    if case_name:
        p.case_name = case_name
    if team_a_side:
        p.team_a_side = team_a_side
    if team_b_side:
        p.team_b_side = team_b_side

    log_audit_event(
        db=db,
        action="PAIRING_UPDATED",
        entity_type="Round4Pair",
        entity_id=p.id,
        actor_id=getattr(actor, "id", "system") if actor else "system",
        actor_role=getattr(actor, "role", "organizer") if actor else "organizer",
        round_number=4,
        details={"team_a_id": team_a_id, "team_b_id": team_b_id, "case_name": p.case_name}
    )
    db.commit()
    db.refresh(p)
    return p


def confirm_pairings(db: Session, actor=None):
    ensure_round4_pairs(db)
    pairs = db.query(Round4PairModel).all()
    now = datetime.now(timezone.utc)
    for p in pairs:
        if not p.team_a_id or not p.team_b_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Pair {p.pair_number} has unassigned teams.")
        p.is_confirmed = True
        p.confirmed_at = now
        p.confirmed_by = getattr(actor, "id", "system") if actor else "system"

    log_audit_event(
        db=db,
        action="PAIRINGS_CONFIRMED",
        entity_type="Round4Pairs",
        entity_id="all",
        actor_id=getattr(actor, "id", "system") if actor else "system",
        actor_role=getattr(actor, "role", "organizer") if actor else "organizer",
        round_number=4,
        details={"count": len(pairs)}
    )
    db.commit()


def unlock_pairings(db: Session, actor=None):
    cfg = get_or_create_round4_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Round 4 is finalized.")

    pairs = db.query(Round4PairModel).all()
    for p in pairs:
        p.is_confirmed = False
        p.confirmed_at = None
        p.confirmed_by = None

    log_audit_event(
        db=db,
        action="PAIRINGS_UNLOCKED",
        entity_type="Round4Pairs",
        entity_id="all",
        actor_id=getattr(actor, "id", "system") if actor else "system",
        actor_role=getattr(actor, "role", "organizer") if actor else "organizer",
        round_number=4,
        details={}
    )
    db.commit()


def update_pair_case(db: Session, pair_id: str, updates: UpdatePairCaseInput, actor=None) -> Round4PairModel:
    ensure_round4_pairs(db)
    p = db.query(Round4PairModel).filter(Round4PairModel.id == pair_id).first()
    if not p:
        if pair_id.isdigit():
            p = db.query(Round4PairModel).filter(Round4PairModel.pair_number == int(pair_id)).first()
        elif pair_id.startswith("pair-") and pair_id[5:].isdigit():
            p = db.query(Round4PairModel).filter(Round4PairModel.pair_number == int(pair_id[5:])).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pair {pair_id} not found.")

    now = datetime.now(timezone.utc)
    if updates.case_id is not None:
        p.case_id = updates.case_id
    if updates.case_name is not None:
        p.case_name = updates.case_name
    if updates.case_details is not None:
        p.case_details = updates.case_details
    if updates.team_a_side is not None:
        p.team_a_side = updates.team_a_side
    if updates.team_b_side is not None:
        p.team_b_side = updates.team_b_side
    if updates.team_a_has_case_file is not None:
        p.team_a_has_case_file = updates.team_a_has_case_file
        if updates.team_a_has_case_file and not p.team_a_case_file_at:
            p.team_a_case_file_at = now
    if updates.team_a_has_opposing_file is not None:
        p.team_a_has_opposing_file = updates.team_a_has_opposing_file
        if updates.team_a_has_opposing_file and not p.team_a_opposing_file_at:
            p.team_a_opposing_file_at = now
    if updates.team_b_has_case_file is not None:
        p.team_b_has_case_file = updates.team_b_has_case_file
        if updates.team_b_has_case_file and not p.team_b_case_file_at:
            p.team_b_case_file_at = now
    if updates.team_b_has_opposing_file is not None:
        p.team_b_has_opposing_file = updates.team_b_has_opposing_file
        if updates.team_b_has_opposing_file and not p.team_b_opposing_file_at:
            p.team_b_opposing_file_at = now
    if updates.resource_person_name is not None:
        p.resource_person_name = updates.resource_person_name
    if updates.resource_person_notes is not None:
        p.resource_person_notes = updates.resource_person_notes
    if updates.resource_person_questions is not None:
        p.resource_person_questions_json = updates.resource_person_questions
    if updates.is_confirmed is not None:
        p.is_confirmed = updates.is_confirmed
        if updates.is_confirmed and not p.confirmed_at:
            p.confirmed_at = now
            p.confirmed_by = getattr(actor, "id", "system") if actor else "system"

    p.updated_at = now
    db.commit()
    db.refresh(p)
    return p


def record_resource_person_question(
    db: Session,
    pair_id: str,
    question_data: ResourcePersonQuestionInput,
    actor=None
) -> Round4PairModel:
    ensure_round4_pairs(db)
    p = db.query(Round4PairModel).filter(Round4PairModel.id == pair_id).first()
    if not p:
        if pair_id.isdigit():
            p = db.query(Round4PairModel).filter(Round4PairModel.pair_number == int(pair_id)).first()
        elif pair_id.startswith("pair-") and pair_id[5:].isdigit():
            p = db.query(Round4PairModel).filter(Round4PairModel.pair_number == int(pair_id[5:])).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Pair {pair_id} not found.")

    now = datetime.now(timezone.utc)
    curr_questions = list(p.resource_person_questions_json or [])
    entry = {
        "team_id": question_data.team_id,
        "teamId": question_data.team_id,
        "question": question_data.question,
        "answer": question_data.answer,
        "score": question_data.score,
        "notes": question_data.notes,
        "recorded_at": now.isoformat(),
        "recorded_by": getattr(actor, "id", "system") if actor else "system",
    }
    curr_questions.append(entry)
    p.resource_person_questions_json = curr_questions
    p.updated_at = now

    log_audit_event(
        db=db,
        action="RESOURCE_PERSON_QUESTION_RECORDED",
        entity_type="Round4Pair",
        entity_id=p.id,
        actor_id=getattr(actor, "id", "system") if actor else "system",
        actor_role=getattr(actor, "role", "marshal") if actor else "marshal",
        round_number=4,
        details={"team_id": question_data.team_id, "question": question_data.question}
    )
    db.commit()
    db.refresh(p)
    return p


def update_stage_timing(
    db: Session,
    pair_id: str,
    stage_id: str,
    status_val: str,
    duration: Optional[int] = None,
    notes: Optional[str] = None,
    actor=None
):
    ensure_round4_pairs(db)
    stid = f"r4-{pair_id}-{stage_id}"
    st = db.query(Round4StageTimingModel).filter(Round4StageTimingModel.id == stid).first()
    now = datetime.now(timezone.utc)
    if not st:
        st = Round4StageTimingModel(id=stid, pair_id=pair_id, stage_id=stage_id, status=status_val)
        db.add(st)

    st.status = status_val
    if status_val == "in_progress" and not st.started_at:
        st.started_at = now
    elif status_val == "completed":
        if not st.ended_at:
            st.ended_at = now
        if duration is not None:
            st.actual_duration_seconds = duration

    if notes is not None:
        st.notes = notes

    log_audit_event(
        db=db,
        action="STAGE_TIMING_UPDATED",
        entity_type="Round4StageTiming",
        entity_id=stid,
        actor_id=getattr(actor, "id", "system") if actor else "system",
        actor_role=getattr(actor, "role", "marshal") if actor else "marshal",
        round_number=4,
        details={"status": status_val, "duration": duration}
    )
    db.commit()


def submit_judge_score(
    db: Session,
    team_id: str,
    input_data: SubmitJudgeScoreInput,
    actor=None
) -> Round4JudgeScoreModel:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team '{team_id}' not found.")

    cfg = get_or_create_round4_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Round 4 is finalized.")

    # Validate category limits and rubric using scoring engine
    try:
        validated_scores = validate_rubric_scores(input_data.scores, cfg.rubric_categories)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    total_score = round(sum(validated_scores.values()), 2)
    js_id = f"js-{input_data.judge_id}-{team_id}"
    js = db.query(Round4JudgeScoreModel).filter(Round4JudgeScoreModel.id == js_id).first()
    if not js:
        js = Round4JudgeScoreModel(
            id=js_id,
            judge_id=input_data.judge_id,
            judge_name=input_data.judge_name,
            team_id=team_id,
            scores=validated_scores,
            total_score=total_score,
            is_submitted=True,
            submitted_at=datetime.now(timezone.utc),
            comments=input_data.comments
        )
        db.add(js)
    else:
        js.judge_name = input_data.judge_name
        js.scores = validated_scores
        js.total_score = total_score
        js.is_submitted = True
        js.submitted_at = datetime.now(timezone.utc)
        js.comments = input_data.comments

    log_audit_event(
        db=db,
        action="JUDGE_SCORE_SUBMITTED",
        entity_type="Round4JudgeScore",
        entity_id=js_id,
        actor_id=getattr(actor, "id", "system") if actor else "system",
        actor_role=getattr(actor, "role", "judge") if actor else "judge",
        round_number=4,
        details={"team_id": team_id, "judge_id": input_data.judge_id, "total_score": total_score}
    )
    db.commit()
    db.refresh(js)
    return js


def submit_agent_guess(
    db: Session,
    team_id: str,
    input_data: SubmitAgentGuessInput,
    actor=None
) -> Round4AgentGuessModel:
    """
    [ISOLATED / HISTORICAL AUDIT RECORDING]
    Records secret agent deduction for historical/record-keeping purposes.
    NOTE: In accordance with official tournament rules, Secret Agent guessing
    does NOT affect the Round 4 Legal Battle score (max 100 purely from moot court rubric).
    Official agent guessing workflows will be scored during the Finale (Step 14).
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team '{team_id}' not found.")

    cfg = get_or_create_round4_config(db)
    if cfg.is_finalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Round 4 is finalized.")

    pts = input_data.points_awarded
    if pts is None:
        # Section 8.2 values, even though this record is not what decides the
        # championship - the Finale does that, and finale_service already uses
        # these constants. A stored 10.0 here contradicted the published rules
        # and would have been read as authoritative by whoever came next.
        if input_data.outcome == "correct":
            pts = AGENT_CORRECT_GUESS
        elif input_data.outcome == "incorrect":
            pts = AGENT_WRONG_GUESS
        else:
            pts = 0.0

    ag = db.query(Round4AgentGuessModel).filter(Round4AgentGuessModel.team_id == team_id).first()
    now = datetime.now(timezone.utc)
    if not ag:
        ag = Round4AgentGuessModel(
            team_id=team_id,
            outcome=input_data.outcome,
            points_awarded=pts,
            is_verified=True,
            verified_by=getattr(actor, "id", "system") if actor else "system",
            verified_at=now,
            notes=input_data.notes
        )
        db.add(ag)
    else:
        ag.outcome = input_data.outcome
        ag.points_awarded = pts
        ag.is_verified = True
        ag.verified_by = getattr(actor, "id", "system") if actor else "system"
        ag.verified_at = now
        ag.notes = input_data.notes

    log_audit_event(
        db=db,
        action="AGENT_GUESS_SUBMITTED",
        entity_type="Round4AgentGuess",
        entity_id=team_id,
        actor_id=getattr(actor, "id", "system") if actor else "system",
        actor_role=getattr(actor, "role", "organizer") if actor else "organizer",
        round_number=4,
        details={"outcome": input_data.outcome, "points": input_data.points_awarded}
    )
    db.commit()
    db.refresh(ag)
    return ag


def get_round4_overview(db: Session) -> Dict[str, Any]:
    cfg = get_or_create_round4_config(db)
    ensure_round4_pairs(db)
    r3_finalized = is_round_finalized(db, 3)
    eligible_team_ids = get_eligible_team_ids(db, 4)

    teams = db.query(Team).filter(Team.id.in_(eligible_team_ids)).all() if (r3_finalized and eligible_team_ids) else db.query(Team).filter(Team.status != TeamStatus.DISQUALIFIED).limit(8).all()

    team_map = {t.id: t for t in db.query(Team).all()}
    pairs = db.query(Round4PairModel).all()
    stages = db.query(Round4StageTimingModel).all()
    stages_by_pair = {}
    for s in stages:
        stages_by_pair.setdefault(s.pair_id, {})[s.stage_id] = {
            "stage_id": s.stage_id,
            "status": s.status,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "actual_duration_seconds": s.actual_duration_seconds,
            "notes": s.notes
        }

    pairs_dict_list = []
    pair_by_team = {}
    for p in pairs:
        p_stages = stages_by_pair.get(p.id, {})
        p_dict = {
            "id": p.id,
            "pair_number": p.pair_number,
            "team_a_id": p.team_a_id,
            "team_b_id": p.team_b_id,
            "team_a_name": team_map.get(p.team_a_id).name if p.team_a_id and team_map.get(p.team_a_id) else None,
            "team_b_name": team_map.get(p.team_b_id).name if p.team_b_id and team_map.get(p.team_b_id) else None,
            "is_confirmed": p.is_confirmed,
            "confirmed_at": p.confirmed_at.isoformat() if p.confirmed_at else None,
            "confirmed_by": p.confirmed_by,
            "case_id": p.case_id,
            "case_name": p.case_name,
            "case_details": p.case_details,
            "team_a_side": p.team_a_side,
            "team_b_side": p.team_b_side,
            "team_a_has_case_file": p.team_a_has_case_file,
            "team_a_has_opposing_file": p.team_a_has_opposing_file,
            "team_b_has_case_file": p.team_b_has_case_file,
            "team_b_has_opposing_file": p.team_b_has_opposing_file,
            "resource_person_name": p.resource_person_name,
            "resource_person_notes": p.resource_person_notes,
            "resource_person_questions": p.resource_person_questions_json or [],
            "is_questioning_complete": p.is_questioning_complete,
            "stages": p_stages
        }
        pairs_dict_list.append(p_dict)
        if p.team_a_id:
            pair_by_team[p.team_a_id] = (p, "team_a")
        if p.team_b_id:
            pair_by_team[p.team_b_id] = (p, "team_b")

    # Scores
    scores = db.query(Round4JudgeScoreModel).all()
    scores_by_team = {}
    for sc in scores:
        scores_by_team.setdefault(sc.team_id, []).append({
            "judge_id": sc.judge_id,
            "judge_name": sc.judge_name,
            "scores": sc.scores,
            "total_score": sc.total_score,
            "is_submitted": sc.is_submitted
        })

    agent_guesses = {ag.team_id: {"outcome": ag.outcome, "points_awarded": ag.points_awarded, "is_verified": ag.is_verified} for ag in db.query(Round4AgentGuessModel).all()}

    # Fetch black market balances
    bm_cfg = get_or_create_black_market_config(db)
    raw_records = []
    for t in teams:
        t_scores = scores_by_team.get(t.id, [])
        panel_eval = calculate_panel_score(t_scores, cfg.judge_aggregation)
        t_txs = get_team_transactions(db, t.id)
        ledger = compute_team_ledger(t.id, t_txs, bm_cfg.starting_balance)
        agent_g = agent_guesses.get(t.id)

        fs_breakdown = calculate_final_score_breakdown(
            team_id=t.id,
            panel_score=panel_eval["panel_score"],
            agent_record=agent_g,
            black_market_balance=ledger["current_balance"],
            formula=cfg.final_score_formula or {},
            is_guessing_configured=cfg.is_guessing_rules_configured
        )

        pair_info = pair_by_team.get(t.id)
        pairing_id = pair_info[0].id if pair_info else None
        side = (pair_info[0].team_a_side if pair_info[1] == "team_a" else pair_info[0].team_b_side) if pair_info else "Unassigned"
        case_name = pair_info[0].case_name if pair_info else None

        raw_records.append({
            "team_id": t.id,
            "team_number": t.team_number,
            "team_name": t.name,
            "round3_qualified": (t.id in eligible_team_ids) if r3_finalized else True,
            "pairing_id": pairing_id,
            "side": side,
            "case_name": case_name,
            "panel_score": panel_eval["panel_score"],
            "is_judge_panel_complete": panel_eval["is_complete"],
            "final_score_breakdown": fs_breakdown,
            "review_status": "Ready for Review" if fs_breakdown["is_complete"] else "Awaiting Scores",
            "is_advancing": True  # NO ELIMINATION: All 8 finalists advance to Finale
        })

    standings = process_round4_standings(
        records=raw_records,
        pairs=pairs_dict_list,
        config={
            "final_score_formula": cfg.final_score_formula,
            "advancing_teams_count": cfg.advancing_teams_count or R4_ADVANCING_COUNT,
            "is_finalized": cfg.is_finalized
        },
        round3_finalized=r3_finalized
    )

    adv_count = cfg.advancing_teams_count or R4_ADVANCING_COUNT
    if standings.get("ties_affecting_cutoff"):
        tied_teams = [r for r in standings["records"] if r["team_id"] in standings["tied_teams_at_cutoff"]]
        get_or_create_tie_review(
            db=db,
            round_number=4,
            teams_involved=tied_teams,
            ranking_metric="final_score",
            cutoff_position=adv_count,
            notes="Final score tie straddles advancing cutoff for Grand Finale."
        )

    tie_rev = db.query(TieReview).filter(TieReview.id == f"tie-r4-cutoff{adv_count}").first()
    if tie_rev and tie_rev.review_status == "RESOLVED" and standings.get("ties_affecting_cutoff"):
        standings["can_finalize"] = len([i for i in standings["issues"] if i["code"] != "CUTOFF_TIE"]) == 0
        standings["issues"] = [i for i in standings["issues"] if i["code"] != "CUTOFF_TIE"]

    from app.services.round_service import ensure_round_states_initialized
    ensure_round_states_initialized(db)
    from app.models.round_models import RoundState
    rs = db.query(RoundState).filter(RoundState.id == 4).first()
    qual_count = rs.qualifying_teams_count if rs and rs.qualifying_teams_count is not None else adv_count
    config_json = rs.config_json if rs else {}

    return {
        "id": 4,
        "name": rs.name if rs else "Round 4 — The Legal Battle",
        "codename": rs.codename if rs else "ROUND_4_LEGAL_BATTLE",
        "status": rs.status if rs else "In Progress",
        "isFinalized": cfg.is_finalized or (rs.is_finalized if rs else False),
        "qualifyingTeamsCount": qual_count,
        "qualifying_teams_count": qual_count,
        "config_json": config_json,
        "configJson": config_json,
        "config": {
            "rubric_categories": cfg.rubric_categories or [],
            "is_rubric_confirmed": cfg.is_rubric_confirmed,
            "judge_aggregation": cfg.judge_aggregation,
            "judges_list": cfg.judges_list or [],
            "final_score_formula": cfg.final_score_formula or {},
            "advancing_teams_count": adv_count,
            "is_finalized": cfg.is_finalized,
            "finalized_at": cfg.finalized_at.isoformat() if cfg.finalized_at else None,
            "finalized_by": cfg.finalized_by
        },
        "pairs": pairs_dict_list,
        "records": standings["records"],
        "can_finalize": standings["can_finalize"],
        "issues": standings["issues"],
        "checklist": standings["checklist"],
        "ties_affecting_cutoff": standings["ties_affecting_cutoff"]
    }


def finalize_round4(db: Session, actor, override_discrepancy: bool = False) -> Dict[str, Any]:
    cfg = get_or_create_round4_config(db)
    if cfg.is_finalized:
        return {"can_finalize": True, "issues": [], "finalized": True, "message": "Round 4 is already finalized."}

    overview = get_round4_overview(db)
    if not overview["can_finalize"] and not override_discrepancy:
        return {"can_finalize": False, "issues": overview["issues"], "finalized": False, "message": "Finalization blocked by server-side safeguards."}

    advancing_count = cfg.advancing_teams_count or R4_ADVANCING_COUNT
    records = overview["records"]

    # Official rule: All 8 finalists proceed to the Grand Finale
    advancing_team_ids = [r["team_id"] for r in records if r.get("rank") and r["rank"] <= advancing_count]
    if len(advancing_team_ids) == 0 and len(records) > 0:
        advancing_team_ids = [r["team_id"] for r in records]

    tie_rev = db.query(TieReview).filter(TieReview.id == f"tie-r4-cutoff{advancing_count}").first()
    if tie_rev and tie_rev.review_status == "RESOLVED" and tie_rev.advancing_team_ids:
        resolved_adv = set(tie_rev.advancing_team_ids)
        advancing_team_ids = [r["team_id"] for r in records if (r.get("rank") and r["rank"] < advancing_count) or (r["team_id"] in resolved_adv)]

    record_round_finalization(
        db=db,
        round_number=4,
        records=records,
        advancing_team_ids=advancing_team_ids,
        finalized_by=getattr(actor, "id", "organizer") if actor else "organizer"
    )

    # Update advancing teams current_round to 5 and is_qualified_for_next_round to True
    for team_id in advancing_team_ids:
        t = db.query(Team).filter(Team.id == team_id).first()
        if t:
            t.current_round = 5
            t.is_qualified_for_next_round = True

    # Activate Round 5 state
    from app.models.round_models import RoundState
    r5_state = db.query(RoundState).filter(RoundState.id == 5).first()
    if r5_state:
        r5_state.status = "In Progress"

    cfg.is_finalized = True
    cfg.finalized_at = datetime.now(timezone.utc)
    cfg.finalized_by = getattr(actor, "id", "organizer") if actor else "organizer"

    log_audit_event(
        db=db,
        action="ROUND_FINALIZED",
        entity_type="Round4Config",
        entity_id="1",
        actor_id=getattr(actor, "id", "organizer") if actor else "organizer",
        actor_role=getattr(actor, "role", "organizer") if actor else "organizer",
        round_number=4,
        details={"advancing_team_ids": advancing_team_ids, "advancing_count": len(advancing_team_ids)}
    )
    db.commit()

    return {
        "can_finalize": True,
        "issues": [],
        "finalized": True,
        "advancing_team_ids": advancing_team_ids,
        "message": f"Round 4 successfully finalized. {len(advancing_team_ids)} finalist squads advance to Grand Finale."
    }
