import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.constants import (
    R4_FINALISTS,
    R4_PAIRS,
    R4_MAX_SCORE,
    R4_ADVANCING_COUNT,
    R4_RUBRIC_LOGICAL_STRUCTURE_MAX,
    R4_RUBRIC_EVIDENCE_MAX,
    R4_RUBRIC_REBUTTAL_MAX,
    R4_RUBRIC_RESOURCE_PERSON_MAX,
    R4_RUBRIC_PRESENTATION_TEAMWORK_MAX,
    R4_RUBRIC_TIME_MAX,
    R4_RUBRIC_TOTAL_MAX,
)
from app.scoring.round4_scoring import (
    validate_rubric_scores,
    calculate_legal_battle_score,
    calculate_panel_score,
    calculate_final_score_breakdown,
    process_round4_standings,
)
from app.models.core import Team, TeamStatus
from app.models.round4 import Round4ConfigModel, Round4PairModel, Round4JudgeScoreModel
from app.models.progression import RoundQualification
from app.models.round_models import RoundState
from app.services import round4_service, progression_service
from app.schemas.rounds.round4 import (
    SubmitJudgeScoreInput,
    SubmitAgentGuessInput,
    UpdatePairCaseInput,
    ResourcePersonQuestionInput,
    UpdateStageInput,
    CreatePairInput,
)


@pytest.fixture
def sample_squads(db_session: Session):
    """Creates 8 active finalist squads for testing."""
    squads = []
    for i in range(1, 9):
        t = Team(
            id=f"team-finalist-{i}",
            name=f"Finalist Squad {i}",
            team_number=i,
            status=TeamStatus.ACTIVE,
            current_round=4,
            is_qualified_for_next_round=False,
        )
        db_session.add(t)
        squads.append(t)
    db_session.commit()
    for s in squads:
        db_session.refresh(s)
    return squads


# ==============================================================================
# 1. UNIT TESTS: RUBRIC VALIDATION & SCORING ENGINE
# ==============================================================================

def test_calculate_legal_battle_score_perfect():
    score = calculate_legal_battle_score(
        logical_structure=20.0,
        evidence=20.0,
        rebuttal=20.0,
        resource_person_questioning=15.0,
        presentation_teamwork=15.0,
        time=10.0,
    )
    assert score == 100.0


def test_calculate_legal_battle_score_partial():
    score = calculate_legal_battle_score(
        logical_structure=18.5,
        evidence=17.0,
        rebuttal=16.5,
        resource_person_questioning=13.0,
        presentation_teamwork=14.0,
        time=9.0,
    )
    assert score == 88.0


def test_validate_rubric_scores_rejection_negative():
    with pytest.raises(ValueError, match="cannot be negative"):
        validate_rubric_scores({"logical_structure": -5.0})


def test_validate_rubric_scores_rejection_category_overflow():
    # Logical structure max is 20.0
    with pytest.raises(ValueError, match="exceeds maximum allowed marks of 20"):
        validate_rubric_scores({"logical_structure": 25.0})

    # Resource person questioning max is 15.0
    with pytest.raises(ValueError, match="exceeds maximum allowed marks of 15"):
        validate_rubric_scores({"resource_person_questioning": 16.0})

    # Time max is 10.0
    with pytest.raises(ValueError, match="exceeds maximum allowed marks of 10"):
        validate_rubric_scores({"time": 12.0})


def test_validate_rubric_scores_rejection_total_overflow():
    with pytest.raises(ValueError):
        validate_rubric_scores({
            "logical_structure": 20.0,
            "evidence": 20.0,
            "rebuttal": 20.0,
            "resource_person_questioning": 15.0,
            "presentation_teamwork": 15.0,
            "time": 10.0,
            "extra_custom": 10.0,
        })


def test_validate_rubric_scores_alias_handling():
    # Normalizes evidence_use, resource_questioning, time_management
    scores = {
        "logical_structure": 19.0,
        "evidence_use": 18.0,
        "rebuttal": 19.0,
        "resource_questioning": 14.0,
        "presentation_teamwork": 14.0,
        "time_management": 9.0,
    }
    validated = validate_rubric_scores(scores)
    assert validated["evidence_use"] == 18.0
    assert sum(validated.values()) == 93.0


# ==============================================================================
# 2. UNIT TESTS: MULTI-JUDGE PANEL AGGREGATION
# ==============================================================================

def test_panel_score_empty():
    res = calculate_panel_score([])
    assert res["panel_score"] is None
    assert res["is_complete"] is False
    assert res["submitted_count"] == 0


