import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone


def test_get_all_rounds_initializes_five_rounds(client: TestClient):
    resp = client.get("/api/v1/rounds")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    rounds = data["data"]
    assert len(rounds) == 5
    
    assert rounds[0]["id"] == 1
    assert rounds[0]["codename"] == "ROUND_1_CLUE_HUNT"
    assert rounds[0]["initialTeamsCount"] == 32
    assert rounds[0]["qualifyingTeamsCount"] == 24
    
    assert rounds[1]["id"] == 2
    assert rounds[1]["codename"] == "ROUND_2_CABO"
    assert rounds[1]["initialTeamsCount"] == 24
    assert rounds[1]["qualifyingTeamsCount"] == 12
    
    assert rounds[2]["id"] == 3
    assert rounds[2]["codename"] == "ROUND_3_BLACK_MARKET"
    assert rounds[2]["initialTeamsCount"] == 12
    assert rounds[2]["qualifyingTeamsCount"] == 8
    
    assert rounds[3]["id"] == 4
    assert rounds[3]["codename"] == "ROUND_4_LEGAL_BATTLE"
    assert rounds[3]["initialTeamsCount"] == 8
    assert rounds[3]["qualifyingTeamsCount"] == 8  # Sections 7 and 9.1: all 8 finalists are ranked
    
    assert rounds[4]["id"] == 5
    assert rounds[4]["codename"] == "GRAND_FINALE"
    assert rounds[4]["initialTeamsCount"] == 8  # Section 9.1: "the 8 finalists"
    assert rounds[4]["qualifyingTeamsCount"] == 1


def test_get_single_round_and_404(client: TestClient):
    resp = client.get("/api/v1/rounds/1")
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Clue Hunt / Expedition"

    resp_404 = client.get("/api/v1/rounds/99")
    assert resp_404.status_code == 404


def test_update_round_state_rbac(client: TestClient, organizer_headers: dict, marshal_headers: dict):
    # Public / Unauth -> 401
    resp_anon = client.put("/api/v1/rounds/1", json={"location": "North Campus Quad"})
    assert resp_anon.status_code == 401

    # Marshal -> 403 (Organizer only)
    resp_marshal = client.put("/api/v1/rounds/1", json={"location": "North Campus Quad"}, headers=marshal_headers)
    assert resp_marshal.status_code == 403

    # Organizer -> 200
    resp_org = client.put(
        "/api/v1/rounds/1",
        json={"location": "North Campus Quad", "configJson": {"hintPenaltySeconds": 150}},
        headers=organizer_headers
    )
    assert resp_org.status_code == 200
    assert resp_org.json()["data"]["location"] == "North Campus Quad"
    assert resp_org.json()["data"]["configJson"]["hintPenaltySeconds"] == 150


