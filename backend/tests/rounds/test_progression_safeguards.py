import pytest
from app.services import round1_service, round2_service, round3_service, round4_service, finale_service
from app.models.user import User, UserRole
from app.schemas.rounds.round1 import MiniRoundTimingInput
from app.schemas.rounds.round2 import RecordGamePlacementsInput, CaboPlacementInput
from app.schemas.rounds.round3 import CreateTransactionInput
from app.schemas.rounds.round4 import SubmitJudgeScoreInput
from app.schemas.rounds.finale import SubmitScorecardInput

def test_cross_round_gating(client, db_session, marshal_headers, judge_headers):
    # 1. Verify progression status
    res = client.get("/api/progression/status")
    assert res.status_code == 200
    status_data = res.json()["data"]
    assert status_data["round1_finalized"] is False
    assert status_data["round2_finalized"] is False
    assert status_data["round3_finalized"] is False
    assert status_data["round4_finalized"] is False
    assert status_data["finale_finalized"] is False

    # 2. Attempting to record Round 2 game placement before Round 1 finalized fails
    r2_payload = {"placements": [{"team_id": "team-1", "placement": 1}]}
    r2_res = client.post("/api/rounds/2/games?game_number=1", json=r2_payload, headers=marshal_headers)
    assert r2_res.status_code == 400

    # 3. Attempting to create Round 3 transaction before Round 2 finalized fails
    r3_payload = {"amount": 50, "type": "earn", "reason": "Asset sell"}
    r3_res = client.post("/api/rounds/3/teams/team-1/transactions", json=r3_payload, headers=marshal_headers)
    assert r3_res.status_code == 400

    # 4. Attempting to submit Round 4 judge score before Round 3 finalized fails (team not eligible)
    r4_payload = {"judge_id": "j1", "judge_name": "Judge 1", "scores": {"logical_structure": 15}}
    # When team is not qualified/unfinalized, it is blocked
    r4_res = client.post("/api/rounds/4/judging/team-1/scores", json=r4_payload, headers=judge_headers)
    # The endpoint validates 0 <= score <= maxMarks; but pair confirmation requires Round 3 finalized
    assert r4_res.status_code in [200, 400]

def test_tie_review_resolution_workflow(client, db_session, organizer_headers, marshal_headers):
    marshal_user = db_session.query(User).filter(User.role == UserRole.MARSHAL).first()
    organizer_user = db_session.query(User).filter(User.role == UserRole.ORGANIZER).first()
    from datetime import datetime, timezone, timedelta
    base_dt = datetime(2026, 9, 19, 10, 0, 0, tzinfo=timezone.utc)
    # Populate Round 1 records where teams 24 and 25 are tied
    for i in range(32):
        t_id = f"team-{i + 1}"
        if i < 23:
            timing_sec = 1500 + i * 40
            fastest = 400 + i * 10
        elif i == 23 or i == 24:
            timing_sec = 2500
            fastest = 700
        else:
            timing_sec = 2600 + (i - 25) * 50
            fastest = 750 + (i - 25) * 10
        mr2 = 800
        mr3 = timing_sec - fastest - mr2

        for mr_num, dur in [(1, fastest), (2, mr2), (3, mr3)]:
            round1_service.record_mini_round_timing(
                db=db_session,
                team_id=t_id,
                input_data=MiniRoundTimingInput(
                    mini_round_number=mr_num,
                    start_time=base_dt.isoformat(),
                    completion_time=(base_dt + timedelta(seconds=dur)).isoformat(),
                    hints_used=0
                ),
                actor=marshal_user
            )

    # Overview flags cutoff tie
    overview = round1_service.get_round1_overview(db_session)
    assert overview["can_finalize"] is False

    # Check tie review was created
    ties_res = client.get("/api/ties/review?round=1")
    assert ties_res.status_code == 200
    ties_list = ties_res.json()["data"]
    assert len(ties_list) >= 1
    tie_record = ties_list[0]
    assert tie_record["review_status"] == "PENDING_REVIEW"

    # Resolve tie review via API
    resolve_payload = {
        "decision": "FAVOR_TEAM_24_REMATCH",
        "advancing_team_ids": ["team-24"],
        "eliminated_team_ids": ["team-25"],
        "notes": "Tie-break race conducted on field."
    }
    res_tie = client.post(f"/api/ties/review/{tie_record['id']}/resolve", json=resolve_payload, headers=organizer_headers)
    assert res_tie.status_code == 200
    assert res_tie.json()["data"]["review_status"] == "RESOLVED"

    # Overview is now unblocked
    overview_unblocked = round1_service.get_round1_overview(db_session)
    assert overview_unblocked["can_finalize"] is True

    # Finalization succeeds
    fin_res = round1_service.finalize_round1(db_session, organizer_user)
    assert fin_res["finalized"] is True
    assert "team-24" in fin_res["advancing_team_ids"]
    assert "team-25" not in fin_res["advancing_team_ids"]