def test_panel_score_single_judge():
    scorecards = [{"is_submitted": True, "total_score": 88.5}]
    res = calculate_panel_score(scorecards, aggregation="average")
    assert res["panel_score"] == 88.5
    assert res["is_complete"] is True
    assert res["submitted_count"] == 1


def test_panel_score_multi_judge_average():
    scorecards = [
        {"is_submitted": True, "total_score": 80.0},
        {"is_submitted": True, "total_score": 90.0},
        {"is_submitted": True, "total_score": 85.0},
    ]
    res = calculate_panel_score(scorecards, aggregation="average")
    assert res["panel_score"] == 85.0
    assert res["is_complete"] is True
    assert res["submitted_count"] == 3


def test_panel_score_multi_judge_sum():
    scorecards = [
        {"is_submitted": True, "total_score": 80.0},
        {"is_submitted": True, "total_score": 90.0},
    ]
    res = calculate_panel_score(scorecards, aggregation="sum")
    assert res["panel_score"] == 170.0
    assert res["is_complete"] is True


def test_panel_score_multi_judge_median():
    scorecards = [
        {"is_submitted": True, "total_score": 75.0},
        {"is_submitted": True, "total_score": 95.0},
        {"is_submitted": True, "total_score": 88.0},
    ]
    res = calculate_panel_score(scorecards, aggregation="median")
    assert res["panel_score"] == 88.0
    assert res["is_complete"] is True


# ==============================================================================
# 3. UNIT TESTS: NO-ELIMINATION STANDINGS ENGINE
# ==============================================================================

def test_round4_no_elimination_all_8_advance():
    records = []
    for i in range(8):
        records.append({
            "team_id": f"team-{i+1}",
            "team_number": i + 1,
            "team_name": f"Finalist Squad {i+1}",
            "panel_score": float(95 - i * 3),
            "is_judge_panel_complete": True,
            "final_score_breakdown": {
                "final_score": float(95 - i * 3),
                "is_complete": True
            }
        })

    pairs = [
        {
            "id": f"pair-{i+1}",
            "team_a_id": f"team-{i*2+1}",
            "team_b_id": f"team-{i*2+2}",
            "is_confirmed": True,
            "case_name": f"Case {i+1}",
            "team_a_side": "Prosecution",
            "team_b_side": "Defense",
            "stages": {
                "hearing_1": {"status": "completed"},
                "file_exchange": {"status": "completed"},
                "hearing_2": {"status": "completed"}
            }
        }
        for i in range(4)
    ]

    standings = process_round4_standings(
        records=records,
        pairs=pairs,
        config={"final_score_formula": {"isFormulaConfirmed": True}, "advancing_teams_count": 8},
        round3_finalized=True
    )

    assert standings["can_finalize"] is True
    assert len(standings["advancing_team_ids"]) == 8
    assert len(standings["eliminated_team_ids"]) == 0
    # Every single record has is_advancing == True
    for r in standings["records"]:
        assert r["is_advancing"] is True
        assert 1 <= r["rank"] <= 8


# ==============================================================================
# 4. SERVICE TESTS: AUTO-PAIRING, STAGES & FINALIZATION
# ==============================================================================

def test_round4_auto_pairing_and_cases(db_session: Session, sample_squads):
    # Ensure pairs are generated and assigned official cases
    pairs = round4_service.auto_pair_round4_teams(db_session, seed=42, confirm=True)
    assert len(pairs) == 4
    for i, p in enumerate(pairs):
        assert p.pair_number == i + 1
        assert p.team_a_id is not None
        assert p.team_b_id is not None
        assert p.case_name is not None
        assert p.team_a_side == "Prosecution / Plaintiff"
        assert p.team_b_side == "Defense / Respondent"
        assert p.is_confirmed is True


def test_round4_stage_timing_lifecycle(db_session: Session):
    round4_service.ensure_round4_pairs(db_session)
    pair_id = "pair-1"

    # Start hearing 1
    round4_service.update_stage_timing(
        db=db_session,
        pair_id=pair_id,
        stage_id="hearing_1",
        status_val="in_progress",
        actor=None
    )

    overview = round4_service.get_round4_overview(db_session)
    pair = next(p for p in overview["pairs"] if p["id"] == pair_id)
    assert pair["stages"]["hearing_1"]["status"] == "in_progress"

    # Complete hearing 1 with duration
    round4_service.update_stage_timing(
        db=db_session,
        pair_id=pair_id,
        stage_id="hearing_1",
        status_val="completed",
        duration=1800,
        notes="All initial arguments completed on time.",
        actor=None
    )

    overview = round4_service.get_round4_overview(db_session)
    pair = next(p for p in overview["pairs"] if p["id"] == pair_id)
    assert pair["stages"]["hearing_1"]["status"] == "completed"
    assert pair["stages"]["hearing_1"]["actual_duration_seconds"] == 1800


