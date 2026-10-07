import pytest
from datetime import datetime, timezone, timedelta
from app.scoring.round1_scoring import compute_mini_round, compute_team_totals, process_round1_standings

def test_mini_round_duration_and_penalties():
    start = "2026-09-19T10:00:00Z"
    end = "2026-09-19T10:15:00Z"
    mr = {
        "mini_round_number": 1,
        "start_time": start,
        "completion_time": end,
        "hints_used": 2,                     # 2 * 300s = 600s
        "phone_penalties_count": 1,          # 1 * 600s = 600s
        "separation_penalties_count": 1,     # 1 * 300s = 300s
        "clue_tampering_deduction": 0,
        "checkpoints": []
    }
    result = compute_mini_round(
        mr,
        penalty_per_hint_seconds=300,
        phone_penalty_seconds=600,
        separation_penalty_seconds=300
    )
    assert result["duration_seconds"] == 900
    assert result["hint_penalty_seconds"] == 600
    assert result["phone_penalty_seconds"] == 600
    assert result["separation_penalty_seconds"] == 300
    assert result["adjusted_seconds"] == 900 + 600 + 600 + 300  # 2400s
    assert result["status"] == "Completed"
    assert result["gate_name"] == "Gate 1 — The Signal Scramble"

def test_mini_round_incomplete_stays_null():
    mr = {
        "mini_round_number": 1,
        "start_time": "2026-09-19T10:00:00Z",
        "completion_time": None,
        "hints_used": 1,
        "checkpoints": []
    }
    result = compute_mini_round(mr, penalty_per_hint_seconds=300)
    assert result["duration_seconds"] is None
    assert result["adjusted_seconds"] is None
    assert result["status"] == "In Progress"

def test_incomplete_team_totals_and_unranked():
    rec = {
        "team_id": "team-1",
        "team_number": 1,
        "team_name": "Squad 1",
        "mini_rounds": [
            {"mini_round_number": 1, "start_time": "2026-09-19T10:00:00Z", "completion_time": "2026-09-19T10:10:00Z", "hints_used": 0},
            {"mini_round_number": 2, "start_time": "2026-09-19T10:15:00Z", "completion_time": None, "hints_used": 0},
            {"mini_round_number": 3, "start_time": None, "completion_time": None, "hints_used": 0}
        ]
    }
    totals = compute_team_totals(rec, 300)
    assert totals["is_complete"] is False
    assert totals["raw_total_seconds"] is None
    assert totals["adjusted_total_seconds"] is None

def test_round1_fastest_gate_tie_breaker():
    records = [
        {
            "team_id": "team-1",
            "team_number": 1,
            "team_name": "Team 1",
            "mini_rounds": [
                {"mini_round_number": 1, "start_time": "2026-09-19T10:00:00Z", "completion_time": "2026-09-19T10:10:00Z", "hints_used": 0},  # 600s
                {"mini_round_number": 2, "start_time": "2026-09-19T10:20:00Z", "completion_time": "2026-09-19T10:30:00Z", "hints_used": 0},  # 600s
                {"mini_round_number": 3, "start_time": "2026-09-19T10:40:00Z", "completion_time": "2026-09-19T10:50:00Z", "hints_used": 0}   # 600s (fastest: 600s)
            ]
        },
        {
            "team_id": "team-2",
            "team_number": 2,
            "team_name": "Team 2",
            "mini_rounds": [
                {"mini_round_number": 1, "start_time": "2026-09-19T10:00:00Z", "completion_time": "2026-09-19T10:08:00Z", "hints_used": 0},  # 480s (fastest: 480s)
                {"mini_round_number": 2, "start_time": "2026-09-19T10:20:00Z", "completion_time": "2026-09-19T10:32:00Z", "hints_used": 0},  # 720s
                {"mini_round_number": 3, "start_time": "2026-09-19T10:40:00Z", "completion_time": "2026-09-19T10:50:00Z", "hints_used": 0}   # 600s
            ]
        }
    ]
    standings = process_round1_standings(records, 300, False)
    # Team 2 must be ranked #1 because fastest gate 480s < 600s
    assert standings["records"][0]["team_id"] == "team-2"
    assert standings["records"][0]["rank"] == 1
    assert standings["records"][1]["team_id"] == "team-1"
    assert standings["records"][1]["rank"] == 2

