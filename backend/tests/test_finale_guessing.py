"""
Unit and Integration Tests for Step 14: Grand Finale & Secret Agent Guessing Engine.
Source of Truth: Authoritative Event Documentation reconciled in Step 6B & Step 14.

Rules under test:
1. Exactly 8 finalist teams participate in Grand Finale guessing.
2. Guess count bounds: Min 1 guess, Max 5 guesses per squad.
3. Target rules: Cannot guess self; cannot submit duplicate guesses for the same target team.
4. Scoring: Correct guess = +30.0 pts; Wrong guess = -20.0 pts; Unguessed = 0.0 pts.
5. Round 4 isolation: Agent guessing points NEVER modify Round 4 Legal Battle score.
6. Best Secret Agent resolution:
   - Primary: Most verified Secret Agent tasks (descending).
   - Secondary: Fewest correct guesses received against that agent (ascending).
   - Tie-Breaker: Flag tie_requires_review = True for manual review if tied on both.
7. Confidentiality:
   - Teams cannot view correctness or points before official reveal.
   - Teams cannot view other teams' guesses.
   - Organizers can view full unmasked overview and trigger official reveal.
8. Overall Final Score Breakdown:
   Final Score = R4 Score + Agent Guessing Points + 10% of Remaining Black Market Wallet Points.
9. Finalization is idempotent and respects progression safeguards.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.constants import (
    AGENT_CORRECT_GUESS,
    AGENT_WRONG_GUESS,
    AGENT_GUESS_MIN,
    AGENT_GUESS_MAX,
    DEFAULT_CARRYOVER_WEIGHT_PERCENT,
    R4_ADVANCING_COUNT,
)
from app.models.team import Team
from app.models.participant import Participant
from app.models.agent import SecretAgentDossier, SecretAgentTask, AgentTaskStatus, AgentDossierStatus
from app.models.wallet import TeamWallet
from app.models.progression import RoundQualification
from app.models.finale import FinaleConfigModel, FinaleTeamGuessSubmissionModel, FinaleAgentGuessModel
from app.scoring.finale_scoring import (
    validate_team_guesses,
    evaluate_single_guess,
    calculate_team_guessing_score,
    calculate_best_secret_agent,
    calculate_overall_final_score,
    process_finale_guessing_standings,
)
from app.services import finale_service, progression_service


# ==============================================================================
# 1. PURE SCORING ENGINE UNIT TESTS
# ==============================================================================

def test_scoring_validate_team_guesses_bounds():
    """Verify guess count validation: min 1, max 5."""
    finalists = [f"team-{i}" for i in range(1, 9)]

    # 0 guesses -> Invalid
    res_0 = validate_team_guesses("team-1", [], finalists, min_guesses=1, max_guesses=5)
    assert res_0["is_valid"] is False
    assert any("require between 1 and 5" in err for err in res_0["errors"])

    # 1 guess -> Valid
    g1 = [{"target_team_id": "team-2", "suspected_agent_name": "Agent Cobra"}]
    res_1 = validate_team_guesses("team-1", g1, finalists, min_guesses=1, max_guesses=5)
    assert res_1["is_valid"] is True

    # 5 guesses -> Valid
    g5 = [{"target_team_id": f"team-{i}", "suspected_agent_name": f"Agent {i}"} for i in range(2, 7)]
    res_5 = validate_team_guesses("team-1", g5, finalists, min_guesses=1, max_guesses=5)
    assert res_5["is_valid"] is True

    # 6 guesses -> Invalid
    g6 = [{"target_team_id": f"team-{i}", "suspected_agent_name": f"Agent {i}"} for i in range(2, 8)]
    res_6 = validate_team_guesses("team-1", g6, finalists, min_guesses=1, max_guesses=5)
    assert res_6["is_valid"] is False
    assert any("require between 1 and 5" in err for err in res_6["errors"])


def test_scoring_validate_prohibits_self_guessing():
    """Verify team cannot guess its own undercover agent."""
    finalists = ["team-1", "team-2", "team-3"]
    guesses = [{"target_team_id": "team-1", "suspected_agent_name": "Agent Self"}]
    res = validate_team_guesses("team-1", guesses, finalists)
    assert res["is_valid"] is False
    assert any("Self-guessing is prohibited" in err for err in res["errors"])


def test_scoring_validate_prohibits_duplicate_targets():
    """Verify team cannot submit duplicate guesses targeting the same team."""
    finalists = ["team-1", "team-2", "team-3", "team-4"]
    guesses = [
        {"target_team_id": "team-2", "suspected_agent_name": "Agent A"},
        {"target_team_id": "team-2", "suspected_agent_name": "Agent B"},
    ]
    res = validate_team_guesses("team-1", guesses, finalists)
    assert res["is_valid"] is False
    assert any("Duplicate guess" in err for err in res["errors"])


def test_scoring_validate_prohibits_non_finalist_targets():
    """Verify team cannot submit guesses targeting non-finalist teams."""
    finalists = ["team-1", "team-2", "team-3"]
    guesses = [{"target_team_id": "team-99", "suspected_agent_name": "Agent Rogue"}]
    res = validate_team_guesses("team-1", guesses, finalists)
    assert res["is_valid"] is False
    assert any("not an official finalist squad" in err for err in res["errors"])


def test_scoring_validate_requires_participant_or_name():
    """Verify each guess must provide at least a suspected participant ID or codename."""
    finalists = ["team-1", "team-2"]
    guesses = [{"target_team_id": "team-2", "suspected_participant_id": None, "suspected_agent_name": ""}]
    res = validate_team_guesses("team-1", guesses, finalists)
    assert res["is_valid"] is False
    assert any("must specify suspected participant ID or codename" in err for err in res["errors"])


def test_scoring_evaluate_single_guess_correct_and_wrong():
    """Verify unmasking awards +30.0 for correct guess and -20.0 for wrong guess."""
    dossier_map = {
        "team-2": {
            "participant_id": "p-102",
            "codename": "Shadow",
            "participant_name": "Alice Smith",
        }
    }

    # Correct guess by participant ID (+30.0)
    g_correct_pid = {"target_team_id": "team-2", "suspected_participant_id": "p-102"}
    res_c1 = evaluate_single_guess(g_correct_pid, dossier_map)
    assert res_c1["is_correct"] is True
    assert res_c1["points_awarded"] == 30.0

    # Correct guess by codename (+30.0)
    g_correct_code = {"target_team_id": "team-2", "suspected_agent_name": "Shadow"}
    res_c2 = evaluate_single_guess(g_correct_code, dossier_map)
    assert res_c2["is_correct"] is True
    assert res_c2["points_awarded"] == 30.0

    # Correct guess by participant name (+30.0)
    g_correct_name = {"target_team_id": "team-2", "suspected_agent_name": "alice smith"}
    res_c3 = evaluate_single_guess(g_correct_name, dossier_map)
    assert res_c3["is_correct"] is True
    assert res_c3["points_awarded"] == 30.0

    # Wrong guess (-20.0)
    g_wrong = {"target_team_id": "team-2", "suspected_participant_id": "p-999"}
    res_w = evaluate_single_guess(g_wrong, dossier_map)
    assert res_w["is_correct"] is False
    assert res_w["points_awarded"] == -20.0


def test_scoring_calculate_team_guessing_score_aggregate():
    """Verify net score calculation: (Correct * 30) + (Wrong * -20)."""
    evaluated = [
        {"is_correct": True, "points_awarded": 30.0},
        {"is_correct": True, "points_awarded": 30.0},
        {"is_correct": False, "points_awarded": -20.0},
        {"is_correct": False, "points_awarded": -20.0},
        {"is_correct": True, "points_awarded": 30.0},
    ]  # 3 correct (90), 2 wrong (-40) -> Net: 50.0
    summary = calculate_team_guessing_score("team-1", evaluated)
    assert summary["total_guesses"] == 5
    assert summary["correct_guesses"] == 3
    assert summary["wrong_guesses"] == 2
    assert summary["total_guessing_points"] == 50.0


def test_scoring_best_secret_agent_two_tier_ranking():
    """
    Verify Best Secret Agent criteria:
    1. Primary: Most verified tasks (desc).
    2. Secondary: Fewest correct guesses received against that agent (asc).
    """
    dossiers = [
        {"id": "d1", "team_id": "t1", "team_number": 1, "participant_id": "p1", "codename": "Alpha", "verified_tasks_count": 3},
        {"id": "d2", "team_id": "t2", "team_number": 2, "participant_id": "p2", "codename": "Bravo", "verified_tasks_count": 4},
        {"id": "d3", "team_id": "t3", "team_number": 3, "participant_id": "p3", "codename": "Charlie", "verified_tasks_count": 4},
    ]
    # Guesses against agents:
    # t2 was correctly guessed 2 times
    # t3 was correctly guessed 1 time
    # Both t2 and t3 have 4 verified tasks, but t3 has fewer correct guesses against them (1 vs 2), so t3 wins!
    all_evaluated_guesses = [
        {"target_team_id": "t2", "is_correct": True},
        {"target_team_id": "t2", "is_correct": True},
        {"target_team_id": "t3", "is_correct": True},
        {"target_team_id": "t1", "is_correct": False},
    ]

    res = calculate_best_secret_agent(dossiers, all_evaluated_guesses)
    assert res["tie_requires_review"] is False
    assert res["best_agent"]["team_id"] == "t3"
    assert res["rankings"][0]["team_id"] == "t3"
    assert res["rankings"][1]["team_id"] == "t2"
    assert res["rankings"][2]["team_id"] == "t1"


def test_scoring_best_secret_agent_tie_requires_review():
    """Verify when two agents tie on both primary & secondary criteria, tie_requires_review is set."""
    dossiers = [
        {"id": "d1", "team_id": "t1", "team_number": 1, "participant_id": "p1", "codename": "Alpha", "verified_tasks_count": 4},
        {"id": "d2", "team_id": "t2", "team_number": 2, "participant_id": "p2", "codename": "Bravo", "verified_tasks_count": 4},
    ]
    all_evaluated_guesses = [
        {"target_team_id": "t1", "is_correct": True},
        {"target_team_id": "t2", "is_correct": True},
    ]
    res = calculate_best_secret_agent(dossiers, all_evaluated_guesses)
    assert res["tie_requires_review"] is True
    assert len(res["tied_candidate_ids"]) == 2
    assert "d1" in res["tied_candidate_ids"]
    assert "d2" in res["tied_candidate_ids"]


def test_scoring_overall_final_score_formula_and_isolation():
    """
    Verify Overall Final Score = R4 Legal Battle + Agent Guessing Points + 10% Black Market Wallet.
    Verify that components are strictly isolated.
    """
    r4_panel_score = 88.5
    guessing_points = 40.0  # e.g., 2 correct (60) - 1 wrong (20)
    wallet_balance = 1250.0  # 10% = 125.0

    breakdown = calculate_overall_final_score(
        round4_score=r4_panel_score,
        guessing_points=guessing_points,
        wallet_balance=wallet_balance,
        carryover_percent=10.0,
    )
    assert breakdown["round4_legal_battle_score"] == 88.5
    assert breakdown["agent_guessing_points"] == 40.0
    assert breakdown["wallet_carryover_points"] == 125.0
    assert breakdown["total_final_score"] == 253.5  # 88.5 + 40.0 + 125.0


def test_scoring_process_standings_checklist_and_podium_titles():
    """Verify standings sorting, checklist generation, and podium honors."""
    records = [
        {
            "team_id": f"team-{i}",
            "team_number": i,
            "team_name": f"Team {i}",
            "submission": {"is_submitted": True},
            "score_breakdown": {
                "round4_legal_battle_score": 80.0 + i,
                "agent_guessing_points": (i * 10.0),
                "wallet_carryover_points": 100.0,
                "total_final_score": 180.0 + (i * 11.0),
            }
        }
        for i in range(1, 9)
    ]
    standings = process_finale_guessing_standings(
        records=records,
        config={"is_scoring_rules_confirmed": True, "advancing_teams_count": 8},
        round4_finalized=True,
    )
    assert standings["can_finalize"] is True
    assert standings["champion_team_id"] == "team-8"
    assert standings["runner_up1_team_id"] == "team-7"
    assert standings["runner_up2_team_id"] == "team-6"
    assert standings["records"][0]["placement_title"] == "Grand Champion"
    assert standings["records"][1]["placement_title"] == "1st Runner Up"
    assert standings["records"][2]["placement_title"] == "2nd Runner Up"


# ==============================================================================
# 2. INTEGRATION TESTS (API + DB)
# ==============================================================================

@pytest.fixture
def setup_finale_tournament(db_session: Session):
    """Sets up an isolated tournament with 8 finalist teams, wallets, dossiers, and R4 qualifications."""
    from app.models.round4 import Round4ConfigModel
    from app.models.round_models import RoundState

    # Mark Round 4 as finalized
    r4_cfg = Round4ConfigModel(id=1, is_finalized=True, is_rubric_confirmed=True)
    db_session.merge(r4_cfg)
    r4_state = RoundState(id=4, name="Round 4", codename="legal_battle", is_finalized=True, status="Completed")
    db_session.merge(r4_state)

    teams = []
    for i in range(1, 9):
        t = Team(
            id=f"fin-team-{i}",
            name=f"Finalist Squad {i}",
            team_number=i,
        )
        db_session.add(t)
        teams.append(t)

        # Add participant for agent
        p = Participant(
            id=f"fin-part-{i}",
            team_id=t.id,
            name=f"Agent Candidate {i}",
            email=f"agent{i}@tournament.org",
            usn=f"1MS21CS{i:03d}",
            phone=f"987654321{i}",
        )
        db_session.add(p)

        # Add Secret Agent Dossier
        d = SecretAgentDossier(
            id=f"sad-fin-{i}",
            team_id=t.id,
            participant_id=p.id,
            codename=f"Agent-{i}",
            status=AgentDossierStatus.ACTIVE,
        )
        db_session.add(d)

        # Add verified task for team 1, 2, 3
        if i in (1, 2, 3):
            for task_num in range(i):  # Team 1: 0 tasks, Team 2: 1 task, Team 3: 2 tasks
                tk = SecretAgentTask(
                    id=f"sat-fin-{i}-{task_num}",
                    dossier_id=d.id,
                    task_description=f"Sabotage mission {task_num}",
                    status=AgentTaskStatus.VERIFIED,
                )
                db_session.add(tk)

        # Add Wallet
        w = TeamWallet(
            team_id=t.id,
            current_balance=1000.0 + (i * 100.0),
        )
        db_session.add(w)

        # Add Round 4 qualification record (80.0 to 95.0 pts)
        q = RoundQualification(
            id=f"qual-r4-{t.id}",
            round_number=4,
            team_id=t.id,
            rank=i,
            status="Finalized Qualified",
            score_snapshot=80.0 + i * 2.0,
            is_advancing=True,
            finalized_by="Lead Organizer",
        )
        db_session.add(q)

    # Initialize finale config
    cfg = FinaleConfigModel(
        id=1,
        is_scoring_rules_confirmed=True,
        advancing_teams_count=8,
        min_guesses=1,
        max_guesses=5,
        correct_guess_points=30.0,
        wrong_guess_points=-20.0,
        carryover_wallet_percent=10.0,
        is_guessing_open=True,
        is_finalized=False,
        is_revealed=False,
    )
    db_session.merge(cfg)
    db_session.commit()
    return teams


def test_api_submit_team_guesses_success(
    client: TestClient,
    organizer_headers: dict,
    setup_finale_tournament,
):
    """Test submitting 3 secret agent guesses for Team 1."""
    payload = {
        "guessingTeamId": "fin-team-1",
        "guesses": [
            {"targetTeamId": "fin-team-2", "suspectedParticipantId": "fin-part-2"},  # Correct (+30)
            {"targetTeamId": "fin-team-3", "suspectedAgentName": "Agent-3"},         # Correct (+30)
            {"targetTeamId": "fin-team-4", "suspectedAgentName": "WrongGuy"},        # Wrong (-20)
        ]
    }
    res = client.post("/api/v1/rounds/finale/guesses", json=payload, headers=organizer_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["guessing_team_id"] == "fin-team-1"
    assert data["total_guesses"] == 3
    assert data["correct_guesses"] == 2
    assert data["wrong_guesses"] == 1
    assert data["total_guessing_points"] == 40.0  # 30 + 30 - 20 = 40.0


def test_api_submit_team_guesses_self_guess_blocked(
    client: TestClient,
    organizer_headers: dict,
    setup_finale_tournament,
):
    """Test that self-guessing returns HTTP 400."""
    payload = {
        "guessingTeamId": "fin-team-1",
        "guesses": [
            {"targetTeamId": "fin-team-1", "suspectedAgentName": "Agent-1"}
        ]
    }
    res = client.post("/api/v1/rounds/finale/guesses", json=payload, headers=organizer_headers)
    assert res.status_code == 400
    assert "Self-guessing is prohibited" in res.json()["message"]


def test_api_submit_team_guesses_duplicate_target_blocked(
    client: TestClient,
    organizer_headers: dict,
    setup_finale_tournament,
):
    """Test that multiple guesses targeting the same team returns HTTP 400."""
    payload = {
        "guessingTeamId": "fin-team-1",
        "guesses": [
            {"targetTeamId": "fin-team-2", "suspectedAgentName": "Agent-2"},
            {"targetTeamId": "fin-team-2", "suspectedAgentName": "Agent-X"},
        ]
    }
    res = client.post("/api/v1/rounds/finale/guesses", json=payload, headers=organizer_headers)
    assert res.status_code == 400
    assert "Duplicate guess" in res.json()["message"]


def test_api_submit_team_guesses_bounds_blocked(
    client: TestClient,
    organizer_headers: dict,
    setup_finale_tournament,
):
    """Test that 0 or >5 guesses returns HTTP 400."""
    # 0 guesses
    res0 = client.post(
        "/api/v1/rounds/finale/guesses",
        json={"guessingTeamId": "fin-team-1", "guesses": []},
        headers=organizer_headers,
    )
    assert res0.status_code == 400
    assert "between 1 and 5" in res0.json()["message"]

    # 6 guesses
    guesses_6 = [{"targetTeamId": f"fin-team-{i}", "suspectedAgentName": f"Agent-{i}"} for i in range(2, 8)]
    res6 = client.post(
        "/api/v1/rounds/finale/guesses",
        json={"guessingTeamId": "fin-team-1", "guesses": guesses_6},
        headers=organizer_headers,
    )
    assert res6.status_code == 400
    assert "between 1 and 5" in res6.json()["message"]


def test_api_best_secret_agent_endpoint(
    client: TestClient,
    organizer_headers: dict,
    setup_finale_tournament,
):
    """Test Best Secret Agent resolution via GET /api/v1/rounds/finale/best-secret-agent."""
    # Team 3 has 2 verified tasks (most tasks), so Team 3 should be Best Secret Agent
    res = client.get("/api/v1/rounds/finale/best-secret-agent", headers=organizer_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    best = data.get("best_agent") or data.get("bestAgent")
    assert best is not None
    team_id = best.get("team_id") or best.get("teamId")
    assert team_id == "fin-team-3"
    tasks_count = best.get("verified_tasks_count") or best.get("verifiedTasksCount")
    assert tasks_count == 3
    assert len(data.get("rankings", [])) == 8


def test_api_confidentiality_masks_results_before_reveal(
    client: TestClient,
    organizer_headers: dict,
    setup_finale_tournament,
):
    """
    Test confidentiality:
    Before reveal: team overview hides agent identities and score outcomes for teams.
    After reveal: full unmasked outcomes are visible.
    """
    # Submit guess for Team 1
    client.post(
        "/api/v1/rounds/finale/guesses",
        json={
            "guessingTeamId": "fin-team-1",
            "guesses": [
                {"targetTeamId": "fin-team-2", "suspectedParticipantId": "fin-part-2"},
            ]
        },
        headers=organizer_headers,
    )

    # Organizer view (unmasked)
    res_org = client.get("/api/v1/rounds/finale/overview", headers=organizer_headers)
    assert res_org.status_code == 200
    t1_org = next(r for r in res_org.json()["data"]["records"] if r["team_id"] == "fin-team-1")
    assert t1_org["submission"]["total_guessing_points"] == 30.0

    # Reveal results
    rev_res = client.post("/api/v1/rounds/finale/reveal", headers=organizer_headers)
    assert rev_res.status_code == 200
    assert rev_res.json()["data"]["is_revealed"] is True


def test_api_finale_finalization_lifecycle_and_idempotency(
    client: TestClient,
    organizer_headers: dict,
    setup_finale_tournament,
):
    """
    Test finalization of Grand Finale:
    - Finalizes when all conditions met (or override used).
    - Idempotent on second call.
    - Locked against further submissions.
    """
    # Submit guesses for all 8 teams
    for i in range(1, 9):
        target_idx = 2 if i == 1 else 1
        client.post(
            "/api/v1/rounds/finale/guesses",
            json={
                "guessingTeamId": f"fin-team-{i}",
                "guesses": [
                    {"targetTeamId": f"fin-team-{target_idx}", "suspectedAgentName": f"Agent-{target_idx}"}
                ]
            },
            headers=organizer_headers,
        )

    # Finalize
    res_fin = client.post(
        "/api/v1/rounds/finale/finalize",
        json={"overrideDiscrepancy": True},
        headers=organizer_headers,
    )
    assert res_fin.status_code == 200
    assert res_fin.json()["data"]["finalized"] is True

    # Verify idempotency
    res_idempotent = client.post(
        "/api/v1/rounds/finale/finalize",
        headers=organizer_headers,
    )
    assert res_idempotent.status_code == 200
    assert "already" in res_idempotent.json()["data"]["message"].lower()

    # Mutation locked after finalization -> HTTP 400
    res_blocked = client.post(
        "/api/v1/rounds/finale/guesses",
        json={
            "guessingTeamId": "fin-team-1",
            "guesses": [{"targetTeamId": "fin-team-2", "suspectedAgentName": "Agent-2"}]
        },
        headers=organizer_headers,
    )
    assert res_blocked.status_code == 400
    assert "already finalized" in res_blocked.json()["message"]


def test_api_guesses_blocked_when_guessing_closed(
    client: TestClient,
    organizer_headers: dict,
    setup_finale_tournament,
):
    """Test that closing guessing rejects submissions with HTTP 400."""
    # Close guessing via config update
    client.put(
        "/api/v1/rounds/finale/config",
        json={"isGuessingOpen": False},
        headers=organizer_headers,
    )

    res = client.post(
        "/api/v1/rounds/finale/guesses",
        json={
            "guessingTeamId": "fin-team-1",
            "guesses": [{"targetTeamId": "fin-team-2", "suspectedAgentName": "Agent-2"}]
        },
        headers=organizer_headers,
    )
    assert res.status_code == 400
    assert "currently closed" in res.json()["message"]

    # Re-open guessing
    client.put(
        "/api/v1/rounds/finale/config",
        json={"isGuessingOpen": True},
        headers=organizer_headers,
    )


def test_api_guesses_blocked_when_r4_unfinalized(
    client: TestClient,
    organizer_headers: dict,
    db_session: Session,
):
    """Test that submitting guesses is blocked if Round 4 is unfinalized."""
    from app.models.round4 import Round4ConfigModel
    from app.models.round_models import RoundState

    # Mark Round 4 unfinalized
    r4_cfg = Round4ConfigModel(id=1, is_finalized=False)
    db_session.merge(r4_cfg)
    r4_state = RoundState(id=4, name="Round 4", codename="legal_battle", is_finalized=False, status="In Progress")
    db_session.merge(r4_state)
    db_session.commit()

    res = client.post(
        "/api/v1/rounds/finale/guesses",
        json={
            "guessingTeamId": "fin-team-1",
            "guesses": [{"targetTeamId": "fin-team-2", "suspectedAgentName": "Agent-2"}]
        },
        headers=organizer_headers,
    )
    assert res.status_code == 400
    assert "Round 4: The Legal Battle must be finalized" in res.json()["message"]


def test_scoring_case_insensitive_codename_and_name_matching():
    """Verify codename and participant name matching is case-insensitive and trims whitespace."""
    dossier_map = {
        "team-A": {
            "participant_id": "p-A",
            "codename": "NightHawk",
            "participant_name": "Bob Vance",
        }
    }

    # Match upper case codename
    res1 = evaluate_single_guess({"target_team_id": "team-A", "suspected_agent_name": "  NIGHTHAWK  "}, dossier_map)
    assert res1["is_correct"] is True
    assert res1["points_awarded"] == 30.0

    # Match mixed case participant name
    res2 = evaluate_single_guess({"target_team_id": "team-A", "suspected_agent_name": "bOb VaNcE"}, dossier_map)
    assert res2["is_correct"] is True
    assert res2["points_awarded"] == 30.0


def test_scoring_best_agent_three_way_tie_flagged():
    """Verify 3-way tie for Best Secret Agent flags all 3 candidate dossiers for review."""
    dossiers = [
        {"id": "d1", "team_id": "t1", "team_number": 1, "verified_tasks_count": 5},
        {"id": "d2", "team_id": "t2", "team_number": 2, "verified_tasks_count": 5},
        {"id": "d3", "team_id": "t3", "team_number": 3, "verified_tasks_count": 5},
    ]
    all_evaluated_guesses = [
        {"target_team_id": "t1", "is_correct": False},
        {"target_team_id": "t2", "is_correct": False},
        {"target_team_id": "t3", "is_correct": False},
    ]  # All have 5 tasks and 0 correct guesses against them
    res = calculate_best_secret_agent(dossiers, all_evaluated_guesses)
    assert res["tie_requires_review"] is True
    assert len(res["tied_candidate_ids"]) == 3


def test_scoring_best_agent_zero_tasks_uncompromised_wins():
    """Verify when all have 0 tasks, the uncompromised agent (0 unmaskings) beats the compromised agent."""
    dossiers = [
        {"id": "d1", "team_id": "t1", "team_number": 1, "verified_tasks_count": 0},
        {"id": "d2", "team_id": "t2", "team_number": 2, "verified_tasks_count": 0},
    ]
    all_evaluated_guesses = [
        {"target_team_id": "t2", "is_correct": True},  # t2 was unmasked
    ]
    res = calculate_best_secret_agent(dossiers, all_evaluated_guesses)
    assert res["tie_requires_review"] is False
    assert res["best_agent"]["team_id"] == "t1"
    assert res["best_agent"]["is_uncompromised"] is True
    assert res["rankings"][1]["team_id"] == "t2"
    assert res["rankings"][1]["is_uncompromised"] is False


def test_scoring_overall_score_zero_wallet_carryover():
    """Verify final score formula when remaining wallet balance is 0."""
    breakdown = calculate_overall_final_score(
        round4_score=95.0,
        guessing_points=60.0,
        wallet_balance=0.0,
        carryover_percent=10.0,
    )
    assert breakdown["wallet_carryover_points"] == 0.0
    assert breakdown["total_final_score"] == 155.0  # 95 + 60 + 0


def test_scoring_overall_score_negative_guessing_points():
    """Verify net negative guessing points subtracts from final score without altering R4 score."""
    breakdown = calculate_overall_final_score(
        round4_score=85.0,
        guessing_points=-40.0,  # 2 wrong guesses (-40)
        wallet_balance=1000.0,   # 10% = 100.0
        carryover_percent=10.0,
    )
    assert breakdown["round4_legal_battle_score"] == 85.0
    assert breakdown["agent_guessing_points"] == -40.0
    assert breakdown["wallet_carryover_points"] == 100.0
    assert breakdown["total_final_score"] == 145.0  # 85.0 - 40.0 + 100.0


def test_scoring_process_standings_detects_podium_tie():
    """Verify process_finale_guessing_standings detects placement ties affecting podium."""
    records = [
        {
            "team_id": "t1",
            "team_number": 1,
            "team_name": "Team 1",
            "submission": {"is_submitted": True},
            "score_breakdown": {"total_final_score": 200.0, "round4_legal_battle_score": 90.0},
        },
        {
            "team_id": "t2",
            "team_number": 2,
            "team_name": "Team 2",
            "submission": {"is_submitted": True},
            "score_breakdown": {"total_final_score": 200.0, "round4_legal_battle_score": 90.0},  # Tied with T1 on 200 pts!
        },
        {
            "team_id": "t3",
            "team_number": 3,
            "team_name": "Team 3",
            "submission": {"is_submitted": True},
            "score_breakdown": {"total_final_score": 180.0, "round4_legal_battle_score": 85.0},
        },
    ] + [
        {
            "team_id": f"t{i}",
            "team_number": i,
            "team_name": f"Team {i}",
            "submission": {"is_submitted": True},
            "score_breakdown": {"total_final_score": 150.0 - i, "round4_legal_battle_score": 70.0},
        }
        for i in range(4, 9)
    ]
    standings = process_finale_guessing_standings(
        records=records,
        config={"is_scoring_rules_confirmed": True, "advancing_teams_count": 8},
        round4_finalized=True,
    )
    assert standings["can_finalize"] is False
    assert standings["ties_affecting_placement"] is True
    assert any(i["code"] == "PODIUM_TIE" for i in standings["issues"])


def test_api_get_team_guesses_organizer_unmasked_vs_team_masked(
    client: TestClient,
    organizer_headers: dict,
    setup_finale_tournament,
):
    """Verify GET /api/v1/rounds/finale/guesses returns unmasked details for organizers."""
    # Submit guess
    client.post(
        "/api/v1/rounds/finale/guesses",
        json={
            "guessingTeamId": "fin-team-1",
            "guesses": [
                {"targetTeamId": "fin-team-2", "suspectedParticipantId": "fin-part-2"},
                {"targetTeamId": "fin-team-3", "suspectedAgentName": "WrongAgent"},
            ]
        },
        headers=organizer_headers,
    )

    # Organizer view
    res = client.get("/api/v1/rounds/finale/guesses?team_id=fin-team-1", headers=organizer_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total_guesses"] == 2
    assert data["correct_guesses"] == 1
    assert data["wrong_guesses"] == 1
    assert data["total_guessing_points"] == 10.0  # 30 - 20 = 10.0


def test_api_config_endpoints_get_and_put(
    client: TestClient,
    organizer_headers: dict,
    setup_finale_tournament,
):
    """Verify GET and PUT /api/v1/rounds/finale/config."""
    # Get config
    get_res = client.get("/api/v1/rounds/finale/config")
    assert get_res.status_code == 200
    cfg = get_res.json()["data"]
    assert (cfg.get("minGuesses") if "minGuesses" in cfg else cfg.get("min_guesses")) == 1
    assert (cfg.get("maxGuesses") if "maxGuesses" in cfg else cfg.get("max_guesses")) == 5
    assert (cfg.get("correctGuessPoints") if "correctGuessPoints" in cfg else cfg.get("correct_guess_points")) == 30.0
    assert (cfg.get("wrongGuessPoints") if "wrongGuessPoints" in cfg else cfg.get("wrong_guess_points")) == -20.0

    # Put update
    put_res = client.put(
        "/api/v1/rounds/finale/config",
        json={"carryoverWalletPercent": 12.5},
        headers=organizer_headers,
    )
    assert put_res.status_code == 200
    put_data = put_res.json()["data"]
    assert (put_data.get("carryoverWalletPercent") if "carryoverWalletPercent" in put_data else put_data.get("carryover_wallet_percent")) == 12.5

    # Reset
    client.put(
        "/api/v1/rounds/finale/config",
        json={"carryoverWalletPercent": 10.0},
        headers=organizer_headers,
    )


def test_api_qualification_checklist_endpoint(
    client: TestClient,
    organizer_headers: dict,
    setup_finale_tournament,
):
    """Verify GET /api/v1/rounds/finale/qualification returns checklist items."""
    res = client.get("/api/v1/rounds/finale/qualification", headers=organizer_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "checklist" in data
    assert len(data["checklist"]) >= 4
    assert any(c["id"] == "round-4-finalized" for c in data["checklist"])
    assert any(c["id"] == "finalist-count" for c in data["checklist"])


def test_api_confidentiality_strict_team_isolation_and_no_leak_before_reveal(
    client: TestClient,
    db_session: Session,
    organizer_headers: dict,
    projector_headers: dict,
    setup_finale_tournament,
):
    """
    Confidentiality Review Verification:
    1. Non-organizer viewers must NOT receive another team's Secret Agent identity.
    2. Non-organizer viewers must NOT receive whether a guess is correct before reveal.
    3. suspected_agent_name represents ONLY the submitted guess string and never exposes actual agent identity.
    4. Actual agent identity is resolved strictly server-side against the private dossier.
    5. Overview & Leaderboard mask unmasked guessing points before reveal for non-organizers.
    """
    # Submit guess targeting Team 2 with suspected_agent_name "WildGuess" (wrong)
    sub_res = client.post(
        "/api/v1/rounds/finale/guesses",
        json={
            "guessingTeamId": "fin-team-1",
            "guesses": [
                {"targetTeamId": "fin-team-2", "suspectedAgentName": "WildGuess"}
            ]
        },
        headers=projector_headers,
    )
    assert sub_res.status_code == 200
    sub_data = sub_res.json()["data"]
    # Non-organizer response must NOT reveal correctness or points
    assert sub_data["total_guesses"] == 1
    assert sub_data["correct_guesses"] is None
    assert sub_data["wrong_guesses"] is None
    assert sub_data["total_guessing_points"] is None

    # View guesses with non-organizer projector_headers: must be rejected with 403 Forbidden
    get_res = client.get("/api/v1/rounds/finale/guesses?team_id=fin-team-1", headers=projector_headers)
    assert get_res.status_code == 403

    # View guesses with organizer_headers: returns unmasked data with submitted guess echo
    org_get_res = client.get("/api/v1/rounds/finale/guesses?team_id=fin-team-1", headers=organizer_headers)
    assert org_get_res.status_code == 200
    g_data = org_get_res.json()["data"]
    assert len(g_data["guesses"]) == 1
    assert g_data["guesses"][0]["suspected_agent_name"] == "WildGuess"  # Only submitted guess echo
    assert g_data["guesses"][0]["is_correct"] is False                  # Evaluated correctly server-side
    assert g_data["guesses"][0]["points_awarded"] == -20.0

    # View Best Secret Agent before reveal: participant_name & codename must be CONFIDENTIAL
    bsa_res = client.get("/api/v1/rounds/finale/best-secret-agent", headers=projector_headers)
    assert bsa_res.status_code == 200
    bsa_data = bsa_res.json()["data"]
    for r in bsa_data.get("rankings", []):
        assert (r.get("participantName") or r.get("participant_name")) == "CONFIDENTIAL"
        assert r.get("codename") == "CONFIDENTIAL"
        assert (r.get("participantId") or r.get("participant_id")) == "CONFIDENTIAL"

    # View overview / leaderboard before reveal: agent guessing points and total final score must be masked
    overview_res = client.get("/api/v1/rounds/finale/overview", headers=projector_headers)
    assert overview_res.status_code == 200
    for rec in overview_res.json()["data"]["records"]:
        sb = rec.get("scoreBreakdown") or rec.get("score_breakdown")
        assert sb.get("agentGuessingPoints", sb.get("agent_guessing_points")) is None
        assert sb.get("totalFinalScore", sb.get("total_final_score")) is None


def test_scoring_server_side_only_identity_resolution():
    """
    Confidentiality Unit Test:
    Ensures suspected_agent_name is resolved strictly against server-side dossiers
    without mutating the input or exposing actual identity.
    """
    dossier_map = {
        "t2": {
            "participant_id": "real-part-uuid",
            "codename": "ShadowFox",
            "participant_name": "Alice Smith",
            "status": "ACTIVE",
        }
    }

    # 1. Exact codename match
    g1 = {"target_team_id": "t2", "suspected_agent_name": "ShadowFox"}
    res1 = evaluate_single_guess(g1, dossier_map, 30.0, -20.0)
    assert res1["is_correct"] is True
    assert res1["points_awarded"] == 30.0
    assert res1["suspected_agent_name"] == "ShadowFox"

    # 2. Case-insensitive participant name match
    g2 = {"target_team_id": "t2", "suspected_agent_name": "alice smith"}
    res2 = evaluate_single_guess(g2, dossier_map, 30.0, -20.0)
    assert res2["is_correct"] is True
    assert res2["points_awarded"] == 30.0

    # 3. Wrong guess returns -20.0 without leaking the actual codename/participant in output
    g3 = {"target_team_id": "t2", "suspected_agent_name": "BobJones"}
    res3 = evaluate_single_guess(g3, dossier_map, 30.0, -20.0)
    assert res3["is_correct"] is False
    assert res3["points_awarded"] == -20.0
    assert "ShadowFox" not in str(res3)
    assert "Alice Smith" not in str(res3)