def test_round1_scoring_and_ranking(client: TestClient, organizer_headers: dict, marshal_headers: dict):
    # Create 3 teams
    t1_resp = client.post("/api/v1/teams", json={"name": "Alpha Squad", "identifier": "T01"}, headers=organizer_headers)
    t2_resp = client.post("/api/v1/teams", json={"name": "Bravo Squad", "identifier": "T02"}, headers=organizer_headers)
    t3_resp = client.post("/api/v1/teams", json={"name": "Charlie Squad", "identifier": "T03"}, headers=organizer_headers)
    
    t1_id = t1_resp.json()["data"]["id"]
    t2_id = t2_resp.json()["data"]["id"]
    t3_id = t3_resp.json()["data"]["id"]

    # Submit mini rounds for t1: mini1=100s(0 hints), mini2=120s(1 hint=120s penalty), mini3=80s(0 hints) -> total = 300s + 120s = 420s
    t1_update = client.put(
        f"/api/v1/rounds/1/records/{t1_id}",
        json={
            "miniRounds": [
                {"roundNumber": 1, "durationSeconds": 100, "hintsUsed": 0, "isCompleted": True},
                {"roundNumber": 2, "durationSeconds": 120, "hintsUsed": 1, "isCompleted": True},
                {"roundNumber": 3, "durationSeconds": 80, "hintsUsed": 0, "isCompleted": True},
            ],
            "hiddenCodeRecovered": True,
            "hiddenCodeNotes": "Found in library archives"
        },
        headers=marshal_headers
    )
    assert t1_update.status_code == 200
    data1 = t1_update.json()["data"]
    assert data1["rawTotalSeconds"] == 300.0
    assert data1["totalPenaltySeconds"] == 300.0  # Section 4.3: +5 minutes
    assert data1["adjustedTotalSeconds"] == 600.0  # 300s raw + one 5-minute hint
    assert data1["fastestMiniRoundSeconds"] == 80.0
    assert data1["isComplete"] is True
    assert data1["hiddenCodeRecovered"] is True

    # Submit mini rounds for t2: mini1=90s, mini2=90s, mini3=90s (0 hints) -> total = 270s (faster than t1)
    client.put(
        f"/api/v1/rounds/1/records/{t2_id}",
        json={
            "miniRounds": [
                {"roundNumber": 1, "durationSeconds": 90, "hintsUsed": 0, "isCompleted": True},
                {"roundNumber": 2, "durationSeconds": 90, "hintsUsed": 0, "isCompleted": True},
                {"roundNumber": 3, "durationSeconds": 90, "hintsUsed": 0, "isCompleted": True},
            ]
        },
        headers=marshal_headers
    )

    # Get records and check ranking
    records_resp = client.get("/api/v1/rounds/1/records")
    assert records_resp.status_code == 200
    recs = {r["teamId"]: r for r in records_resp.json()["data"]}
    
    assert recs[t2_id]["rank"] == 1
    assert recs[t2_id]["adjustedTotalSeconds"] == 270.0
    assert recs[t2_id]["qualificationStatus"] == "Qualified"

    assert recs[t1_id]["rank"] == 2
    assert recs[t1_id]["adjustedTotalSeconds"] == 600.0  # 300s raw + one 5-minute hint
    assert recs[t1_id]["qualificationStatus"] == "Qualified"

    assert recs[t3_id]["rank"] is None
    assert recs[t3_id]["qualificationStatus"] == "Incomplete"


def test_round2_cabo_placements_and_standings(client: TestClient, organizer_headers: dict, marshal_headers: dict):
    t1 = client.post("/api/v1/teams", json={"name": "Delta Force", "identifier": "T04"}, headers=organizer_headers).json()["data"]["id"]
    t2 = client.post("/api/v1/teams", json={"name": "Echo Strike", "identifier": "T05"}, headers=organizer_headers).json()["data"]["id"]

    # Submit Game 1 results
    g1_resp = client.post(
        "/api/v1/rounds/2/game/submit",
        json={
            "gameNumber": 1,
            "placements": [
                {"teamId": t1, "placement": 1, "points": 100},
                {"teamId": t2, "placement": 2, "points": 80},
            ]
        },
        headers=marshal_headers
    )
    assert g1_resp.status_code == 200

    # Submit Game 2 results
    client.post(
        "/api/v1/rounds/2/game/submit",
        json={
            "gameNumber": 2,
            "placements": [
                {"teamId": t1, "placement": 2, "points": 80},
                {"teamId": t2, "placement": 1, "points": 100},
            ]
        },
        headers=marshal_headers
    )

    standings = client.get("/api/v1/rounds/2/standings").json()["data"]
    s_map = {s["teamId"]: s for s in standings}
    assert s_map[t1]["totalPoints"] == 180.0
    assert s_map[t2]["totalPoints"] == 180.0
    assert s_map[t1]["gamesPlayed"] == 2


