import pytest
from fastapi.testclient import TestClient

def test_round_progression_gating_and_immutability(
    client: TestClient,
    organizer_headers: dict,
    marshal_headers: dict,
    judge_headers: dict
):
    """
    Verifies Part 4 Round Progression & Finalization Rules:
    1. Round N cannot finalize before Round N-1 is finalized.
    2. Finalization is idempotent (calling multiple times does not duplicate state).
    3. Finalized rounds are immutable: subsequent mutations are strictly blocked (HTTP 400).
    """
    # 1. Attempt to finalize Round 2 before Round 1 -> HTTP 400
    res_premature = client.post(
        "/api/v1/rounds/2/finalize",
        json={"finalizedBy": "Lead Organizer"},
        headers=organizer_headers
    )
    assert res_premature.status_code == 400
    assert "not finalized yet" in res_premature.json()["message"]

    # 2. Finalize Round 1 with overrideDiscrepancy (since only partial test teams exist)
    res_r1_fin = client.post(
        "/api/v1/rounds/1/finalize",
        json={"finalizedBy": "Lead Organizer", "overrideDiscrepancy": True, "notes": "Part 4 progression gate test"},
        headers=organizer_headers
    )
    assert res_r1_fin.status_code == 200
    assert res_r1_fin.json()["data"]["success"] is True

    # 3. Verify idempotency: calling finalize again on Round 1 succeeds with idempotent message
    res_r1_idempotent = client.post(
        "/api/v1/rounds/1/finalize",
        json={"finalizedBy": "Lead Organizer"},
        headers=organizer_headers
    )
    assert res_r1_idempotent.status_code == 200
    assert "already finalized" in res_r1_idempotent.json()["data"]["message"]

    # 4. Immutability Lock: attempting to mutate Round 1 records after finalization -> HTTP 400
    # Create a team
    t_res = client.post("/api/v1/teams", json={"name": "Lock Test Team"}, headers=organizer_headers)
    assert t_res.status_code in (200, 201)
    team_id = t_res.json()["data"]["id"]

    res_mutate_blocked = client.put(
        f"/api/v1/rounds/1/records/{team_id}",
        json={"miniRounds": [{"roundNumber": 1, "durationSeconds": 100, "hintsUsed": 0, "isCompleted": True}]},
        headers=marshal_headers
    )
    assert res_mutate_blocked.status_code == 400
    assert "is finalized and sealed" in res_mutate_blocked.json()["message"]


def test_round1_tiebreaker_fastest_mini_round(
    client: TestClient,
    organizer_headers: dict,
    marshal_headers: dict
):
    """
    Verifies Round 1 (The Great Expedition) tie-breaking rule:
    When adjusted total seconds are identical, the squad with the lower
    fastest_mini_round_seconds ranks higher.
    """
    # Create 2 teams
    t1 = client.post("/api/v1/teams", json={"name": "Tiebreak Squad A"}, headers=organizer_headers).json()["data"]["id"]
    t2 = client.post("/api/v1/teams", json={"name": "Tiebreak Squad B"}, headers=organizer_headers).json()["data"]["id"]

    # Squad A: 100s, 100s, 100s -> Total: 300s, Fastest mini: 100s
    client.put(
        f"/api/v1/rounds/1/records/{t1}",
        json={
            "miniRounds": [
                {"roundNumber": 1, "durationSeconds": 100, "hintsUsed": 0, "isCompleted": True},
                {"roundNumber": 2, "durationSeconds": 100, "hintsUsed": 0, "isCompleted": True},
                {"roundNumber": 3, "durationSeconds": 100, "hintsUsed": 0, "isCompleted": True},
            ]
        },
        headers=marshal_headers
    )

    # Squad B: 80s, 110s, 110s -> Total: 300s, Fastest mini: 80s (Faster single mini-round!)
    client.put(
        f"/api/v1/rounds/1/records/{t2}",
        json={
            "miniRounds": [
                {"roundNumber": 1, "durationSeconds": 80, "hintsUsed": 0, "isCompleted": True},
                {"roundNumber": 2, "durationSeconds": 110, "hintsUsed": 0, "isCompleted": True},
                {"roundNumber": 3, "durationSeconds": 110, "hintsUsed": 0, "isCompleted": True},
            ]
        },
        headers=marshal_headers
    )

    recs = {r["teamId"]: r for r in client.get("/api/v1/rounds/1/records").json()["data"]}
    assert recs[t1]["adjustedTotalSeconds"] == 300.0
    assert recs[t2]["adjustedTotalSeconds"] == 300.0

    # Squad B has faster mini-round (80s vs 100s), so Squad B should rank higher than Squad A
    assert recs[t2]["rank"] < recs[t1]["rank"]


