import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.core.constants import (
    R4_FINALISTS, R4_PAIRS, R4_RUBRIC_LIMITS,
    AGENT_CORRECT_GUESS, AGENT_WRONG_GUESS, AGENT_NO_GUESS
)
from app.models.core import Team, TeamStatus
from app.models.round4 import Round4ConfigModel, Round4PairModel, Round4JudgeScoreModel, Round4AgentGuessModel
from app.models.progression import RoundQualification
from app.models.round_models import RoundState
from app.services import round4_service
from app.schemas.rounds.round4 import (
    SubmitJudgeScoreInput, CorrectJudgeScoreInput,
    SubmitAgentGuessesInput, AgentGuessItemInput,
    UpdateStageInput, FinalizeRound4Input
)
from app.scoring.round4_scoring import (
    calculate_legal_battle_score, validate_rubric_scores,
    calculate_panel_score, calculate_final_score_breakdown,
    calculate_agent_guess_points, process_round4_standings
)


@pytest.fixture
def four_finalists(db_session: Session):
    teams = []
    for i in range(1, 5):
        t = Team(
            id=f"team-finalist-{i}",
            name=f"Finalist Squad {i}",
            team_number=i,
            status=TeamStatus.ACTIVE,
            current_round=4,
            is_qualified_for_next_round=False,
        )
        db_session.add(t)
        teams.append(t)
    db_session.commit()
    for t in teams:
        db_session.refresh(t)
    return teams


def test_rubric_100_point_limits():
    """Verify official 6-category rubric totaling 100 points."""
    assert sum(R4_RUBRIC_LIMITS.values()) == 100.0
    assert R4_RUBRIC_LIMITS["logical_structure"] == 20.0
    assert R4_RUBRIC_LIMITS["evidence"] == 20.0
    assert R4_RUBRIC_LIMITS["rebuttal"] == 20.0
    assert R4_RUBRIC_LIMITS["resource_person_questioning"] == 15.0
    assert R4_RUBRIC_LIMITS["presentation_teamwork"] == 15.0
    assert R4_RUBRIC_LIMITS["time"] == 10.0

    score = calculate_legal_battle_score(
        logical_structure=20.0,
        evidence=20.0,
        rebuttal=20.0,
        resource_person_questioning=15.0,
        presentation_teamwork=15.0,
        time=10.0
    )
    assert score == 100.0

    # Overflows must fail
    with pytest.raises(ValueError):
        validate_rubric_scores({"logical_structure": 21.0})
    with pytest.raises(ValueError):
        validate_rubric_scores({"time": 11.0})


def test_auto_pairing_4_teams_into_2_matchups(db_session: Session, four_finalists):
    """Seed 1 vs Seed 4 (Matchup 1) and Seed 2 vs Seed 3 (Matchup 2)."""
    pairs = round4_service.auto_pair_round4_teams(db_session, confirm=True)
    assert len(pairs) == 2
    assert pairs[0].pair_number == 1
    assert pairs[0].team_a_id == "team-finalist-1"
    assert pairs[0].team_b_id == "team-finalist-4"
    assert pairs[1].pair_number == 2
    assert pairs[1].team_a_id == "team-finalist-2"
    assert pairs[1].team_b_id == "team-finalist-3"


def test_judge_score_locking_and_organizer_correction(db_session: Session, four_finalists):
    """Verify score submission, locking, rejection when locked, and organizer correction."""
    team = four_finalists[0]

    # 1. Submit score
    sc = round4_service.submit_judge_score(
        db=db_session,
        team_id=team.id,
        input_data=SubmitJudgeScoreInput(
            judge_id="judge-1",
            judge_name="Justice Evelyn",
            team_id=team.id,
            scores={
                "logical_structure": 18.0,
                "evidence": 19.0,
                "rebuttal": 17.0,
                "resource_person_questioning": 14.0,
                "presentation_teamwork": 13.0,
                "time": 9.0,
            },
            is_locked=False
        )
    )
    assert sc.total_score == 90.0
    assert sc.is_locked is False

    # 2. Lock score
    sc_locked = round4_service.lock_judge_score(db_session, sc.id)
    assert sc_locked.is_locked is True
    assert sc_locked.locked_at is not None

    # 3. Attempt to submit new score while locked should raise 400
    with pytest.raises(Exception):
        round4_service.submit_judge_score(
            db=db_session,
            team_id=team.id,
            input_data=SubmitJudgeScoreInput(
                judge_id="judge-1",
                judge_name="Justice Evelyn",
                team_id=team.id,
                scores={"logical_structure": 15.0}
            ),
            actor=None
        )

    # 4. Organizer correction with audit trail
    sc_corrected = round4_service.correct_judge_score(
        db=db_session,
        score_id=sc.id,
        input_data=CorrectJudgeScoreInput(
            scores={
                "logical_structure": 20.0,
                "evidence": 20.0,
                "rebuttal": 18.0,
                "resource_person_questioning": 15.0,
                "presentation_teamwork": 14.0,
                "time": 10.0,
            },
            correction_notes="Organizer rectified clerical error in rebuttal rubric scoring."
        ),
        actor=None
    )
    assert sc_corrected.total_score == 97.0
    assert sc_corrected.correction_notes == "Organizer rectified clerical error in rebuttal rubric scoring."


