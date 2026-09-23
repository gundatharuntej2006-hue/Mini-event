import pytest
from app.scoring.round2_scoring import compute_team_round2_points, process_round2_standings
from app.models.round2 import default_cabo_point_table

def test_cabo_incomplete_games_stay_null():
    point_table = default_cabo_point_table()
    rec = compute_team_round2_points(
        team_id="team-1",
        team_number=1,
        team_name="Team 1",
        round1_qualified=True,
        games_placements=[1, 2, None],  # Game 3 missing
        point_table=point_table
    )
    assert rec["is_complete"] is False
    assert rec["total_points"] is None
    assert rec["games_completed_count"] == 2
    assert rec["game1_points"] == 24.0
    assert rec["game2_points"] == 23.0
    assert rec["game3_points"] is None

def test_cabo_complete_points_calculation():
    point_table = default_cabo_point_table()
    rec = compute_team_round2_points(
        team_id="team-1",
        team_number=1,
        team_name="Team 1",
        round1_qualified=True,
        games_placements=[1, 2, 3],
        point_table=point_table
    )
    assert rec["is_complete"] is True
    assert rec["total_points"] == (24 + 23 + 22)
    assert rec["games_completed_count"] == 3

def test_cabo_cutoff_tie_blocks_finalization():
    records = []
    for i in range(24):
        pts = 60 - i * 2
        # Introduce a tie straddling 12th cutoff (rank 12 and 13 share 38 pts)
        if i == 11 or i == 12:
            pts = 38
        records.append({
            "team_id": f"team-{i + 1}",
            "team_number": i + 1,
            "team_name": f"Team {i + 1}",
            "total_points": pts,
            "is_complete": True
        })

    standings = process_round2_standings(
        records=records,
        config={"scoring_direction": "higher_is_better", "point_table": default_cabo_point_table(), "is_finalized": False},
        round1_finalized=True
    )
    assert standings["can_finalize"] is False
    assert standings["ties_affecting_cutoff"] is True
    assert any(i["code"] == "CUTOFF_TIE" for i in standings["issues"])

def test_cabo_api_blocks_unfinalized_round1(client, marshal_headers):
    # Attempting to submit game placements before Round 1 is finalized
    payload = {
        "placements": [{"team_id": "team-1", "placement": 1}]
    }
    res = client.post("/api/rounds/2/games?game_number=1", json=payload, headers=marshal_headers)
    assert res.status_code == 400
    assert "Round 1 is not yet finalized" in (res.json().get("detail") or res.json().get("message", ""))