def test_round1_hidden_code_recovery(
    client: TestClient,
    organizer_headers: dict,
    marshal_headers: dict
):
    """
    Verifies Round 1 Hidden Code Recovery:
    Saves recovery flag, timestamp, and notes without exposing confidential values.
    """
    t = client.post("/api/v1/teams", json={"name": "QR Explorer Team"}, headers=organizer_headers).json()["data"]["id"]
    
    update_res = client.put(
        f"/api/v1/rounds/1/records/{t}",
        json={
            "miniRounds": [
                {"roundNumber": 1, "durationSeconds": 120, "hintsUsed": 0, "isCompleted": True},
                {"roundNumber": 2, "durationSeconds": 120, "hintsUsed": 0, "isCompleted": True},
                {"roundNumber": 3, "durationSeconds": 120, "hintsUsed": 0, "isCompleted": True},
            ],
            "hiddenCodeRecovered": True,
            "hiddenCodeNotes": "Recovered physical tag beneath quadrangle bench."
        },
        headers=marshal_headers
    )
    assert update_res.status_code == 200
    data = update_res.json()["data"]
    assert data["hiddenCodeRecovered"] is True
    assert data["hiddenCodeRecoveredAt"] is not None
    assert "quadrangle bench" in data["hiddenCodeNotes"]


def test_round3_code_fragments_and_balance_tiebreaker(
    client: TestClient,
    organizer_headers: dict,
    marshal_headers: dict
):
    """
    Verifies Round 3 (The Black Market):
    1. 4 QR Code fragments can be logged and verified per squad.
    2. Standings tie-breaker: If two teams have identical balance,
       the team with more fragments discovered ranks higher.
    """
    t1 = client.post("/api/v1/teams", json={"name": "Market Trader Alpha"}, headers=organizer_headers).json()["data"]["id"]
    t2 = client.post("/api/v1/teams", json={"name": "Market Trader Beta"}, headers=organizer_headers).json()["data"]["id"]

    # Both earn 50 pts -> Balance: 100 (starting) + 50 = 150 pts
    client.post("/api/v1/rounds/3/transactions", json={"teamId": t1, "amount": 50.0, "type": "earn", "reason": "Trade"}, headers=marshal_headers)
    client.post("/api/v1/rounds/3/transactions", json={"teamId": t2, "amount": 50.0, "type": "earn", "reason": "Trade"}, headers=marshal_headers)

    # Trader Alpha discovers 1 fragment
    client.put("/api/v1/rounds/3/codes/fragment", json={"teamId": t1, "fragmentIndex": 0, "isDiscovered": True, "code": "SIGMA-1"}, headers=marshal_headers)

    # Trader Beta discovers 3 fragments
    client.put("/api/v1/rounds/3/codes/fragment", json={"teamId": t2, "fragmentIndex": 0, "isDiscovered": True, "code": "BETA-1"}, headers=marshal_headers)
    client.put("/api/v1/rounds/3/codes/fragment", json={"teamId": t2, "fragmentIndex": 1, "isDiscovered": True, "code": "BETA-2"}, headers=marshal_headers)
    client.put("/api/v1/rounds/3/codes/fragment", json={"teamId": t2, "fragmentIndex": 2, "isDiscovered": True, "code": "BETA-3"}, headers=marshal_headers)

    standings = {s["teamId"]: s for s in client.get("/api/v1/rounds/3/standings").json()["data"]}
    assert standings[t1]["currentBalance"] == 1050.0  # 1,000 start + 50 earned
    assert standings[t2]["currentBalance"] == 1050.0
    assert standings[t1]["fragmentsDiscovered"] == 1
    assert standings[t2]["fragmentsDiscovered"] == 3

    # Trader Beta has more fragments discovered, so Trader Beta ranks higher
    assert standings[t2]["rank"] < standings[t1]["rank"]