def test_round1_rank_points_distribution():
    records = []
    base = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(32):
        team_num = i + 1
        t_sec = 600 + i * 30
        records.append({
            "team_id": f"team-{team_num}",
            "team_number": team_num,
            "team_name": f"Team {team_num}",
            "mini_rounds": [
                {"mini_round_number": 1, "start_time": base.isoformat(), "completion_time": (base + timedelta(seconds=t_sec)).isoformat(), "hints_used": 0},
                {"mini_round_number": 2, "start_time": base.isoformat(), "completion_time": (base + timedelta(seconds=t_sec)).isoformat(), "hints_used": 0},
                {"mini_round_number": 3, "start_time": base.isoformat(), "completion_time": (base + timedelta(seconds=t_sec)).isoformat(), "hints_used": 0},
            ]
        })
    standings = process_round1_standings(records, 300, False)
    recs = standings["records"]
    assert recs[0]["rank"] == 1
    assert recs[0]["rank_points"] == 16
    assert recs[1]["rank"] == 2
    assert recs[1]["rank_points"] == 15
    assert recs[15]["rank"] == 16
    assert recs[15]["rank_points"] == 1
    assert recs[15]["qualification_status"] == "Provisional Qualified"
    assert recs[16]["rank"] == 17
    assert recs[16]["rank_points"] == 0
    assert recs[16]["qualification_status"] == "Provisional Eliminated"

def test_round1_cutoff_boundary_tie_blocks_finalization():
    records = []
    base = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(32):
        team_num = i + 1
        # Create identical times for rank 16 and rank 17 (indices 15 and 16)
        if i < 15:
            total_sec = 1500 + i * 40
            fastest = 400 + i * 10
        elif i == 15 or i == 16:
            total_sec = 2500
            fastest = 700
        else:
            total_sec = 2600 + (i - 17) * 50
            fastest = 750 + (i - 17) * 10

        mr2 = 800
        mr3 = total_sec - fastest - mr2
        records.append({
            "team_id": f"team-{team_num}",
            "team_number": team_num,
            "team_name": f"Team {team_num}",
            "mini_rounds": [
                {"mini_round_number": 1, "start_time": base.isoformat(), "completion_time": (base + timedelta(seconds=fastest)).isoformat(), "hints_used": 0},
                {"mini_round_number": 2, "start_time": base.isoformat(), "completion_time": (base + timedelta(seconds=mr2)).isoformat(), "hints_used": 0},
                {"mini_round_number": 3, "start_time": base.isoformat(), "completion_time": (base + timedelta(seconds=mr3)).isoformat(), "hints_used": 0},
            ]
        })

    standings = process_round1_standings(records, 300, False)
    assert standings["can_finalize"] is False
    assert standings["cutoff_boundary_tie"] is True
    assert any(issue["code"] == "CUTOFF_TIE" for issue in standings["issues"])