def test_round4_resource_person_questioning(db_session: Session, sample_squads):
    round4_service.ensure_round4_pairs(db_session)
    team_a = sample_squads[0]

    q_input = ResourcePersonQuestionInput(
        team_id=team_a.id,
        question="What cryptographic algorithm secured the ledger?",
        answer="SHA-256 with elliptic-curve signatures.",
        score=14.5,
        notes="Accurate and articulate technical response."
    )
    p = round4_service.record_resource_person_question(
        db=db_session,
        pair_id="pair-1",
        question_data=q_input,
        actor=None
    )
    assert len(p.resource_person_questions_json) == 1
    assert p.resource_person_questions_json[0]["question"] == "What cryptographic algorithm secured the ledger?"


def test_round4_full_finalization_advances_all_8(db_session: Session, sample_squads):
    # Setup 8 squads in Round 4
    squads = sample_squads[:8]
    assert len(squads) == 8

    # Auto pair
    round4_service.auto_pair_round4_teams(db_session, seed=100, confirm=True)

    # Complete all stages for all 4 pairs
    for i in range(1, 5):
        for st in ["hearing_1", "file_exchange", "hearing_2"]:
            round4_service.update_stage_timing(db_session, f"pair-{i}", st, "completed", 600, None, None)

    # Submit judge scorecards for all 8 teams
    for i, t in enumerate(squads):
        round4_service.submit_judge_score(
            db=db_session,
            team_id=t.id,
            input_data=SubmitJudgeScoreInput(
                judge_id="judge-lead",
                judge_name="Chief Justice Evelyn",
                team_id=t.id,
                scores={
                    "logical_structure": 18.0,
                    "evidence": 19.0,
                    "rebuttal": 17.0,
                    "resource_person_questioning": 14.0,
                    "presentation_teamwork": 14.0,
                    "time": 9.0,
                },
                comments=f"Excellent courtroom advocacy by {t.name}"
            ),
            actor=None
        )

    # Confirm formula in config
    round4_service.update_round4_config(
        db=db_session,
        updates={"final_score_formula": {"isFormulaConfirmed": True, "panelScoreWeight": 1.0, "blackMarketWeightPercent": 10.0}},
        actor=None
    )

    # Finalize Round 4
    res = round4_service.finalize_round4(db_session, actor=None, override_discrepancy=True)
    assert res["finalized"] is True
    assert len(res["advancing_team_ids"]) == 8

    # Verify RoundQualification table has all 8 advancing
    quals = db_session.query(RoundQualification).filter(
        RoundQualification.round_number == 4,
        RoundQualification.is_advancing == True
    ).all()
    assert len(quals) == 8

    # Verify all 8 teams are now in round 5
    for t in squads:
        refreshed = db_session.query(Team).filter(Team.id == t.id).first()
        assert refreshed.current_round == 5
        assert refreshed.is_qualified_for_next_round is True

    # Verify progression eligibility for Round 5 (Grand Finale)
    r5_eligible = progression_service.get_eligible_team_ids(db_session, 5)
    assert len(r5_eligible) == 8


# ==============================================================================
# 5. INTEGRATION TESTS: REST API ENDPOINTS & RBAC
# ==============================================================================

def test_api_get_round4_overview(client: TestClient, organizer_headers: dict):
    resp = client.get("/api/v1/rounds/4")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == 4
    assert "Legal Battle" in data["name"]
    assert "pairs" in data
    assert "records" in data


def test_api_get_round4_config_and_update(client: TestClient, organizer_headers: dict, marshal_headers: dict):
    # Get config
    get_res = client.get("/api/v1/rounds/4/config")
    assert get_res.status_code == 200
    cfg = get_res.json()["data"]
    assert len(cfg["rubricCategories"]) == 6

    # Update config (Organizer allowed)
    put_res = client.put(
        "/api/v1/rounds/4/config",
        json={"isRubricConfirmed": True, "judgeAggregation": "average"},
        headers=organizer_headers
    )
    assert put_res.status_code == 200
    assert put_res.json()["data"]["isRubricConfirmed"] is True


