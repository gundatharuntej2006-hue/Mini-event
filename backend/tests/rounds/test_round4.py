import pytest
from app.scoring.round4_scoring import calculate_panel_score, calculate_final_score_breakdown, process_round4_standings

def test_panel_score_empty_and_average():
    # Empty scores produces None, never zero
    empty = calculate_panel_score([], "average")
    assert empty["panel_score"] is None
    assert empty["is_complete"] is False

    # Two submitted scorecards
    cards = [
        {"is_submitted": True, "total_score": 80.0},
        {"is_submitted": True, "total_score": 90.0}
    ]
    avg = calculate_panel_score(cards, "average")
    assert avg["panel_score"] == 85.0
    assert avg["is_complete"] is True

def test_final_score_strictly_pure_rubric_panel_score():
    breakdown = calculate_final_score_breakdown(
        team_id="team-1",
        panel_score=85.0,
        agent_record=None,
        black_market_balance=100.0,
        formula={"isFormulaConfirmed": False, "panelScoreWeight": 1.0, "blackMarketWeightPercent": 10},
        is_guessing_configured=False
    )
    assert breakdown["final_score"] == 85.0
    assert breakdown["is_complete"] is True
    assert breakdown["agent_guessing_points"] is None
    assert breakdown["black_market_contribution"] == 0.0

def test_round4_cutoff_tie_blocks_finalization():
    records = []
    for i in range(8):
        # Tie at 3rd cutoff (ranks 3 and 4 share 90.0 panel score)
        ps = 90.0 if (i == 2 or i == 3) else float(100 - i * 5)
        records.append({
            "team_id": f"team-{i + 1}",
            "team_number": i + 1,
            "team_name": f"Team {i + 1}",
            "panel_score": ps,
            "is_judge_panel_complete": True,
            "final_score_breakdown": {
                "final_score": ps,
                "is_complete": True
            }
        })

    # 4 confirmed pairs with completed hearings
    pairs = [
        {
            "id": f"pair-{i + 1}",
            "team_a_id": f"team-{i * 2 + 1}",
            "team_b_id": f"team-{i * 2 + 2}",
            "is_confirmed": True,
            "case_name": f"Case {i + 1}",
            "team_a_side": "Prosecution",
            "team_b_side": "Defense",
            "stages": {
                "hearing_1": {"status": "completed"},
                "file_exchange": {"status": "completed"},
                "hearing_2": {"status": "completed"}
            }
        }
        for i in range(4)
    ]

    standings = process_round4_standings(
        records=records,
        pairs=pairs,
        config={"advancing_teams_count": 3, "is_finalized": False},
        round3_finalized=True
    )
    assert standings["can_finalize"] is False
    assert standings["ties_affecting_cutoff"] is True
    assert any(i["code"] == "CUTOFF_TIE" for i in standings["issues"])