def test_round1_api_endpoints(client, marshal_headers, organizer_headers):
    # Test GET /api/rounds/1
    res = client.get("/api/rounds/1")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data["records"]) == 32
    assert data["name"] == "The ODDyssey Protocol"
    assert data["can_finalize"] is False  # All teams initially unstarted

    # Test POST /api/rounds/1/teams/{team_id}/timings
    timing_payload = {
        "mini_round_number": 1,
        "start_time": "2026-09-19T10:00:00Z",
        "completion_time": "2026-09-19T10:12:00Z",
        "hints_used": 1,
        "phone_penalties_count": 0,
        "separation_penalties_count": 0,
        "checkpoints": [{"checkpoint_id": "cp1", "name": "GATE 42", "arrival_time": "2026-09-19T10:05:00Z"}]
    }
    t_res = client.post("/api/rounds/1/teams/team-1/timings", json=timing_payload, headers=marshal_headers)
    assert t_res.status_code == 200
    t_data = t_res.json()["data"]
    assert t_data["duration_seconds"] == 720
    assert t_data["hint_penalty_seconds"] == 300
    assert t_data["adjusted_seconds"] == 1020

    # Test Gate 1 fragment award
    f1_res = client.post("/api/rounds/1/teams/team-1/gates/1/award-fragment", headers=organizer_headers)
    assert f1_res.status_code == 200
    assert f1_res.json()["data"]["fragment"] == "ODD"

    # Test Gate 2 fragment award
    f2_res = client.post("/api/rounds/1/teams/team-1/gates/2/award-fragment", headers=organizer_headers)
    assert f2_res.status_code == 200
    assert f2_res.json()["data"]["fragment"] == "42"

    # Test Gate 3 confirmation
    g3_res = client.post("/api/rounds/1/teams/team-1/gate-3/confirm", headers=organizer_headers)
    assert g3_res.status_code == 200
    assert g3_res.json()["data"]["gate_3_confirmed"] is True

    # Test Public Checkpoint endpoint (requires NO login)
    pub_res = client.get("/api/rounds/1/gates/1/public")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()["data"]
    assert pub_data["system_status"] == "CORRUPTED"
    assert pub_data["fragment_recovered"] == "ODD"

    # Test Public Teams list for QR gate selection (requires NO login)
    teams_res = client.get("/api/rounds/1/teams/public-list")
    assert teams_res.status_code == 200
    assert len(teams_res.json()["data"]) >= 1

    # Test Gate checkin before Round 1 start is rejected with 400
    early_chk = client.post("/api/rounds/1/gates/1/checkin", json={"team_name": "Vanguard Titans"})
    assert early_chk.status_code == 400
    assert "Round 1 has not been started" in early_chk.json()["message"]

    # Start Round 1 officially
    start_res = client.post("/api/rounds/1/start", headers=organizer_headers)
    assert start_res.status_code == 200
    assert start_res.json()["data"]["is_started"] is True
    assert "started_at" in start_res.json()["data"]

    # Cannot start Round 1 twice
    start_dup = client.post("/api/rounds/1/start", headers=organizer_headers)
    assert start_dup.status_code == 400
    assert "already been started" in start_dup.json()["message"]

    # Test Gate 1 Check-in with Team Name (requires NO login)
    chk1_res = client.post("/api/rounds/1/gates/1/checkin", json={"team_name": "Vanguard Titans"})
    assert chk1_res.status_code == 200
    chk1_data = chk1_res.json()["data"]
    assert chk1_data["is_duplicate"] is False
    assert chk1_data["attempt_number"] == 1
    assert chk1_data["status"] == "VERIFIED"
    assert "scanned_at" in chk1_data
    # Verify exact navigation string from ODDyssey Organiser.html
    nav1 = chk1_data["navigation"]
    assert "ODDYSSEY NAVIGATION SYSTEM | SYSTEM STATUS: CORRUPTED | FRAGMENT 01 RECOVERED: ODD | ACCESS KEY: 42 | MAP DATA PARTIALLY RECOVERED - proceed to the marked region of the campus map to find Gate 2." in nav1["raw_text"]
    assert "Printed Fallback" in nav1["fallback_instructions"] or "Official Yellow Gate 1" in nav1["fallback_instructions"]

    # Test Repeat Scan: Duplicate submission should preserve original official timestamp
    chk1_dup = client.post("/api/rounds/1/gates/1/checkin", json={"team_name": "Vanguard Titans"})
    assert chk1_dup.status_code == 200
    chk1_dup_data = chk1_dup.json()["data"]
    assert chk1_dup_data["is_duplicate"] is True
    assert chk1_dup_data["attempt_number"] == 2
    assert chk1_dup_data["status"] == "DUPLICATE"
    assert chk1_dup_data["official_scanned_at"] == chk1_data["official_scanned_at"]

    # Test Invalid Team Name returns 404
    chk_err = client.post("/api/rounds/1/gates/1/checkin", json={"team_name": "NonExistentTeam999"})
    assert chk_err.status_code == 404

    # Test Gate 2 Check-in reveals Gate 2 navigation
    chk2_res = client.post("/api/rounds/1/gates/2/checkin", json={"team_name": "Vanguard Titans"})
    assert chk2_res.status_code == 200
    nav2 = chk2_res.json()["data"]["navigation"]
    assert "FRAGMENT 02 RECOVERED: 42" in nav2["raw_text"]
    assert "ODD · 42" in nav2["raw_text"]

    # Test Gate 3 Check-in reveals Gate 3 validation
    chk3_res = client.post("/api/rounds/1/gates/3/checkin", json={"team_name": "Vanguard Titans"})
    assert chk3_res.status_code == 200
    nav3 = chk3_res.json()["data"]["navigation"]
    assert "THE REAL ODDYSSEY BEGINS NOW. Proceed to Round 2." in nav3["raw_text"]

    # Test Organizer Check-ins feed
    feed_res = client.get("/api/rounds/1/checkins")
    assert feed_res.status_code == 200
    feed_items = feed_res.json()["data"]
    assert len(feed_items) >= 4  # Gate 1, Gate 1 dup, Gate 2, Gate 3