def test_api_auto_pair_and_lock_unlock(client: TestClient, organizer_headers: dict):
    # Create 8 teams
    t_ids = []
    for i in range(8):
        t_res = client.post(
            "/api/v1/teams",
            json={"name": f"Legal Eagle {i+1}", "identifier": f"LE{i+1:02d}"},
            headers=organizer_headers
        )
        t_ids.append(t_res.json()["data"]["id"])

    # Auto pair
    pair_res = client.post("/api/v1/rounds/4/pairs/auto", json={"seed": 42, "confirm": True}, headers=organizer_headers)
    assert pair_res.status_code == 200
    pairs = pair_res.json()["data"]
    assert len(pairs) == 4

    # Unlock
    unlock_res = client.post("/api/v1/rounds/4/pairs/unlock", headers=organizer_headers)
    assert unlock_res.status_code == 200
    assert unlock_res.json()["data"]["confirmed"] is False

    # Confirm
    lock_res = client.post("/api/v1/rounds/4/pairs/confirm", headers=organizer_headers)
    assert lock_res.status_code == 200
    assert lock_res.json()["data"]["confirmed"] is True


def test_api_judge_score_submission_and_rubric_bounds(client: TestClient, organizer_headers: dict, marshal_headers: dict):
    # Create team
    t_res = client.post(
        "/api/v1/teams",
        json={"name": "Barristers United", "identifier": "BU01"},
        headers=organizer_headers
    )
    team_id = t_res.json()["data"]["id"]

    # Submit valid judge score
    valid_sc = client.post(
        f"/api/v1/rounds/4/judging/{team_id}/scores",
        json={
            "judgeId": "judge-10",
            "judgeName": "Hon. Marcus Cole",
            "teamId": team_id,
            "scores": {
                "logical_structure": 19.0,
                "evidence": 19.0,
                "rebuttal": 18.0,
                "resource_person_questioning": 14.0,
                "presentation_teamwork": 14.0,
                "time": 9.5,
            },
            "comments": "Masterful closing statements."
        },
        headers=marshal_headers
    )
    assert valid_sc.status_code == 200
    assert valid_sc.json()["data"]["totalScore"] == 93.5

    # Submit invalid score (negative)
    neg_sc = client.post(
        f"/api/v1/rounds/4/judging/{team_id}/scores",
        json={
            "judgeId": "judge-10",
            "judgeName": "Hon. Marcus Cole",
            "teamId": team_id,
            "scores": {"logical_structure": -5.0}
        },
        headers=marshal_headers
    )
    assert neg_sc.status_code == 400

    # Submit invalid score (category overflow: logical_structure max is 20)
    over_sc = client.post(
        f"/api/v1/rounds/4/judging/{team_id}/scores",
        json={
            "judgeId": "judge-10",
            "judgeName": "Hon. Marcus Cole",
            "teamId": team_id,
            "scores": {"logical_structure": 25.0}
        },
        headers=marshal_headers
    )
    assert over_sc.status_code == 400


def test_api_resource_person_question_and_case_update(client: TestClient, organizer_headers: dict, marshal_headers: dict):
    # Update case parameters
    case_up = client.put(
        "/api/v1/rounds/4/cases/pair-1",
        json={
            "caseName": "Cybernetics Corp Sabotage Dispute",
            "teamASide": "Prosecution",
            "teamBSide": "Defense",
            "teamAHasCaseFile": True,
            "teamBHasCaseFile": True,
            "resourcePersonName": "Dr. Aris Thorne"
        },
        headers=marshal_headers
    )
    assert case_up.status_code == 200
    assert case_up.json()["data"]["caseName"] == "Cybernetics Corp Sabotage Dispute"
    assert case_up.json()["data"]["resourcePersonName"] == "Dr. Aris Thorne"

    # Create team to ask question
    t_res = client.post(
        "/api/v1/teams",
        json={"name": "Advocate Alliance", "identifier": "AA01"},
        headers=organizer_headers
    )
    team_id = t_res.json()["data"]["id"]

    # Record question
    q_res = client.post(
        "/api/v1/rounds/4/pairs/pair-1/questions",
        json={
            "teamId": team_id,
            "question": "Did the server logs exhibit unauthorized API tokens?",
            "answer": "Yes, bearer token 0x99A was active.",
            "score": 14.0
        },
        headers=marshal_headers
    )
    assert q_res.status_code == 200
    assert q_res.json()["data"]["questions_count"] >= 1


