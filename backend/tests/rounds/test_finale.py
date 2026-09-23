import pytest
from app.scoring.finale_scoring import calculate_scorecard_total, process_finale_standings
from app.models.finale import default_finale_criteria

def test_finale_incomplete_scorecard_stays_null():
    criteria = default_finale_criteria()
    scores = {
        "climax_defense": 45.0,
        "cross_examination": None,  # Incomplete
        "synergy_decorum": 18.0
    }
    result = calculate_scorecard_total(scores, criteria)
    assert result["total_score"] is None
    assert result["is_complete"] is False

def test_finale_podium_tie_blocks_finalization():
    records = [
        {
            "team_id": "team-1",
            "team_number": 1,
            "team_name": "Team 1",
            "round4_score": 90.0,
            "scorecard": {"is_complete": True, "total_score": 90.0},
            "score_breakdown": {"total_finale_score": 110.0}
        },
        {
            "team_id": "team-2",
            "team_number": 2,
            "team_name": "Team 2",
            "round4_score": 90.0,
            "scorecard": {"is_complete": True, "total_score": 90.0},
            "score_breakdown": {"total_finale_score": 110.0}  # Tied with team 1 on 110 pts!
        },
        {
            "team_id": "team-3",
            "team_number": 3,
            "team_name": "Team 3",
            "round4_score": 85.0,
            "scorecard": {"is_complete": True, "total_score": 85.0},
            "score_breakdown": {"total_finale_score": 100.0}
        }
    ]

    standings = process_finale_standings(
        records=records,
        config={"is_scoring_rules_confirmed": True, "scoring_direction": "higher_wins"},
        round4_finalized=True
    )
    assert standings["can_finalize"] is False
    assert standings["ties_affecting_placement"] is True
    assert any(i["code"] == "PODIUM_TIE" for i in standings["issues"])

def test_finale_clean_podium_awards_titles():
    records = [
        {
            "team_id": "team-1",
            "team_number": 1,
            "team_name": "Team 1",
            "round4_score": 90.0,
            "scorecard": {"is_complete": True, "total_score": 95.0},
            "score_breakdown": {"total_finale_score": 115.0}
        },
        {
            "team_id": "team-2",
            "team_number": 2,
            "team_name": "Team 2",
            "round4_score": 90.0,
            "scorecard": {"is_complete": True, "total_score": 90.0},
            "score_breakdown": {"total_finale_score": 110.0}
        },
        {
            "team_id": "team-3",
            "team_number": 3,
            "team_name": "Team 3",
            "round4_score": 85.0,
            "scorecard": {"is_complete": True, "total_score": 85.0},
            "score_breakdown": {"total_finale_score": 105.0}
        }
    ]

    standings = process_finale_standings(
        records=records,
        config={"is_scoring_rules_confirmed": True, "scoring_direction": "higher_wins"},
        round4_finalized=True
    )
    assert standings["can_finalize"] is True
    assert standings["champion_team_id"] == "team-1"
    assert standings["runner_up1_team_id"] == "team-2"
    assert standings["runner_up2_team_id"] == "team-3"
    assert standings["records"][0]["placement_title"] == "Grand Champion"
    assert standings["records"][1]["placement_title"] == "1st Runner Up"
    assert standings["records"][2]["placement_title"] == "2nd Runner Up"