def test_participant_checkpoint_completion_syncs_to_official_timing(client, organizer_headers):
    # Ensure Round 1 is started
    client.post("/api/rounds/1/start", headers=organizer_headers)

    # Create participant session for team 1002 (team-2)
    sess_res = client.post("/api/rounds/1/participant/session", json={"team_identifier": "1002"})
    assert sess_res.status_code == 200
    token = sess_res.json()["data"]["session_token"]

    # Get participant state
    st_res = client.get(f"/api/rounds/1/participant/current?token={token}")
    assert st_res.status_code == 200
    cur_st = st_res.json()["data"]
    loc = cur_st["current_location_number"]

    # 1. First scan of correct location
    scan1 = client.post(f"/api/rounds/1/participant/scan?token={token}", json={"location": loc})
    assert scan1.status_code == 200
    scan1_data = scan1.json()["data"]
    assert scan1_data["valid"] is True
    assert scan1_data.get("is_duplicate") is not True
    assigned_set = scan1_data["question_set"]

    # 2. Duplicate scan of same location - must be idempotent and return is_duplicate: True
    scan2 = client.post(f"/api/rounds/1/participant/scan?token={token}", json={"location": loc})
    assert scan2.status_code == 200
    scan2_data = scan2.json()["data"]
    assert scan2_data["valid"] is True
    assert scan2_data.get("is_duplicate") is True

    # 3. Submit correct answer for CP1
    from app.services.round1_service import R1_QUESTION_KEY
    expected_ans = R1_QUESTION_KEY[assigned_set]["1"]
    ans_res = client.post(f"/api/rounds/1/participant/submit?token={token}", json={"answer": expected_ans})
    assert ans_res.status_code == 200
    assert ans_res.json()["data"]["is_correct"] is True

    # 4. Check official organizer overview
    ov_res = client.get("/api/rounds/1")
    assert ov_res.status_code == 200
    records = ov_res.json()["data"]["records"]
    t_rec = next((r for r in records if r["team_id"] == "team-2" or r["team_number"] == 2), None)
    assert t_rec is not None
    mr1 = t_rec["mini_rounds"][0]
    assert mr1["status"] == "Completed"
    assert mr1["duration_seconds"] is not None
    assert t_rec["gate_1_fragment_status"] == "RECOVERED"

    # 5. Check public scoreboard records
    pub_records_res = client.get("/api/rounds/1/records")
    assert pub_records_res.status_code == 200
    pub_recs = pub_records_res.json()["data"]
    pub_team2 = next((r for r in pub_recs if r.get("teamId") == "team-2" or r.get("team_id") == "team-2"), None)
    assert pub_team2 is not None
    mr_list = pub_team2.get("miniRounds") or pub_team2.get("mini_rounds_json")
    assert mr_list[0]["isCompleted"] is True


def test_get_round1_records_baseline_unstarted_no_crash(client):
    """
    Regression test:
    GET /api/v1/rounds/1/records must not crash when baseline teams have no timing data,
    and must correctly calculate rule penalties from MiniRoundTimingModel without AttributeError.
    """
    res = client.get("/api/v1/rounds/1/records")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    records = body["data"]
    assert len(records) > 0
    for rec in records:
        assert rec["isComplete"] is False
        assert rec["rawTotalSeconds"] is None
        assert rec["adjustedTotalSeconds"] is None
        assert rec["rank"] is None
        assert rec["qualificationStatus"] == "Incomplete"


def test_get_round1_records_fallback_when_legacy_service_raises(client, monkeypatch):
    """
    Regression test:
    GET /api/v1/rounds/1/records must fall back to round1_service.get_round1_overview
    and return all 32 baseline records even if the legacy service raises an exception.
    """
    from app.services import round_service

    def mock_broken_legacy_service(db):
        raise RuntimeError("Simulated legacy round service error")

    monkeypatch.setattr(round_service, "get_round1_records", mock_broken_legacy_service)

    res = client.get("/api/v1/rounds/1/records")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    records = body["data"]
    assert len(records) == 32

    for rec in records:
        assert rec["isComplete"] is False
        assert rec["rawTotalSeconds"] is None
        assert rec["adjustedTotalSeconds"] is None
        assert rec["rank"] is None
        assert rec["qualificationStatus"] == "Incomplete"
        assert len(rec["miniRounds"]) == 3
        for mr in rec["miniRounds"]:
            assert mr["isCompleted"] is False
            assert mr["durationSeconds"] is None
            assert mr["startTime"] is None
            assert mr["completionTime"] is None

