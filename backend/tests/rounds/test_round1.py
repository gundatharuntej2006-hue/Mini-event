import pytest
from datetime import datetime, timezone, timedelta
from app.scoring.round1_scoring import compute_mini_round, compute_team_totals, process_round1_standings

def test_mini_round_duration_and_penalty():
    start = "2026-09-19T10:00:00Z"
    end = "2026-09-19T10:15:00Z"
    mr = {
        "mini_round_number": 1,
        "start_time": start,
        "completion_time": end,
        "hints_used": 2,
        "checkpoints": []
    }
    result = compute_mini_round(mr, penalty_per_hint_seconds=120)
    assert result["duration_seconds"] == 900
    assert result["hint_penalty_seconds"] == 240
    assert result["adjusted_seconds"] == 1140
    assert result["status"] == "Completed"

def test_mini_round_incomplete_stays_null():
    mr = {
        "mini_round_number": 1,
        "start_time": "2026-09-19T10:00:00Z",
        "completion_time": None,
        "hints_used": 1,
        "checkpoints": []
    }
    result = compute_mini_round(mr, penalty_per_hint_seconds=120)
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
    totals = compute_team_totals(rec, 120)
    assert totals["is_complete"] is False
    assert totals["raw_total_seconds"] is None
    assert totals["adjusted_total_seconds"] is None

def test_round1_fastest_mini_round_tie_breaker():
    # Team 1 and Team 2 have same total adjusted time (1800s), but Team 2 has a faster single mini-round
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
    standings = process_round1_standings(records, 120, False)
    # Team 2 must be ranked #1 because fastest mini-round 480s < 600s
    assert standings["records"][0]["team_id"] == "team-2"
    assert standings["records"][0]["rank"] == 1
    assert standings["records"][1]["team_id"] == "team-1"
    assert standings["records"][1]["rank"] == 2

def test_round1_cutoff_boundary_tie_blocks_finalization():
    records = []
    base = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(32):
        team_num = i + 1
        if i < 23:
            total_sec = 1500 + i * 40
            fastest = 400 + i * 10
        elif i == 23 or i == 24:
            total_sec = 2500
            fastest = 700
        else:
            total_sec = 2600 + (i - 25) * 50
            fastest = 750 + (i - 25) * 10

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

    standings = process_round1_standings(records, 120, False)
    assert standings["can_finalize"] is False
    assert standings["cutoff_boundary_tie"] is True
    assert any(issue["code"] == "CUTOFF_TIE" for issue in standings["issues"])

def test_round1_api_endpoints(client, marshal_headers, organizer_headers):
    # Test GET /api/rounds/1
    res = client.get("/api/rounds/1")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data["records"]) == 32
    assert data["can_finalize"] is False  # All teams are initially unstarted

    # Test POST /api/rounds/1/teams/{team_id}/timings
    timing_payload = {
        "mini_round_number": 1,
        "start_time": "2026-09-19T10:00:00Z",
        "completion_time": "2026-09-19T10:12:00Z",
        "hints_used": 1,
        "checkpoints": [{"checkpoint_id": "cp1", "name": "Station 1", "arrival_time": "2026-09-19T10:05:00Z"}]
    }
    t_res = client.post("/api/rounds/1/teams/team-1/timings", json=timing_payload, headers=marshal_headers)
    assert t_res.status_code == 200
    t_data = t_res.json()["data"]
    assert t_data["duration_seconds"] == 720
    assert t_data["hint_penalty_seconds"] == 120
    assert t_data["adjusted_seconds"] == 840

    # Test Finalize fails when incomplete
    fin_res = client.post("/api/rounds/1/finalize", headers=organizer_headers)
    assert fin_res.status_code == 200
    fin_data = fin_res.json()["data"]
    assert fin_data["can_finalize"] is False
    assert any(i["code"] == "INCOMPLETE_RESULTS" for i in fin_data["issues"])