def test_round3_black_market_economy_and_transfers(client: TestClient, organizer_headers: dict, marshal_headers: dict):
    t1 = client.post("/api/v1/teams", json={"name": "Foxtrot", "identifier": "T06"}, headers=organizer_headers).json()["data"]["id"]
    t2 = client.post("/api/v1/teams", json={"name": "Golf", "identifier": "T07"}, headers=organizer_headers).json()["data"]["id"]

    # Initial balance is 100.0 each.
    # T1 earns 50 pts
    tx_earn = client.post(
        "/api/v1/rounds/3/transactions",
        json={"teamId": t1, "amount": 50.0, "type": "earn", "reason": "Station Challenge Bounty"},
        headers=marshal_headers
    )
    assert tx_earn.status_code == 200
    tx_id = tx_earn.json()["data"]["id"]

    # T1 transfers 30 pts to T2
    transfer_resp = client.post(
        "/api/v1/rounds/3/transfer",
        json={"fromTeamId": t1, "toTeamId": t2, "amount": 30.0, "reason": "Secret Document Purchase"},
        headers=marshal_headers
    )
    assert transfer_resp.status_code == 200

    # Check standings: T1 should have 100 + 50 - 30 = 120; T2 should have 100 + 30 = 130
    st = {s["teamId"]: s for s in client.get("/api/v1/rounds/3/standings").json()["data"]}
    assert st[t1]["currentBalance"] == 1020.0  # Section 3.3: start on 1,000
    assert st[t2]["currentBalance"] == 1030.0

    # Reversal of earn transaction
    rev_resp = client.post(f"/api/v1/rounds/3/transactions/{tx_id}/reverse", headers=organizer_headers)
    assert rev_resp.status_code == 200

    # Check updated balance: T1 has 1020 - 50 = 970.0 (Section 3.3: start on 1,000)
    st_after = {s["teamId"]: s for s in client.get("/api/v1/rounds/3/standings").json()["data"]}
    assert st_after[t1]["currentBalance"] == 970.0

    # Update code fragment discovery
    frag_resp = client.put(
        "/api/v1/rounds/3/codes/fragment",
        json={"teamId": t1, "fragmentIndex": 0, "code": "SIGMA-99", "isDiscovered": True, "clueStation": "Station 4"},
        headers=marshal_headers
    )
    assert frag_resp.status_code == 200
    assert frag_resp.json()["data"]["fragments"][0]["isDiscovered"] is True


def test_round4_courtroom_pairings_and_scoring(client: TestClient, organizer_headers: dict, marshal_headers: dict):
    t_a = client.post("/api/v1/teams", json={"name": "Prosecution Masters", "identifier": "T08"}, headers=organizer_headers).json()["data"]["id"]
    t_b = client.post("/api/v1/teams", json={"name": "Defense Titans", "identifier": "T09"}, headers=organizer_headers).json()["data"]["id"]

    # Update Pair 1
    pair_resp = client.put(
        "/api/v1/rounds/4/pairs/1",
        json={
            "caseId": "case-alpha",
            "caseName": "AI Intellectual Property Dispute",
            "teamASide": "Prosecution",
            "teamBSide": "Defense",
            "teamAHasCaseFile": True,
            "teamBHasCaseFile": True,
            "resourcePersonName": "Dr. Vance",
            "resourcePersonQuestions": [
                {"teamId": t_a, "question": "What was the timestamp of the commit?", "answer": "23:14 UTC"}
            ],
            "isConfirmed": True
        },
        headers=marshal_headers
    )
    assert pair_resp.status_code == 200
    pdata = pair_resp.json()["data"]
    assert pdata["caseId"] == "case-alpha"
    assert pdata["teamAHasCaseFile"] is True
    assert len(pdata["resourcePersonQuestions"]) == 1

    # Submit Judge Score
    score_resp = client.post(
        "/api/v1/rounds/4/scores",
        json={
            "judgeId": "judge-101",
            "judgeName": "Prof. Harrison",
            "teamId": t_a,
            "scores": {"arguments": 28.0, "crossExam": 24.0, "evidence": 23.0, "demeanor": 18.0},
            "comments": "Superb rebuttal arguments"
        },
        headers=marshal_headers
    )
    assert score_resp.status_code == 200
    assert score_resp.json()["data"]["totalScore"] == 93.0

    # Submit Agent Guess
    guess_resp = client.post(
        "/api/v1/rounds/4/agent-guess",
        json={"teamId": t_a, "outcome": "correct", "pointsAwarded": 10.0, "notes": "Identified the double agent"},
        headers=marshal_headers
    )
    assert guess_resp.status_code == 200

    # Check Standings: total = 93.0 (pure Legal Battle rubric score, max 100)
    st4 = {s["teamId"]: s for s in client.get("/api/v1/rounds/4/standings").json()["data"]}
    assert st4[t_a]["juryScore"] == 93.0
    assert st4[t_a]["totalScore"] == 93.0


