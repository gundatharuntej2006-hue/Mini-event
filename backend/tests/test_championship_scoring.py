"""
Unit and Integration Tests for Step 15: Final Championship Scoring, Top 4, Top 3 & Best Secret Agent.
Source of Truth: Authoritative Event Documentation reconciled in Step 6B, Step 14 & Step 15.

Tests cover:
1. Exactly 8 finalists
2. Fewer than 8 rejected
3. More than 8 rejected
4. Legal Battle component preserved
5. Agent Guessing component preserved
6. 10% wallet carryover calculation
7. Final score calculation
8. Zero wallet carryover
9. Decimal wallet carryover
10. Negative/invalid score rejection
11. Top 4 calculation
12. Top-4 cutoff tie
13. Top 3 calculation
14. Podium tie handling
15. Best Secret Agent integration
16. Best Secret Agent tie
17. Round 4 score cannot be modified by final scoring
18. Wallet balance cannot be modified by final scoring
19. Finale guessing points cannot be modified by final scoring
20. Pre-reveal confidentiality
21. Post-reveal behavior
22. Team RBAC
23. Organizer RBAC
24. Incomplete Round 4 blocks finalization
25. Incomplete Finale guessing blocks finalization
26. Idempotent finalization
27. Duplicate finalization doesn't duplicate records
28. Audit events
29. Component breakdown correctness
30. Complete 8-team final leaderboard
31. Progressive stage reveals (top_four, podium, secret_agents)
32. Organizer tie resolution endpoint
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.constants import (
    DEFAULT_CARRYOVER_WEIGHT_PERCENT,
    AGENT_CORRECT_GUESS,
    AGENT_WRONG_GUESS,
    R4_ADVANCING_COUNT,
    PODIUM_SIZE,
)
from app.models.team import Team
from app.models.participant import Participant
from app.models.wallet import TeamWallet
from app.models.agent import SecretAgentDossier, SecretAgentTask, AgentTaskStatus, AgentDossierStatus
from app.models.progression import RoundQualification, TieReview, AuditLog
from app.models.finale import (
    FinaleConfigModel,
    FinaleTeamGuessSubmissionModel,
    FinaleAgentGuessModel,
    FinaleChampionshipStandingModel,
)
from app.scoring.championship_scoring import (
    calculate_final_championship_score,
    calculate_championship_standings,
    calculate_best_secret_agent,
)
from app.services import championship_service, progression_service


# ==============================================================================
# 1. PURE SCORING CALCULATION & COMPONENT TESTS (1 - 10)
# ==============================================================================

def test_01_final_score_calculation_formula():
    """Verify official formula: Final Score = Legal Battle + Agent Guessing + (Wallet * 0.10)."""
    res = calculate_final_championship_score(
        legal_battle_score=90.0,
        agent_guessing_points=40.0,
        remaining_black_market_points=1000.0,
        carryover_weight=0.10,
    )
    # 90.0 + 40.0 + (1000 * 0.10) = 90.0 + 40.0 + 100.0 = 230.0
    assert res["final_score"] == 230.0


def test_02_legal_battle_component_preserved():
    """Verify Legal Battle component is preserved separately and unmodified."""
    res = calculate_final_championship_score(
        legal_battle_score=85.5,
        agent_guessing_points=10.0,
        remaining_black_market_points=500.0,
        carryover_weight=0.10,
    )
    assert res["legal_battle_component"] == 85.5
    assert res["legal_battle_score"] == 85.5


def test_03_agent_guessing_component_preserved():
    """Verify Agent Guessing points are preserved separately."""
    res = calculate_final_championship_score(
        legal_battle_score=80.0,
        agent_guessing_points=-20.0,
        remaining_black_market_points=500.0,
        carryover_weight=0.10,
    )
    assert res["agent_guessing_component"] == -20.0
    assert res["agent_guessing_points"] == -20.0


def test_04_wallet_carryover_ten_percent_calculation():
    """Verify 10% wallet carryover calculation."""
    res = calculate_final_championship_score(
        legal_battle_score=75.0,
        agent_guessing_points=0.0,
        remaining_black_market_points=1250.0,
        carryover_weight=0.10,
    )
    assert res["black_market_component"] == 125.0
    assert res["remaining_black_market_points"] == 1250.0
    assert res["final_score"] == 200.0  # 75.0 + 0 + 125.0


def test_05_zero_wallet_carryover():
    """Verify composite final score when remaining wallet balance is 0."""
    res = calculate_final_championship_score(
        legal_battle_score=95.0,
        agent_guessing_points=60.0,
        remaining_black_market_points=0.0,
        carryover_weight=0.10,
    )
    assert res["black_market_component"] == 0.0
    assert res["final_score"] == 155.0  # 95.0 + 60.0 + 0.0


def test_06_decimal_wallet_carryover():
    """Verify decimal wallet balance and fractional carryover without precision loss."""
    res = calculate_final_championship_score(
        legal_battle_score=88.25,
        agent_guessing_points=30.0,
        remaining_black_market_points=735.50,
        carryover_weight=0.10,
    )
    # 735.50 * 0.10 = 73.55 -> Total = 88.25 + 30.0 + 73.55 = 191.80
    assert res["black_market_component"] == 73.55
    assert res["final_score"] == 191.80


def test_07_negative_or_invalid_legal_battle_score_rejected():
    """Verify negative or > 100 Legal Battle scores are rejected."""
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_final_championship_score(
            legal_battle_score=-5.0,
            agent_guessing_points=0.0,
            remaining_black_market_points=1000.0,
        )

    with pytest.raises(ValueError, match="cannot exceed maximum of 100.0"):
        calculate_final_championship_score(
            legal_battle_score=105.0,
            agent_guessing_points=0.0,
            remaining_black_market_points=1000.0,
        )


def test_08_missing_legal_battle_score_keeps_final_score_none():
    """Verify unentered / missing Legal Battle score keeps final_score as None without error."""
    res = calculate_final_championship_score(
        legal_battle_score=None,
        agent_guessing_points=30.0,
        remaining_black_market_points=1000.0,
    )
    assert res["legal_battle_component"] is None
    assert res["final_score"] is None
    assert res["black_market_component"] == 100.0


def test_09_configurable_carryover_weight():
    """Verify carryover weight parameter is customizable (e.g. 15%)."""
    res = calculate_final_championship_score(
        legal_battle_score=90.0,
        agent_guessing_points=0.0,
        remaining_black_market_points=1000.0,
        carryover_weight=0.15,
    )
    assert res["black_market_component"] == 150.0
    assert res["final_score"] == 240.0


def test_10_component_breakdown_correctness_summary():
    """Verify all breakdown components are strictly non-mutating and returned together."""
    res = calculate_final_championship_score(
        legal_battle_score=92.0,
        agent_guessing_points=60.0,
        remaining_black_market_points=800.0,
        carryover_weight=0.10,
    )
    assert res == {
        "legal_battle_score": 92.0,
        "agent_guessing_points": 60.0,
        "remaining_black_market_points": 800.0,
        "carryover_weight": 0.10,
        "legal_battle_component": 92.0,
        "agent_guessing_component": 60.0,
        "black_market_component": 80.0,
        "final_score": 232.0,
    }


# ==============================================================================
# 2. STANDINGS, TOP 4, PODIUM & TIE SAFEGUARDS (11 - 16)
# ==============================================================================

def test_11_exactly_eight_finalists_validated():
    """Verify calculate_championship_standings passes when exactly 8 finalists participate."""
    records = [
        {
            "team_id": f"team-{i}",
            "team_number": i,
            "team_name": f"Squad {i}",
            "legal_battle_score": 70.0 + i * 2,
            "agent_guessing_points": 10.0 * i,
            "remaining_black_market_points": 1000.0,
        }
        for i in range(1, 9)
    ]
    standings = calculate_championship_standings(records, carryover_weight=0.10, expected_finalists=8)
    assert standings["can_finalize"] is True
    assert len(standings["records"]) == 8


def test_12_fewer_than_eight_finalists_rejected():
    """Verify fewer than 8 finalists blocks finalization with FEWER_THAN_8_FINALISTS issue."""
    records = [
        {
            "team_id": f"team-{i}",
            "team_number": i,
            "team_name": f"Squad {i}",
            "legal_battle_score": 80.0,
            "agent_guessing_points": 10.0,
            "remaining_black_market_points": 1000.0,
        }
        for i in range(1, 7)  # Only 6 teams
    ]
    standings = calculate_championship_standings(records, carryover_weight=0.10, expected_finalists=8)
    assert standings["can_finalize"] is False
    assert any(i["code"] == "FEWER_THAN_8_FINALISTS" for i in standings["issues"])


def test_13_more_than_eight_finalists_rejected():
    """Verify more than 8 finalists blocks finalization with MORE_THAN_8_FINALISTS issue."""
    records = [
        {
            "team_id": f"team-{i}",
            "team_number": i,
            "team_name": f"Squad {i}",
            "legal_battle_score": 80.0,
            "agent_guessing_points": 10.0,
            "remaining_black_market_points": 1000.0,
        }
        for i in range(1, 10)  # 9 teams
    ]
    standings = calculate_championship_standings(records, carryover_weight=0.10, expected_finalists=8)
    assert standings["can_finalize"] is False
    assert any(i["code"] == "MORE_THAN_8_FINALISTS" for i in standings["issues"])


def test_14_top_four_calculation_and_status():
    """Verify top 4 teams receive is_top_four = True, others False."""
    records = [
        {
            "team_id": f"team-{i}",
            "team_number": i,
            "team_name": f"Squad {i}",
            "legal_battle_score": 50.0 + (i * 5.0),  # team 8 has highest score
            "agent_guessing_points": 0.0,
            "remaining_black_market_points": 1000.0,
        }
        for i in range(1, 9)
    ]
    standings = calculate_championship_standings(records, carryover_weight=0.10)
    assert len(standings["top_four"]) == 4
    # Top 4 should be team-8, team-7, team-6, team-5
    top4_ids = [t["team_id"] for t in standings["top_four"]]
    assert top4_ids == ["team-8", "team-7", "team-6", "team-5"]

    for r in standings["records"]:
        if r["team_id"] in top4_ids:
            assert r["is_top_four"] is True
        else:
            assert r["is_top_four"] is False


def test_15_top_four_cutoff_tie_flags_organizer_review():
    """Verify when rank 4 and rank 5 are tied, top_four_tie_requires_review is flagged."""
    records = [
        {"team_id": "team-1", "team_number": 1, "legal_battle_score": 95.0, "agent_guessing_points": 0.0, "remaining_black_market_points": 1000.0},
        {"team_id": "team-2", "team_number": 2, "legal_battle_score": 90.0, "agent_guessing_points": 0.0, "remaining_black_market_points": 1000.0},
        {"team_id": "team-3", "team_number": 3, "legal_battle_score": 85.0, "agent_guessing_points": 0.0, "remaining_black_market_points": 1000.0},
        {"team_id": "team-4", "team_number": 4, "legal_battle_score": 80.0, "agent_guessing_points": 0.0, "remaining_black_market_points": 1000.0},  # 80 + 100 = 180
        {"team_id": "team-5", "team_number": 5, "legal_battle_score": 80.0, "agent_guessing_points": 0.0, "remaining_black_market_points": 1000.0},  # 80 + 100 = 180 (TIED with 4)
        {"team_id": "team-6", "team_number": 6, "legal_battle_score": 70.0, "agent_guessing_points": 0.0, "remaining_black_market_points": 1000.0},
        {"team_id": "team-7", "team_number": 7, "legal_battle_score": 65.0, "agent_guessing_points": 0.0, "remaining_black_market_points": 1000.0},
        {"team_id": "team-8", "team_number": 8, "legal_battle_score": 60.0, "agent_guessing_points": 0.0, "remaining_black_market_points": 1000.0},
    ]
    standings = calculate_championship_standings(records, carryover_weight=0.10)
    assert standings["can_finalize"] is False
    assert standings["top_four_tie_requires_review"] is True
    assert standings["requires_organizer_review"] is True
    assert set(standings["tied_top_four_teams"]) == {"team-4", "team-5"}
    assert any(i["code"] == "TOP_FOUR_CUTOFF_TIE" for i in standings["issues"])


def test_16_podium_titles_and_tie_handling():
    """Verify Top 3 assign Grand Champion, 1st Runner Up, 2nd Runner Up, and detect podium ties."""
    records = [
        {"team_id": "team-1", "team_number": 1, "legal_battle_score": 90.0, "agent_guessing_points": 0.0, "remaining_black_market_points": 1000.0},  # 190.0
        {"team_id": "team-2", "team_number": 2, "legal_battle_score": 90.0, "agent_guessing_points": 0.0, "remaining_black_market_points": 1000.0},  # 190.0 (TIED for Champion)
        {"team_id": "team-3", "team_number": 3, "legal_battle_score": 80.0, "agent_guessing_points": 0.0, "remaining_black_market_points": 1000.0},
    ] + [
        {"team_id": f"team-{i}", "team_number": i, "legal_battle_score": 70.0 - i, "agent_guessing_points": 0.0, "remaining_black_market_points": 1000.0}
        for i in range(4, 9)
    ]
    standings = calculate_championship_standings(records, carryover_weight=0.10)
    assert standings["can_finalize"] is False
    assert standings["podium_tie_requires_review"] is True
    assert standings["requires_organizer_review"] is True
    assert set(standings["tied_podium_teams"]) == {"team-1", "team-2"}
    assert any(i["code"] == "PODIUM_TIE" for i in standings["issues"])


def test_17_best_secret_agent_integration_two_tier():
    """Verify Best Secret Agent integration ranks by verified tasks desc, unmaskings asc."""
    dossiers = [
        {"id": "d1", "team_id": "t1", "team_number": 1, "verified_tasks_count": 3},
        {"id": "d2", "team_id": "t2", "team_number": 2, "verified_tasks_count": 3},
        {"id": "d3", "team_id": "t3", "team_number": 3, "verified_tasks_count": 1},
    ]
    # t1 was unmasked once (+1 correct guess against them), t2 was unmasked 0 times
    all_evaluated_guesses = [
        {"target_team_id": "t1", "is_correct": True},
    ]
    res = calculate_best_secret_agent(dossiers, all_evaluated_guesses)
    assert res["tie_requires_review"] is False
    assert res["best_agent"]["team_id"] == "t2"  # 3 tasks, 0 unmaskings > 3 tasks, 1 unmasking
    assert res["rankings"][1]["team_id"] == "t1"


def test_18_best_secret_agent_tie_requires_organizer_review():
    """Verify Best Secret Agent tie on both tiers flags tie_requires_review = True."""
    dossiers = [
        {"id": "d1", "team_id": "t1", "team_number": 1, "verified_tasks_count": 4},
        {"id": "d2", "team_id": "t2", "team_number": 2, "verified_tasks_count": 4},
    ]
    all_evaluated_guesses = []  # Both have 0 unmaskings
    res = calculate_best_secret_agent(dossiers, all_evaluated_guesses)
    assert res["tie_requires_review"] is True
    assert set(res["tied_candidate_ids"]) == {"d1", "d2"}


# ==============================================================================
# 3. DATABASE & INTEGRATION WORKFLOW TESTS (19 - 32)
# ==============================================================================

@pytest.fixture
def setup_championship_tournament(db_session: Session):
    """Sets up an isolated tournament with 8 finalist teams, wallets, dossiers, and R4 qualifications."""
    from app.models.round4 import Round4ConfigModel
    from app.models.round_models import RoundState

    # Mark Round 4 as finalized
    r4_cfg = Round4ConfigModel(id=1, is_finalized=True, is_rubric_confirmed=True)
    db_session.merge(r4_cfg)
    r4_state = RoundState(id=4, name="Round 4", codename="legal_battle", is_finalized=True, status="Completed")
    db_session.merge(r4_state)

    r5_state = RoundState(id=5, name="Round 5", codename="grand_finale", is_finalized=False, status="In Progress")
    db_session.merge(r5_state)

    teams = []
    for i in range(1, 9):
        t = Team(
            id=f"champ-team-{i}",
            name=f"Finalist Squad {i}",
            team_number=i,
        )
        db_session.add(t)
        teams.append(t)

        p = Participant(
            id=f"champ-part-{i}",
            team_id=t.id,
            name=f"Agent Candidate {i}",
            email=f"champagent{i}@tournament.org",
            usn=f"1MS21CS{i:03d}",
            phone=f"987654321{i}",
        )
        db_session.add(p)

        d = SecretAgentDossier(
            id=f"sad-champ-{i}",
            team_id=t.id,
            participant_id=p.id,
            codename=f"Agent-{i}",
            status=AgentDossierStatus.ACTIVE,
        )
        db_session.add(d)

        # Team 1: 3 tasks, Team 2: 2 tasks, Team 3: 1 task
        if i in (1, 2, 3):
            for task_num in range(4 - i):
                tk = SecretAgentTask(
                    id=f"sat-champ-{i}-{task_num}",
                    dossier_id=d.id,
                    task_description=f"Sabotage mission {task_num}",
                    status=AgentTaskStatus.VERIFIED,
                )
                db_session.add(tk)

        # Team Wallets: 1000.0, 1100.0, 1200.0 ...
        w = TeamWallet(
            team_id=t.id,
            current_balance=1000.0 + (i * 100.0),
        )
        db_session.add(w)

        # R4 Qualification: 70.0 + (i * 3.0) -> team 8 has 94.0
        q = RoundQualification(
            id=f"qual-r4-{t.id}",
            round_number=4,
            team_id=t.id,
            rank=i,
            status="Finalized Qualified",
            score_snapshot=70.0 + (i * 3.0),
            is_advancing=True,
            finalized_by="Lead Organizer",
        )
        db_session.add(q)

        # Guess submissions
        sub = FinaleTeamGuessSubmissionModel(
            id=f"fg-sub-{t.id}",
            guessing_team_id=t.id,
            total_guesses=2,
            correct_guesses=1 if i <= 4 else 0,
            wrong_guesses=1 if i <= 4 else 2,
            total_guessing_points=10.0 if i <= 4 else -40.0,
            is_submitted=True,
        )
        db_session.add(sub)

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
        is_top_four_revealed=False,
        is_podium_revealed=False,
        is_agents_revealed=False,
    )
    db_session.merge(cfg)
    db_session.commit()
    return teams


def test_19_underlying_data_not_mutated_by_final_scoring(
    client: TestClient,
    organizer_headers: dict,
    db_session: Session,
    setup_championship_tournament,
):
    """Verify calculating championship scores does not mutate R4 score or wallet balance."""
    # Check original wallet balance for Team 1
    w_before = db_session.query(TeamWallet).filter(TeamWallet.team_id == "champ-team-1").first()
    bal_before = w_before.current_balance

    # Fetch standings
    res = client.get("/api/v1/finale/leaderboard", headers=organizer_headers)
    assert res.status_code == 200

    # Verify wallet balance unchanged
    db_session.refresh(w_before)
    assert w_before.current_balance == bal_before

    # Verify R4 qualification score snapshot unchanged
    r4_q = db_session.query(RoundQualification).filter(
        RoundQualification.round_number == 4,
        RoundQualification.team_id == "champ-team-1",
    ).first()
    assert r4_q.score_snapshot == 73.0  # 70 + (1 * 3)


def test_20_pre_reveal_confidentiality_masks_scores_for_viewers(
    client: TestClient,
    projector_headers: dict,
    setup_championship_tournament,
):
    """Verify non-organizers cannot view unmasked final scores or private identities before reveal."""
    # Top 4 before reveal: empty/masked
    t4_res = client.get("/api/v1/finale/top-four", headers=projector_headers)
    assert t4_res.status_code == 200
    t4_data = t4_res.json()["data"]
    assert t4_data.get("isRevealed", t4_data.get("is_revealed")) is False
    assert len(t4_data.get("topFour", t4_data.get("top_four", []))) == 0

    # Podium before reveal: empty/masked
    pod_res = client.get("/api/v1/finale/podium", headers=projector_headers)
    assert pod_res.status_code == 200
    pod_data = pod_res.json()["data"]
    assert pod_data.get("isRevealed", pod_data.get("is_revealed")) is False
    assert len(pod_data.get("podium", [])) == 0

    # Best Secret Agent before reveal: confidential
    bsa_res = client.get("/api/v1/finale/best-secret-agent", headers=projector_headers)
    assert bsa_res.status_code == 200
    for r in bsa_res.json()["data"]["rankings"]:
        assert (r.get("participantName") or r.get("participant_name")) == "CONFIDENTIAL"
        assert r.get("codename") == "CONFIDENTIAL"


def test_21_progressive_stage_reveals_workflow(
    client: TestClient,
    organizer_headers: dict,
    projector_headers: dict,
    setup_championship_tournament,
):
    """Verify organizer can progressively reveal Top 4, then Podium, then Secret Agents."""
    # 1. Reveal Top 4
    rev_t4 = client.post(
        "/api/v1/finale/reveal",
        json={"stage": "top_four"},
        headers=organizer_headers,
    )
    assert rev_t4.status_code == 200
    assert rev_t4.json()["data"]["is_top_four_revealed"] is True

    # Public viewer can now see Top 4
    t4_view = client.get("/api/v1/finale/top-four", headers=projector_headers)
    assert t4_view.status_code == 200
    t4_data = t4_view.json()["data"]
    assert t4_data.get("isRevealed", t4_data.get("is_revealed")) is True
    assert len(t4_data.get("topFour", t4_data.get("top_four", []))) == 4

    # But Podium is still not revealed to public
    pod_view = client.get("/api/v1/finale/podium", headers=projector_headers)
    assert pod_view.status_code == 200
    pod_data = pod_view.json()["data"]
    assert pod_data.get("isRevealed", pod_data.get("is_revealed")) is False

    # 2. Reveal Podium
    rev_pod = client.post(
        "/api/v1/finale/reveal",
        json={"stage": "podium"},
        headers=organizer_headers,
    )
    assert rev_pod.status_code == 200
    assert rev_pod.json()["data"]["is_podium_revealed"] is True

    # Public viewer can now see Podium
    pod_view2 = client.get("/api/v1/finale/podium", headers=projector_headers)
    assert pod_view2.status_code == 200
    pod_data2 = pod_view2.json()["data"]
    assert pod_data2.get("isRevealed", pod_data2.get("is_revealed")) is True
    assert len(pod_data2.get("podium", [])) == 3

    # 3. Reveal Secret Agents
    rev_sa = client.post(
        "/api/v1/finale/reveal",
        json={"stage": "secret_agents"},
        headers=organizer_headers,
    )
    assert rev_sa.status_code == 200
    assert rev_sa.json()["data"]["is_agents_revealed"] is True

    # Public viewer can now see Secret Agent codenames
    bsa_view = client.get("/api/v1/finale/best-secret-agent", headers=projector_headers)
    assert bsa_view.status_code == 200
    assert bsa_view.json()["data"]["rankings"][0]["codename"] != "CONFIDENTIAL"


def test_22_api_get_individual_final_score(
    client: TestClient,
    organizer_headers: dict,
    setup_championship_tournament,
):
    """Verify GET /api/v1/finale/final-score returns composite breakdown."""
    res = client.get("/api/v1/finale/final-score?team_id=champ-team-1", headers=organizer_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert (data.get("teamId") or data.get("team_id")) == "champ-team-1"
    assert (data.get("legalBattleScore") or data.get("legal_battle_score")) == 73.0
    assert (data.get("agentGuessingPoints") if "agentGuessingPoints" in data else data.get("agent_guessing_points")) == 10.0
    assert (data.get("remainingBlackMarketPoints") if "remainingBlackMarketPoints" in data else data.get("remaining_black_market_points")) == 1100.0
    assert (data.get("blackMarketComponent") if "blackMarketComponent" in data else data.get("black_market_component")) == 110.0
    assert (data.get("finalScore") if "finalScore" in data else data.get("final_score")) == 193.0  # 73 + 10 + 110 = 193.0


def test_23_api_championship_finalization_lifecycle_and_idempotency(
    client: TestClient,
    organizer_headers: dict,
    db_session: Session,
    setup_championship_tournament,
):
    """Verify championship finalization seals standings, advances champions, and is idempotent."""
    # First call: finalize
    res = client.post(
        "/api/v1/finale/finalize-championship",
        json={"overrideDiscrepancy": True},
        headers=organizer_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["finalized"] is True

    # Verify FinaleChampionshipStandingModel entries exist in DB
    standings_in_db = db_session.query(FinaleChampionshipStandingModel).all()
    assert len(standings_in_db) == 8

    # Verify idempotency on second call
    res_idempotent = client.post(
        "/api/v1/finale/finalize-championship",
        headers=organizer_headers,
    )
    assert res_idempotent.status_code == 200
    assert "already" in res_idempotent.json()["data"]["message"].lower()

    # Verify no duplicate entries were created
    standings_after = db_session.query(FinaleChampionshipStandingModel).all()
    assert len(standings_after) == 8


def test_24_incomplete_round4_blocks_championship_finalization(
    client: TestClient,
    organizer_headers: dict,
    db_session: Session,
    setup_championship_tournament,
):
    """Verify unfinalized Round 4 blocks championship finalization."""
    # Unfinalize Round 4
    from app.models.round4 import Round4ConfigModel
    from app.models.round_models import RoundState
    r4_cfg = db_session.query(Round4ConfigModel).first()
    r4_cfg.is_finalized = False
    r4_st = db_session.query(RoundState).filter(RoundState.id == 4).first()
    r4_st.is_finalized = False
    db_session.commit()

    res = client.post(
        "/api/v1/finale/finalize-championship",
        headers=organizer_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["finalized"] is False
    assert any(i["code"] == "PREVIOUS_ROUND_UNFINALIZED" for i in data["issues"])


def test_25_incomplete_guessing_blocks_championship_finalization(
    client: TestClient,
    organizer_headers: dict,
    db_session: Session,
    setup_championship_tournament,
):
    """Verify missing team guess submissions blocks finalization."""
    # Delete one team's guess submission
    db_session.query(FinaleTeamGuessSubmissionModel).filter(
        FinaleTeamGuessSubmissionModel.guessing_team_id == "champ-team-8"
    ).delete()
    db_session.commit()

    res = client.post(
        "/api/v1/finale/finalize-championship",
        headers=organizer_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["finalized"] is False
    assert any(i["code"] == "GUESSING_UNFINALIZED" for i in data["issues"])


def test_26_api_resolve_tie_workflow(
    client: TestClient,
    organizer_headers: dict,
    setup_championship_tournament,
):
    """Verify POST /api/v1/finale/resolve-tie allows organizer to resolve ties."""
    res = client.post(
        "/api/v1/finale/resolve-tie",
        json={
            "tieType": "podium",
            "decisions": {"champ-team-1": 1, "champ-team-2": 2},
            "notes": "Oral presentation tie-break resolution applied by faculty panel.",
        },
        headers=organizer_headers,
    )
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "RESOLVED"


def test_27_audit_log_records_championship_events(
    client: TestClient,
    organizer_headers: dict,
    db_session: Session,
    setup_championship_tournament,
):
    """Verify organizer actions create immutable AuditLog entries."""
    client.post(
        "/api/v1/finale/reveal",
        json={"stage": "podium"},
        headers=organizer_headers,
    )
    logs = db_session.query(AuditLog).filter(
        AuditLog.round_number == 5,
        AuditLog.action == "FINALE_REVEAL_PODIUM",
    ).all()
    assert len(logs) >= 1


def test_28_rbac_unauthorized_mutation_rejected(
    client: TestClient,
    projector_headers: dict,
    setup_championship_tournament,
):
    """Verify non-organizer cannot trigger finalization or reveal."""
    fin_res = client.post(
        "/api/v1/finale/finalize-championship",
        headers=projector_headers,
    )
    assert fin_res.status_code == 403

    rev_res = client.post(
        "/api/v1/finale/reveal",
        json={"stage": "all"},
        headers=projector_headers,
    )
    assert rev_res.status_code == 403


def test_29_full_eight_team_final_leaderboard_endpoint(
    client: TestClient,
    organizer_headers: dict,
    setup_championship_tournament,
):
    """Verify GET /api/v1/finale/leaderboard returns complete 8-team standings."""
    res = client.get("/api/v1/finale/leaderboard", headers=organizer_headers)
    assert res.status_code == 200
    records = res.json()["data"]
    assert len(records) == 8
    # Highest score is rank 1
    scores = [r["score_breakdown"]["final_score"] for r in records]
    assert scores == sorted(scores, reverse=True)


def test_30_qualification_endpoint_returns_readiness_checklist(
    client: TestClient,
    organizer_headers: dict,
    setup_championship_tournament,
):
    """Verify GET /api/v1/finale/qualification returns readiness metrics."""
    res = client.get("/api/v1/finale/qualification", headers=organizer_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "checklist" in data
    assert len(data["checklist"]) >= 4
    assert any(c["id"] == "round-4-finalized" for c in data["checklist"])
    assert any(c["id"] == "finalist-count" for c in data["checklist"])


def test_31_rounds_finale_and_finale_prefix_aliases_both_work(
    client: TestClient,
    organizer_headers: dict,
    setup_championship_tournament,
):
    """Verify both /api/v1/rounds/finale/leaderboard and /api/v1/finale/leaderboard work."""
    res1 = client.get("/api/v1/rounds/finale/leaderboard", headers=organizer_headers)
    res2 = client.get("/api/v1/finale/leaderboard", headers=organizer_headers)
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert len(res1.json()["data"]) == len(res2.json()["data"]) == 8


def test_32_final_score_ranking_respects_podium_placement_titles(
    client: TestClient,
    organizer_headers: dict,
    setup_championship_tournament,
):
    """Verify rank 1 is Grand Champion, rank 2 is 1st Runner Up, rank 3 is 2nd Runner Up, rank 4+ is Finalist."""
    res = client.get("/api/v1/finale/leaderboard", headers=organizer_headers)
    assert res.status_code == 200
    records = res.json()["data"]
    assert records[0]["placement_title"] == "Grand Champion"
    assert records[0]["podium_position"] == 1
    assert records[1]["placement_title"] == "1st Runner Up"
    assert records[1]["podium_position"] == 2
    assert records[2]["placement_title"] == "2nd Runner Up"
    assert records[2]["podium_position"] == 3
    for r in records[3:]:
        assert r["placement_title"] == "Finalist"
        assert r["podium_position"] is None
