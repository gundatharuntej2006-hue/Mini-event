import pytest
from app.services import round1_service, round2_service, round3_service, round4_service, finale_service
def test_full_tournament_e2e_flow(client, db_session, organizer_headers, marshal_headers, judge_headers):
    """
    End-to-end automated simulation of the entire EVENT HQ tournament:
    32 teams (R1) -> 24 teams (R2) -> 12 teams (R3) -> 8 teams (R4) -> 3 teams (Finale) -> Podium champion
    """
    from datetime import datetime, timezone, timedelta
    base = datetime(2026, 9, 19, 9, 0, 0, tzinfo=timezone.utc)

    # -------------------------------------------------------------
    # 1. ROUND 1: THE GREAT EXPEDITION (32 teams -> 24 advance)
    # -------------------------------------------------------------
    for i in range(32):
        t_id = f"team-{i + 1}"
        # Team 1 is fastest, Team 32 is slowest. No ties.
        dur1 = 300 + i * 20
        dur2 = 350 + i * 20
        dur3 = 400 + i * 20

        for mr_num, dur in [(1, dur1), (2, dur2), (3, dur3)]:
            client.post(
                f"/api/rounds/1/teams/{t_id}/timings",
                json={
                    "mini_round_number": mr_num,
                    "start_time": base.isoformat(),
                    "completion_time": (base + timedelta(seconds=dur)).isoformat(),
                    "hints_used": 0
                },
                headers=marshal_headers
            )

    # Verify R1 overview & finalize
    r1_check = client.get("/api/rounds/1/qualification", headers=organizer_headers).json()["data"]
    assert r1_check["can_finalize"] is True
    assert r1_check["completed_count"] == 32

    r1_fin = client.post("/api/rounds/1/finalize", headers=organizer_headers).json()["data"]
    assert r1_fin["finalized"] is True
    assert len(r1_fin["advancing_team_ids"]) == 24
    r2_teams = r1_fin["advancing_team_ids"]
    assert r2_teams == [f"team-{i + 1}" for i in range(24)]

    # -------------------------------------------------------------
    # 2. ROUND 2: CABO (24 teams -> 12 advance)
    # -------------------------------------------------------------
    for g_num in [1, 2, 3]:
        # Placements: team-1 gets 1st, team-24 gets 24th
        placements = [
            {"team_id": f"team-{i + 1}", "placement": i + 1}
            for i in range(24)
        ]
        res = client.post(f"/api/rounds/2/games?game_number={g_num}", json={"placements": placements}, headers=marshal_headers)
        assert res.status_code == 200

    r2_check = client.get("/api/rounds/2/qualification", headers=organizer_headers).json()["data"]
    assert r2_check["can_finalize"] is True

    r2_fin = client.post("/api/rounds/2/finalize", headers=organizer_headers).json()["data"]
    assert r2_fin["finalized"] is True
    assert len(r2_fin["advancing_team_ids"]) == 12
    r3_teams = r2_fin["advancing_team_ids"]
    assert r3_teams == [f"team-{i + 1}" for i in range(12)]

    # -------------------------------------------------------------
    # 3. ROUND 3: THE BLACK MARKET (12 teams -> 8 advance)
    # -------------------------------------------------------------
    # Confirm scoring rules first
    client.put("/api/rounds/3/config", json={"is_scoring_configured": True}, headers=organizer_headers)

    # Give varying earned amounts to teams (Team 1 earns most)
    for i in range(12):
        t_id = f"team-{i + 1}"
        earn_amt = 100.0 - i * 5
        client.post(
            f"/api/rounds/3/teams/{t_id}/transactions",
            json={"amount": earn_amt, "type": "earn", "reason": "Asset trade"},
            headers=marshal_headers
        )

    r3_check = client.get("/api/rounds/3/qualification", headers=organizer_headers).json()["data"]
    assert r3_check["can_finalize"] is True

    r3_fin = client.post("/api/rounds/3/finalize", headers=organizer_headers).json()["data"]
    assert r3_fin["finalized"] is True
    assert len(r3_fin["advancing_team_ids"]) == 8
    r4_teams = r3_fin["advancing_team_ids"]
    assert r4_teams == [f"team-{i + 1}" for i in range(8)]

    # -------------------------------------------------------------
    # 4. ROUND 4: THE LEGAL BATTLE (8 teams -> 3 advance)
    # -------------------------------------------------------------
    # Assign 4 pairs
    for p_num in range(1, 5):
        tA = f"team-{p_num * 2 - 1}"
        tB = f"team-{p_num * 2}"
        client.post(
            "/api/rounds/4/pairs",
            json={
                "pair_number": p_num,
                "team_a_id": tA,
                "team_b_id": tB,
                "case_name": f"Legal Case {p_num}",
                "team_a_side": "Prosecution / Plaintiff",
                "team_b_side": "Defense / Respondent"
            },
            headers=organizer_headers
        )

    # Confirm pairings
    client.post("/api/rounds/4/pairs/confirm", headers=organizer_headers)

    # Complete hearing stages for all 4 pairs
    for p_num in range(1, 5):
        for st_id in ["hearing_1", "file_exchange", "hearing_2"]:
            client.put(
                f"/api/rounds/4/stages/pair-{p_num}/{st_id}",
                json={"status": "completed", "actual_duration_seconds": 1200},
                headers=marshal_headers
            )

    # Submit faculty judge scorecards
    for i in range(8):
        t_id = f"team-{i + 1}"
        # Team 1 gets highest scores
        score_val = 18.0 - i * 1.0
        client.post(
            f"/api/rounds/4/judging/{t_id}/scores",
            json={
                "judge_id": "judge-faculty-1",
                "judge_name": "Chief Justice",
                "scores": {
                    "logical_structure": score_val,
                    "evidence_use": score_val,
                    "rebuttal": score_val
                }
            },
            headers=judge_headers
        )

    # Confirm scoring formula
    client.put(
        "/api/rounds/4/config",
        json={
            "final_score_formula": {
                "panelScoreWeight": 1.0,
                "agentGuessingWeight": 1.0,
                "blackMarketWeightPercent": 10,
                "isFormulaConfirmed": True
            },
            "advancing_teams_count": 3
        },
        headers=organizer_headers
    )

    r4_check = client.get("/api/rounds/4/qualification", headers=organizer_headers).json()["data"]
    assert r4_check["can_finalize"] is True

    r4_fin = client.post("/api/rounds/4/finalize", headers=organizer_headers).json()["data"]
    assert r4_fin["finalized"] is True
    assert len(r4_fin["advancing_team_ids"]) == 3
    finale_teams = r4_fin["advancing_team_ids"]
    assert finale_teams == ["team-1", "team-2", "team-3"]

    # -------------------------------------------------------------
    # 5. GRAND FINALE: PODIUM CHAMPIONSHIP (3 teams -> Champion)
    # -------------------------------------------------------------
    # Confirm rules
    client.put("/api/rounds/finale/config", json={"is_scoring_rules_confirmed": True}, headers=organizer_headers)

    # Submit scorecards for all 3 finalists
    for i, t_id in enumerate(finale_teams):
        score_val = 45.0 - i * 5.0
        client.post(
            f"/api/rounds/finale/scorecards/{t_id}",
            json={
                "judge_name": "Grand Tribunal Inquisitor",
                "scores": {
                    "climax_defense": score_val,
                    "cross_examination": 25.0 - i * 2,
                    "synergy_decorum": 18.0
                }
            },
            headers=judge_headers
        )

    fin_check = client.get("/api/rounds/finale/qualification", headers=organizer_headers).json()["data"]
    assert fin_check["can_finalize"] is True

    finale_fin = client.post("/api/rounds/finale/finalize", headers=organizer_headers).json()["data"]
    assert finale_fin["finalized"] is True
    assert finale_fin["champion_team_id"] == "team-1"

    # Verify Leaderboard shows Podium Honors
    leaderboard = client.get("/api/rounds/finale/leaderboard", headers=organizer_headers).json()["data"]
    assert len(leaderboard) == 3
    assert leaderboard[0]["team_id"] == "team-1"
    assert leaderboard[0]["placement_title"] == "Grand Champion"
    assert leaderboard[1]["team_id"] == "team-2"
    assert leaderboard[1]["placement_title"] == "1st Runner Up"
    assert leaderboard[2]["team_id"] == "team-3"
    assert leaderboard[2]["placement_title"] == "2nd Runner Up"

    # Verify Audit Logs captured all actions
    audit_res = client.get("/api/audit/logs?limit=100", headers=organizer_headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()["data"]
    assert len(logs) > 50  # Over 50 auditable events recorded
