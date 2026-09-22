import pytest
from fastapi.testclient import TestClient

def test_full_organizer_tournament_e2e_lifecycle(client: TestClient, organizer_headers: dict, marshal_headers: dict, judge_headers: dict):
    # ---------------------------------------------------------
    # 1. Organizer Login & Role Authorization Verification
    # ---------------------------------------------------------
    login_resp = client.post("/api/v1/auth/login", json={"email": "organizer@bmsit.in", "password": "DefaultPassword123!"})
    # If using test fixture organizer
    # Try invalid login
    bad_login = client.post("/api/v1/auth/login", json={"email": "organizer@bmsit.in", "password": "WrongPassword"})
    assert bad_login.status_code == 401

    # Verify Current User Profile
    me_resp = client.get("/api/v1/auth/me", headers=organizer_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["role"] == "ORGANIZER"

    # ---------------------------------------------------------
    # 2. Configure Event Settings
    # ---------------------------------------------------------
    settings_update = client.put(
        "/api/v1/settings",
        json={"eventName": "BMSIT Grand Tournament 2026", "tableCount": 32},
        headers=organizer_headers
    )
    assert settings_update.status_code == 200
    assert settings_update.json()["data"]["eventName"] == "BMSIT Grand Tournament 2026"
    assert settings_update.json()["data"]["tableCount"] == 32

    # ---------------------------------------------------------
    # 3. Create Teams and Participants (Check Capacity Limits)
    # ---------------------------------------------------------
    team_ids = []
    for i in range(1, 33):
        t_res = client.post(
            "/api/v1/teams",
            json={"name": f"Squad {i:02d}", "identifier": f"T{i:02d}", "assignedTable": f"Table {i}"},
            headers=organizer_headers
        )
        assert t_res.status_code in (200, 201)
        team_ids.append(t_res.json()["data"]["id"])

    # Create 5 participants for Team 1
    t1_id = team_ids[0]
    p_ids = []
    for j in range(1, 6):
        p_res = client.post(
            "/api/v1/participants",
            json={
                "name": f"Participant {j}",
                "email": f"p{j}_team1@bmsit.in",
                "phone": f"987654321{j}",
                "usn": f"1BY22CS00{j}",
                "teamId": t1_id,
                "role": "Leader" if j == 1 else "Member"
            },
            headers=marshal_headers
        )
        assert p_res.status_code in (200, 201)
        p_ids.append(p_res.json()["data"]["id"])

    # Attempt to add 6th member to Team 1 -> Should fail with 400 (5-person capacity limit)
    p6_fail = client.post(
        "/api/v1/participants",
        json={
            "name": "Participant 6 (Overflow)",
            "email": "p6_team1@bmsit.in",
            "usn": "1BY22CS099",
            "teamId": t1_id,
            "role": "Member"
        },
        headers=marshal_headers
    )
    assert p6_fail.status_code == 400
    assert "maximum squad limit" in p6_fail.json()["message"]

    # Toggle Check-In
    checkin_res = client.patch(f"/api/v1/participants/{p_ids[0]}/check-in", json={"checkedIn": True}, headers=marshal_headers)
    assert checkin_res.status_code == 200
    assert checkin_res.json()["data"]["checkedIn"] is True

    # ---------------------------------------------------------
    # 4. Round 1: Clue Hunt Scoring & Progression
    # ---------------------------------------------------------
    # Submit completed mini-rounds for all teams
    for idx, tid in enumerate(team_ids):
        # Teams 1..24 have fast times; 25..32 have slower times
        base_dur = 100 + (idx * 5)
        hints = 1 if idx % 4 == 0 else 0
        r1_update = client.put(
            f"/api/v1/rounds/1/records/{tid}",
            json={
                "miniRounds": [
                    {"roundNumber": 1, "durationSeconds": base_dur, "hintsUsed": 0, "isCompleted": True},
                    {"roundNumber": 2, "durationSeconds": base_dur + 10, "hintsUsed": hints, "isCompleted": True},
                    {"roundNumber": 3, "durationSeconds": base_dur + 20, "hintsUsed": 0, "isCompleted": True},
                ],
                "hiddenCodeRecovered": (idx == 0)
            },
            headers=marshal_headers
        )
        assert r1_update.status_code == 200

    # Finalize Round 1 -> Top 24 advance
    r1_fin = client.post("/api/v1/rounds/1/finalize", json={"overrideDiscrepancy": True}, headers=organizer_headers)
    assert r1_fin.status_code == 200
    assert r1_fin.json()["data"]["totalEligible"] == 24

    # Verify Round 1 is locked against mutations
    r1_locked_mut = client.put(
        f"/api/v1/rounds/1/records/{t1_id}",
        json={"miniRounds": [{"roundNumber": 1, "durationSeconds": 50, "isCompleted": True}]},
        headers=marshal_headers
    )
    assert r1_locked_mut.status_code == 400
    assert "finalized and sealed" in r1_locked_mut.json()["message"]

    # ---------------------------------------------------------
    # 5. Round 2: Cabo Tournament Scoring & Progression
    # ---------------------------------------------------------
    # Submit 3 games for top 24 teams
    top_24_ids = team_ids[:24]
    for g in [1, 2, 3]:
        placements = []
        for p_idx, tid in enumerate(top_24_ids):
            placements.append({
                "teamId": tid,
                "placement": p_idx + 1,
                "points": max(0, 100 - p_idx * 5)
            })
        g_res = client.post("/api/v1/rounds/2/game/submit", json={"gameNumber": g, "placements": placements}, headers=marshal_headers)
        assert g_res.status_code == 200

    # Finalize Round 2 -> Top 12 advance
    r2_fin = client.post("/api/v1/rounds/2/finalize", json={"overrideDiscrepancy": True}, headers=organizer_headers)
    assert r2_fin.status_code == 200

    # ---------------------------------------------------------
    # 6. Round 3: The Black Market Economy & Transfers
    # ---------------------------------------------------------
    top_12_ids = team_ids[:12]
    # Team 1 earns 80 points
    tx_res = client.post(
        "/api/v1/rounds/3/transactions",
        json={"teamId": top_12_ids[0], "amount": 80.0, "type": "earn", "reason": "Decryption Challenge"},
        headers=marshal_headers
    )
    assert tx_res.status_code == 200

    # Team 1 transfers 20 points to Team 2
    xfer_res = client.post(
        "/api/v1/rounds/3/transfer",
        json={"fromTeamId": top_12_ids[0], "toTeamId": top_12_ids[1], "amount": 20.0, "reason": "Secret Key Purchase"},
        headers=marshal_headers
    )
    assert xfer_res.status_code == 200

    # Team 1 updates all 4 code fragments
    for f_idx in range(4):
        frag_res = client.put(
            "/api/v1/rounds/3/codes/fragment",
            json={"teamId": top_12_ids[0], "fragmentIndex": f_idx, "code": f"CODE-SEG-{f_idx}", "isDiscovered": True},
            headers=marshal_headers
        )
        assert frag_res.status_code == 200

    # Finalize Round 3 -> Top 8 advance
    r3_fin = client.post("/api/v1/rounds/3/finalize", json={"overrideDiscrepancy": True}, headers=organizer_headers)
    assert r3_fin.status_code == 200

    # ---------------------------------------------------------
    # 7. Round 4: The Legal Battle
    # ---------------------------------------------------------
    top_8_ids = team_ids[:8]
    # Auto-pair into 4 courtroom matchups
    autopair_res = client.post("/api/v1/rounds/4/pairs/auto", headers=organizer_headers)
    assert autopair_res.status_code == 200

    # Faculty Judges submit rubric scorecards
    for tid in top_8_ids:
        score_res = client.post(
            "/api/v1/rounds/4/scores",
            json={
                "judgeId": "faculty-judge-01",
                "judgeName": "Dr. Aris",
                "teamId": tid,
                "scores": {"arguments": 25.0, "crossExam": 25.0, "evidence": 20.0, "demeanor": 18.0}
            },
            headers=judge_headers
        )
        assert score_res.status_code == 200

    # Submit Agent Guess for Team 1
    client.post(
        "/api/v1/rounds/4/agent-guess",
        json={"teamId": top_8_ids[0], "outcome": "correct", "pointsAwarded": 10.0},
        headers=marshal_headers
    )

    # Finalize Round 4 -> Top 3 advance
    r4_fin = client.post("/api/v1/rounds/4/finalize", json={"overrideDiscrepancy": True}, headers=organizer_headers)
    assert r4_fin.status_code == 200

    # ---------------------------------------------------------
    # 8. Grand Finale (Round 5) & Championship Podium
    # ---------------------------------------------------------
    top_3_ids = top_8_ids[:3]

    # Grand Jury scorecards
    client.post(
        "/api/v1/rounds/5/scorecards",
        json={"teamId": top_3_ids[0], "judgeName": "Chief Tribunal", "scores": {"opening": 25, "debate": 45, "rebuttal": 20, "poise": 10}},
        headers=judge_headers
    )
    client.post(
        "/api/v1/rounds/5/scorecards",
        json={"teamId": top_3_ids[1], "judgeName": "Chief Tribunal", "scores": {"opening": 20, "debate": 40, "rebuttal": 18, "poise": 8}},
        headers=judge_headers
    )
    client.post(
        "/api/v1/rounds/5/scorecards",
        json={"teamId": top_3_ids[2], "judgeName": "Chief Tribunal", "scores": {"opening": 18, "debate": 35, "rebuttal": 15, "poise": 7}},
        headers=judge_headers
    )

    # Secret Agent Verdicts
    client.post(
        "/api/v1/rounds/5/agent-verdict",
        json={"teamId": top_3_ids[0], "suspectedAgent": "Agent Zero", "actualAgent": "Agent Zero", "isCorrect": True, "bonusPoints": 10.0},
        headers=organizer_headers
    )

    # Check Standings and Podium Titles
    finale_standings = client.get("/api/v1/rounds/5/standings").json()["data"]
    assert len(finale_standings) == 3
    assert finale_standings[0]["teamId"] == top_3_ids[0]
    assert finale_standings[0]["rank"] == 1
    assert finale_standings[0]["podiumTitle"] == "Champion"
    assert finale_standings[1]["podiumTitle"] == "1st Runner Up"
    assert finale_standings[2]["podiumTitle"] == "2nd Runner Up"

    # Finalize Finale
    r5_fin = client.post("/api/v1/rounds/5/finalize", json={"overrideDiscrepancy": True}, headers=organizer_headers)
    assert r5_fin.status_code == 200
    assert r5_fin.json()["data"]["success"] is True

    # ---------------------------------------------------------
    # 9. Dashboard Overview Metrics Check
    # ---------------------------------------------------------
    overview = client.get("/api/v1/dashboard/overview", headers=organizer_headers)
    assert overview.status_code == 200
    data = overview.json()["data"]
    assert data["stats"]["totalTeams"] == 32
    assert data["stats"]["totalParticipants"] == 5