def test_api_leaderboard_and_qualification_checklist(client: TestClient, organizer_headers: dict):
    # Leaderboard
    lead_res = client.get("/api/v1/rounds/4/leaderboard")
    assert lead_res.status_code == 200
    assert isinstance(lead_res.json()["data"], list)

    # Qualification checklist
    qual_res = client.get("/api/v1/rounds/4/qualification")
    assert qual_res.status_code == 200
    qdata = qual_res.json()["data"]
    assert "can_finalize" in qdata
    assert "checklist" in qdata


def test_api_finalization_with_discrepancy_override(client: TestClient, organizer_headers: dict):
    # Call finalize with override_discrepancy
    fin_res = client.post(
        "/api/v1/rounds/4/finalize",
        json={"overrideDiscrepancy": True, "notes": "Authorized by Lead Tournament Director"},
        headers=organizer_headers
    )
    assert fin_res.status_code == 200
    assert fin_res.json()["data"]["finalized"] is True


# ==============================================================================
# 6. SPECIFIC REVIEW TESTS: STEP 13 REQUIREMENTS
# ==============================================================================

def test_legal_battle_score_calculated_only_from_six_official_rubric_categories():
    """Requirement 1: Legal Battle score is calculated only from the six official rubric categories."""
    scores = {
        "logical_structure": 17.5,
        "evidence": 18.0,
        "rebuttal": 16.5,
        "resource_person_questioning": 13.5,
        "presentation_teamwork": 14.0,
        "time": 8.5,
    }
    validated = validate_rubric_scores(scores)
    assert sum(validated.values()) == 88.0
    direct = calculate_legal_battle_score(17.5, 18.0, 16.5, 13.5, 14.0, 8.5)
    assert direct == 88.0

    # Ensure no other criteria are counted
    breakdown = calculate_final_score_breakdown("team-test", panel_score=88.0)
    assert breakdown["final_score"] == 88.0
    assert breakdown["raw_panel_score"] == 88.0
    assert breakdown["weighted_panel_score"] == 88.0


def test_secret_agent_activity_cannot_change_legal_battle_score(db_session: Session, sample_squads):
    """Requirement 2: Secret Agent activity cannot change the Legal Battle score."""
    team = sample_squads[0]

    # Panel score
    panel_score = 85.0

    # Breakdown with no agent record
    bd_without_agent = calculate_final_score_breakdown(
        team_id=team.id,
        panel_score=panel_score,
        agent_record=None,
        black_market_balance=1500.0,
    )

    # Breakdown with verified agent record
    bd_with_agent = calculate_final_score_breakdown(
        team_id=team.id,
        panel_score=panel_score,
        agent_record={"outcome": "correct", "points_awarded": 10.0, "is_verified": True},
        black_market_balance=2500.0,
    )

    assert bd_without_agent["final_score"] == 85.0
    assert bd_with_agent["final_score"] == 85.0
    assert bd_without_agent["final_score"] == bd_with_agent["final_score"]
    assert bd_with_agent["agent_guessing_points"] is None
    assert bd_with_agent["black_market_contribution"] == 0.0

    # Submit agent guess via service and verify overview score unchanged
    round4_service.ensure_round4_pairs(db_session)
    round4_service.submit_judge_score(
        db=db_session,
        team_id=team.id,
        input_data=SubmitJudgeScoreInput(
            judge_id="judge-1",
            judge_name="Judge 1",
            team_id=team.id,
            scores={
                "logical_structure": 20.0,
                "evidence": 20.0,
                "rebuttal": 20.0,
                "resource_person_questioning": 15.0,
                "presentation_teamwork": 15.0,
                "time": 10.0,
            }
        )
    )
    round4_service.submit_agent_guess(
        db=db_session,
        team_id=team.id,
        input_data=SubmitAgentGuessInput(team_id=team.id, outcome="correct", points_awarded=50.0)
    )

    overview = round4_service.get_round4_overview(db_session)
    t_record = next(r for r in overview["records"] if r["team_id"] == team.id)
    assert t_record["panel_score"] == 100.0
    assert t_record["final_score_breakdown"]["final_score"] == 100.0