def test_grand_finale_and_podium(client: TestClient, organizer_headers: dict, marshal_headers: dict):
    t_champ = client.post("/api/v1/teams", json={"name": "Imperial Champions", "identifier": "T10"}, headers=organizer_headers).json()["data"]["id"]

    # Submit Finale Scorecard
    sc_resp = client.post(
        "/api/v1/rounds/5/scorecards",
        json={
            "teamId": t_champ,
            "judgeName": "Grand Finale Jury",
            "scores": {"opening": 20.0, "debate": 39.0, "rebuttal": 25.0, "poise": 15.0},
            "comments": "Masterful debate performance"
        },
        headers=marshal_headers
    )
    assert sc_resp.status_code == 200
    assert sc_resp.json()["data"]["totalScore"] == 99.0

    # Submit Agent Verdict
    verd_resp = client.post(
        "/api/v1/rounds/5/agent-verdict",
        json={
            "teamId": t_champ,
            "suspectedAgent": "Agent Cobalt",
            "actualAgent": "Agent Cobalt",
            "isCorrect": True,
            "bonusPoints": 10.0,
            "notes": "Flawlessly deduced from clue trail"
        },
        headers=marshal_headers
    )
    assert verd_resp.status_code == 200

    # Check Standings
    fin_standings = client.get("/api/v1/rounds/5/standings").json()["data"]
    assert len(fin_standings) >= 1
    assert fin_standings[0]["teamId"] == t_champ
    assert fin_standings[0]["grandTotalScore"] == 109.0
    assert fin_standings[0]["podiumTitle"] == "Champion"


def test_round_finalization_gates_and_progression(client: TestClient, organizer_headers: dict):
    # Attempting to finalize Round 2 before Round 1 must fail
    bad_finalize = client.post("/api/v1/rounds/2/finalize", json={}, headers=organizer_headers)
    assert bad_finalize.status_code == 400
    assert "not finalized yet" in bad_finalize.json()["message"]

    # Finalize Round 1 with overrideDiscrepancy=True
    r1_fin = client.post("/api/v1/rounds/1/finalize", json={"overrideDiscrepancy": True}, headers=organizer_headers)
    assert r1_fin.status_code == 200
    assert r1_fin.json()["data"]["isFinalized"] if "isFinalized" in r1_fin.json()["data"] else r1_fin.json()["data"]["success"] is True

    # Check Round 1 is now marked completed and finalized
    r1_state = client.get("/api/v1/rounds/1").json()["data"]
    assert r1_state["isFinalized"] is True
    assert r1_state["status"] == "Completed"

    # Now Round 2 can be finalized with override
    r2_fin = client.post("/api/v1/rounds/2/finalize", json={"overrideDiscrepancy": True}, headers=organizer_headers)
    assert r2_fin.status_code == 200


def test_finalized_round_immutability(client: TestClient, organizer_headers: dict, marshal_headers: dict):
    # Create team
    t_resp = client.post("/api/v1/teams", json={"name": "Immutable Squad", "identifier": "T11"}, headers=organizer_headers)
    t_id = t_resp.json()["data"]["id"]

    # Finalize Round 1
    client.post("/api/v1/rounds/1/finalize", json={"overrideDiscrepancy": True}, headers=organizer_headers)

    # Attempt mutation on Round 1 -> must return 400
    r1_mut = client.put(
        f"/api/v1/rounds/1/records/{t_id}",
        json={"miniRounds": [{"roundNumber": 1, "durationSeconds": 100, "isCompleted": True}]},
        headers=marshal_headers
    )
    assert r1_mut.status_code == 400
    assert "finalized and sealed" in r1_mut.json()["message"]

    # Finalize Round 2
    client.post("/api/v1/rounds/2/finalize", json={"overrideDiscrepancy": True}, headers=organizer_headers)

    # Attempt mutation on Round 2 -> must return 400
    r2_mut = client.post(
        "/api/v1/rounds/2/placements",
        json={"gameNumber": 1, "teamId": t_id, "placement": 1, "points": 100},
        headers=marshal_headers
    )
    assert r2_mut.status_code == 400
    assert "finalized and sealed" in r2_mut.json()["message"]

    # Finalize Round 3
    client.post("/api/v1/rounds/3/finalize", json={"overrideDiscrepancy": True}, headers=organizer_headers)

    # Attempt mutation on Round 3 -> must return 400
    r3_mut = client.post(
        "/api/v1/rounds/3/transactions",
        json={"teamId": t_id, "amount": 10.0, "type": "earn", "reason": "Post-final Bounty"},
        headers=marshal_headers
    )
    assert r3_mut.status_code == 400
    assert "finalized and sealed" in r3_mut.json()["message"]