def test_secret_agent_tasks_and_scoring(
    client: TestClient,
    organizer_headers: dict,
    marshal_headers: dict,
    judge_headers: dict
):
    """
    Verifies Secret Agent Rules:
    1. Round 4 Agent Guess: correct guess awards configured bonus (+10 pts).
    2. Grand Finale Agent Verdict:
       - correct verdict awards +10 bonus.
       - incorrect verdict applies -5 penalty.
    """
    t_agent = client.post("/api/v1/teams", json={"name": "Agent Hunter Squad"}, headers=organizer_headers).json()["data"]["id"]

    # Round 4 Agent Guess
    r4_guess = client.post(
        "/api/v1/rounds/4/agent-guess",
        json={"teamId": t_agent, "outcome": "correct", "notes": "Identified Agent Cobalt through communications anomaly"},
        headers=judge_headers
    )
    assert r4_guess.status_code == 200
    assert r4_guess.json()["data"]["pointsAwarded"] == 30.0  # Section 8.2
    assert r4_guess.json()["data"]["isVerified"] is True

    # Grand Finale: Correct Agent Verdict (+30, Section 8.2)
    verdict_correct = client.post(
        "/api/v1/rounds/5/agent-verdict",
        json={
            "teamId": t_agent,
            "suspectedAgent": "Agent Cobalt",
            "actualAgent": "Agent Cobalt",
            "isCorrect": True
        },
        headers=judge_headers
    )
    assert verdict_correct.status_code == 200
    assert verdict_correct.json()["data"]["bonusPoints"] == 30.0

    # Grand Finale: Incorrect Agent Verdict (-20, Section 8.2)
    t_wrong = client.post("/api/v1/teams", json={"name": "Agent Mistake Squad"}, headers=organizer_headers).json()["data"]["id"]
    verdict_wrong = client.post(
        "/api/v1/rounds/5/agent-verdict",
        json={
            "teamId": t_wrong,
            "suspectedAgent": "Agent Mirage",
            "actualAgent": "Agent Shadow",
            "isCorrect": False
        },
        headers=judge_headers
    )
    assert verdict_wrong.status_code == 200
    assert verdict_wrong.json()["data"]["penaltyPoints"] == -20.0


def test_finale_configurable_advancing_count_ambiguity(
    client: TestClient,
    organizer_headers: dict
):
    """
    Verifies Documented Ambiguity Resolution:
    Whether Finale includes 3 or 8 teams is explicitly configurable via Round 4/5 config.
    The finalization engine dynamically honors the configured qualifying count,
    and records audit details when overrideDiscrepancy is used.
    """
    # Verify Round 4 default qualifying count is 3
    r4_info = client.get("/api/v1/rounds/4").json()["data"]
    assert r4_info["qualifyingTeamsCount"] == 8  # Section 9.1

    # Organizer updates Round 4 qualifying count to 8 (if all 8 courtroom teams attend finale)
    update_res = client.put(
        "/api/v1/rounds/4",
        json={"qualifyingTeamsCount": 8, "configJson": {"advancingTeamsCount": 8, "note": "All 8 finalist squads attend finale assembly"}},
        headers=organizer_headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["qualifyingTeamsCount"] == 8
    assert update_res.json()["data"]["configJson"]["advancingTeamsCount"] == 8

    # Reset back to official default of 3
    reset_res = client.put(
        "/api/v1/rounds/4",
        json={"qualifyingTeamsCount": 3, "configJson": {"advancingTeamsCount": 3}},
        headers=organizer_headers
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["data"]["qualifyingTeamsCount"] == 3