def test_maximum_legal_battle_score_remains_exactly_100():
    """Requirement 3: Maximum Legal Battle score remains exactly 100."""
    max_score = calculate_legal_battle_score(
        logical_structure=R4_RUBRIC_LOGICAL_STRUCTURE_MAX,  # 20.0
        evidence=R4_RUBRIC_EVIDENCE_MAX,                    # 20.0
        rebuttal=R4_RUBRIC_REBUTTAL_MAX,                    # 20.0
        resource_person_questioning=R4_RUBRIC_RESOURCE_PERSON_MAX,  # 15.0
        presentation_teamwork=R4_RUBRIC_PRESENTATION_TEAMWORK_MAX,  # 15.0
        time=R4_RUBRIC_TIME_MAX,                            # 10.0
    )
    assert max_score == 100.0
    assert R4_RUBRIC_TOTAL_MAX == 100.0

    # Overflows above 100 are rejected
    with pytest.raises(ValueError):
        validate_rubric_scores({
            "logical_structure": 20.0,
            "evidence": 20.0,
            "rebuttal": 20.0,
            "resource_person_questioning": 15.0,
            "presentation_teamwork": 15.0,
            "time": 10.1,
        })


def test_all_8_teams_advance_regardless_of_legal_battle_score(db_session: Session, sample_squads):
    """Requirement 4: All 8 teams advance regardless of Legal Battle score."""
    squads = sample_squads[:8]
    round4_service.auto_pair_round4_teams(db_session, seed=1, confirm=True)

    # Submit scores ranging from 100 down to 10
    scores_desc = [100.0, 90.0, 80.0, 70.0, 60.0, 50.0, 40.0, 10.0]
    for i, t in enumerate(squads):
        s = scores_desc[i]
        round4_service.submit_judge_score(
            db=db_session,
            team_id=t.id,
            input_data=SubmitJudgeScoreInput(
                judge_id="judge-1",
                judge_name="Judge 1",
                team_id=t.id,
                scores={
                    "logical_structure": min(20.0, s * 0.20),
                    "evidence": min(20.0, s * 0.20),
                    "rebuttal": min(20.0, s * 0.20),
                    "resource_person_questioning": min(15.0, s * 0.15),
                    "presentation_teamwork": min(15.0, s * 0.15),
                    "time": min(10.0, s * 0.10),
                }
            )
        )

    for i in range(1, 5):
        for st in ["hearing_1", "file_exchange", "hearing_2"]:
            round4_service.update_stage_timing(db_session, f"pair-{i}", st, "completed", 600)

    res = round4_service.finalize_round4(db_session, actor=None, override_discrepancy=True)
    assert res["finalized"] is True
    assert len(res["advancing_team_ids"]) == 8

    # Check that even lowest scoring squad advanced
    lowest_team = squads[7]
    quals = db_session.query(RoundQualification).filter(
        RoundQualification.round_number == 4,
        RoundQualification.team_id == lowest_team.id
    ).first()
    assert quals is not None
    assert quals.is_advancing is True
    assert quals.status == "Finalized Qualified"


def test_round4_finalization_does_not_perform_finale_agent_guess_scoring(db_session: Session, sample_squads):
    """Requirement 5: Round 4 finalization does not perform Finale agent-guess scoring."""
    squads = sample_squads[:8]
    round4_service.auto_pair_round4_teams(db_session, seed=1, confirm=True)

    # Submit judge scores of 80.0 to all squads
    for t in squads:
        round4_service.submit_judge_score(
            db=db_session,
            team_id=t.id,
            input_data=SubmitJudgeScoreInput(
                judge_id="judge-1",
                judge_name="Judge 1",
                team_id=t.id,
                scores={
                    "logical_structure": 16.0,
                    "evidence": 16.0,
                    "rebuttal": 16.0,
                    "resource_person_questioning": 12.0,
                    "presentation_teamwork": 12.0,
                    "time": 8.0,
                }
            )
        )
        # Add an agent guess record of +10 points
        round4_service.submit_agent_guess(
            db=db_session,
            team_id=t.id,
            input_data=SubmitAgentGuessInput(team_id=t.id, outcome="correct", points_awarded=10.0)
        )

    for i in range(1, 5):
        for st in ["hearing_1", "file_exchange", "hearing_2"]:
            round4_service.update_stage_timing(db_session, f"pair-{i}", st, "completed", 600)

    res = round4_service.finalize_round4(db_session, actor=None, override_discrepancy=True)
    assert res["finalized"] is True

    # The snapshot stored in RoundQualification must be EXACTLY 80.0 (the pure Legal Battle panel score)
    # NOT 90.0 (which would have been 80 + 10 agent points)
    for t in squads:
        qual = db_session.query(RoundQualification).filter(
            RoundQualification.round_number == 4,
            RoundQualification.team_id == t.id
        ).first()
        assert qual.score_snapshot == 80.0