def test_nonexistent_team_validation_returns_404(client: TestClient, organizer_headers: dict, marshal_headers: dict):
    fake_id = "00000000-0000-0000-0000-000000000000"

    # Round 1
    r1 = client.put(f"/api/v1/rounds/1/records/{fake_id}", json={"hiddenCodeRecovered": True}, headers=marshal_headers)
    assert r1.status_code == 404

    # Round 2
    r2 = client.post("/api/v1/rounds/2/placements", json={"gameNumber": 1, "teamId": fake_id, "placement": 1}, headers=marshal_headers)
    assert r2.status_code == 404

    # Round 3
    r3 = client.post("/api/v1/rounds/3/transactions", json={"teamId": fake_id, "amount": 20.0, "type": "earn", "reason": "Test"}, headers=marshal_headers)
    assert r3.status_code == 404

    # Round 4
    r4 = client.post("/api/v1/rounds/4/scores", json={"judgeId": "j1", "judgeName": "Judge", "teamId": fake_id, "scores": {"a": 10.0}}, headers=marshal_headers)
    assert r4.status_code == 404

    # Round 5
    r5 = client.post("/api/v1/rounds/5/scorecards", json={"teamId": fake_id, "judgeName": "Grand Jury", "scores": {"a": 10.0}}, headers=marshal_headers)
    assert r5.status_code == 404


def test_round1_tiebreaker_fastest_mini_round_logic(client: TestClient, organizer_headers: dict, marshal_headers: dict):
    # Team X: 100s + 100s + 100s = 300s. Fastest = 100s.
    # Team Y: 80s + 120s + 100s = 300s. Fastest = 80s.
    t_x = client.post("/api/v1/teams", json={"name": "Team Consistent", "identifier": "T12"}, headers=organizer_headers).json()["data"]["id"]
    t_y = client.post("/api/v1/teams", json={"name": "Team Burst", "identifier": "T13"}, headers=organizer_headers).json()["data"]["id"]

    client.put(
        f"/api/v1/rounds/1/records/{t_x}",
        json={
            "miniRounds": [
                {"roundNumber": 1, "durationSeconds": 100, "hintsUsed": 0, "isCompleted": True},
                {"roundNumber": 2, "durationSeconds": 100, "hintsUsed": 0, "isCompleted": True},
                {"roundNumber": 3, "durationSeconds": 100, "hintsUsed": 0, "isCompleted": True},
            ]
        },
        headers=marshal_headers
    )

    client.put(
        f"/api/v1/rounds/1/records/{t_y}",
        json={
            "miniRounds": [
                {"roundNumber": 1, "durationSeconds": 80, "hintsUsed": 0, "isCompleted": True},
                {"roundNumber": 2, "durationSeconds": 120, "hintsUsed": 0, "isCompleted": True},
                {"roundNumber": 3, "durationSeconds": 100, "hintsUsed": 0, "isCompleted": True},
            ]
        },
        headers=marshal_headers
    )

    records = {r["teamId"]: r for r in client.get("/api/v1/rounds/1/records").json()["data"]}
    # Team Y should rank higher because fastest mini round is 80s < 100s
    assert records[t_y]["rank"] < records[t_x]["rank"]
    assert records[t_y]["adjustedTotalSeconds"] == records[t_x]["adjustedTotalSeconds"]


def test_repeated_finalization_is_idempotent_with_audit(client: TestClient, organizer_headers: dict):
    # Finalize Round 1 with discrepancy override and notes
    r1_fin = client.post(
        "/api/v1/rounds/1/finalize",
        json={"overrideDiscrepancy": True, "notes": "Approved by Chief Judge for early round simulation"},
        headers=organizer_headers
    )
    assert r1_fin.status_code == 200
    assert r1_fin.json()["data"]["success"] is True

    # Check that audit information is preserved
    r1_state = client.get("/api/v1/rounds/1").json()["data"]
    audit = r1_state["configJson"].get("finalizationAudit")
    assert audit is not None
    assert audit["overrideDiscrepancy"] is True
    assert "Chief Judge" in audit["notes"]

    # Finalize Round 1 AGAIN (Idempotency check)
    r1_repeat = client.post(
        "/api/v1/rounds/1/finalize",
        json={"overrideDiscrepancy": True},
        headers=organizer_headers
    )
    assert r1_repeat.status_code == 200
    assert "already finalized" in r1_repeat.json()["data"]["message"]