def test_timekeeper_stage_logging(db_session: Session):
    """Verify timekeeper logging of duration, notes, and violations."""
    round4_service.ensure_round4_pairs(db_session, num_pairs=2)
    round4_service.update_stage_timing(
        db=db_session,
        pair_id="pair-1",
        stage_id="hearing_1",
        status_val="completed",
        duration=900,
        notes="Arguments delivered cleanly.",
        timekeeper_name="Timekeeper Alice",
        time_violations_notes="10s overtime on closing statement.",
        penalty_seconds=10
    )

    overview = round4_service.get_round4_overview(db_session)
    p1 = next(p for p in overview["pairs"] if p["id"] == "pair-1")
    h1 = p1["stages"]["hearing_1"]
    assert h1["status"] == "completed"
    assert h1["timekeeper_name"] == "Timekeeper Alice"
    assert h1["actual_duration_seconds"] == 900
    assert h1["penalty_seconds"] == 10


def test_secret_agent_final_guessing_scoring(db_session: Session, four_finalists):
    """Verify 1-5 guesses with +30 for correct and -20 for incorrect."""
    team = four_finalists[0]

    # Test calculation utility
    calc = calculate_agent_guess_points([
        {"agent_id": "suspect-1", "outcome": "correct"},
        {"agent_id": "suspect-2", "outcome": "incorrect"},
        {"agent_id": "suspect-3", "outcome": "correct"},
    ])
    assert calc["total_guesses"] == 3
    assert calc["correct_guesses"] == 2
    assert calc["wrong_guesses"] == 1
    # 2 * 30 + 1 * (-20) = 40
    assert calc["points_awarded"] == 40.0

    # Submit via service
    ag = round4_service.submit_team_agent_guesses(
        db=db_session,
        team_id=team.id,
        input_data=SubmitAgentGuessesInput(
            team_id=team.id,
            guesses=[
                AgentGuessItemInput(agent_id="suspect-1", outcome="correct"),
                AgentGuessItemInput(agent_id="suspect-2", outcome="incorrect"),
            ],
            notes="Deduction based on card placement patterns in Round 2."
        )
    )
    assert ag.total_guesses == 2
    assert ag.correct_guesses == 1
    assert ag.wrong_guesses == 1
    assert ag.points_awarded == 10.0 # +30 - 20 = 10.0


def test_multi_round_composite_final_score():
    """
    Final Score = R1 Points + R2 Cabo + Agent Task Credits + R3 Balance + R4 Legal Score + Agent Guess Points
    """
    breakdown = calculate_final_score_breakdown(
        team_id="team-finalist-1",
        r1_points=16.0,          # 1st place in R1
        r2_cabo=65.0,            # Raw Cabo score
        agent_task_credits=100.0,# 2 verified tasks * 50
        r3_balance=850.0,        # Remaining Black Market balance
        r4_legal_score=92.5,     # Moot court panel score
        agent_guess_points=40.0  # +30 +30 -20
    )

    expected = 16.0 + 65.0 + 100.0 + 850.0 + 92.5 + 40.0 # = 1163.5
    assert breakdown["final_score"] == round(expected, 2)
    assert breakdown["r1_points"] == 16.0
    assert breakdown["r2_cabo"] == 65.0
    assert breakdown["agent_task_credits"] == 100.0
    assert breakdown["r3_balance"] == 850.0
    assert breakdown["r4_legal_score"] == 92.5
    assert breakdown["agent_guess_points"] == 40.0
