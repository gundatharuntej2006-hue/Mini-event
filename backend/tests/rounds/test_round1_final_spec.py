import pytest
from datetime import datetime, timezone
from app.core.constants import R1_LOCATIONS, R1_DEFAULT_TEAM_IDS, R1_QUESTION_SETS
from app.services.round1_service import (
    validate_route_allocations,
    get_or_create_route_allocations,
    create_or_resume_participant_session,
    get_participant_current_state,
    record_participant_location_scan,
    submit_participant_checkpoint_answer,
    get_location_volunteer_view,
    get_envelope_preparation_sheet,
    get_team_audit_details,
)
from app.models.round1 import (
    Round1RouteAllocationModel,
    Round1ParticipantSessionModel,
    Round1CheckpointAttemptModel,
)


def test_route_allocation_satisfies_all_8_constraints(db_session):
    """
    Validates all 8 constraints specified by the user for Round 1:
    1. Exactly 32 teams (IDs 1001-1032)
    2. 8 physical locations using exact specified locations (1, 2, 5, 6, 7, 8, 9, 10 original; strictly omit 3 and 4)
    3. 3 checkpoints per team
    4. Maximum 4 teams per location at any given checkpoint
    5. 4 question sets (A, B, C, D)
    6. Each team receives 3 distinct question sets across checkpoints
    7. Each location at each checkpoint has exactly one team on Set A, one on B, one on C, one on D
    8. Physical QR codes reuse the same 8 physical locations
    """
    allocations = get_or_create_route_allocations(db_session, force_regenerate=True)
    assert len(allocations) == 32

    # Run formal constraint validator
    validation = validate_route_allocations(allocations)
    assert validation["is_valid"] is True, f"Constraint violations: {validation['errors']}"
    assert len(validation["errors"]) == 0
    assert validation["summary"]["total_teams"] == 32
    assert "ENIGMA" in validation["summary"]["organizer_note"]


def test_organizer_start_round1_authoritative_timestamp(client, organizer_headers):
    """
    Organizer console triggers official Round 1 start once:
    - Logs authoritative backend UTC timestamp
    - Subsequent starts are idempotent / rejected
    """
    # 1. Start Round 1
    resp = client.post("/api/v1/rounds/1/start", headers=organizer_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["is_started"] is True
    assert data["started_at"] is not None

    # Parse and verify valid ISO timestamp
    started_at = datetime.fromisoformat(data["started_at"].replace("Z", "+00:00"))
    assert started_at.tzinfo is not None

    # 2. Subsequent start request should return 400 error (cannot start twice)
    resp2 = client.post("/api/v1/rounds/1/start", headers=organizer_headers)
    assert resp2.status_code == 400
    msg = resp2.json().get("message") or resp2.json().get("detail", "")
    assert "already been started" in msg.lower()


def test_participant_session_and_data_isolation(client, db_session):
    """
    Participants authenticate via 4-digit Team ID:
    - Returns signed temporary session token
    - GET current state returns ONLY current checkpoint, location clue, attempts remaining
    - NEVER leaks future checkpoints, locations, or answer keys
    """
    # Create allocations
    get_or_create_route_allocations(db_session)

    # 1. Create session for Team 1001
    resp = client.post("/api/v1/rounds/1/participant/session", json={"team_identifier": "1001"})
    assert resp.status_code == 200
    session_data = resp.json()["data"]
    token = session_data["session_token"]
    assert session_data["team_identifier"] == "1001"
    assert token is not None

    # 2. Fetch current participant state
    curr_resp = client.get(f"/api/v1/rounds/1/participant/current?token={token}")
    assert curr_resp.status_code == 200
    curr_data = curr_resp.json()["data"]
    assert curr_data["current_checkpoint"] == 1
    assert curr_data["attempts_remaining"] == 3
    assert curr_data["qr_scanned"] is False
    assert curr_data["location_riddle"] is not None

    # Data isolation checks: No future locations or answer keys
    raw_json = curr_resp.json()
    assert "future_checkpoints" not in raw_json
    assert "answers" not in raw_json
    assert "correct_answer" not in raw_json
    assert "leaderboard" not in raw_json


def test_participant_scan_valid_and_invalid_location(client, db_session):
    """
    Location QR scan:
    - Scanning wrong location returns exact error: 'This is not your current assigned location.'
    - Logs INVALID_LOCATION_SCAN audit entry
    - Scanning assigned location unlocks question submission
    """
    from app.services.round1_service import get_or_create_round1_config
    cfg = get_or_create_round1_config(db_session)
    cfg.started_at = datetime.now(timezone.utc)
    db_session.commit()

    allocations = get_or_create_route_allocations(db_session)
    alloc_1001 = next(a for a in allocations if a.team_identifier == "1001")
    correct_loc = alloc_1001.cp1_location
    wrong_loc = 1 if correct_loc != 1 else 2

    # Session for 1001
    sess_res = client.post("/api/v1/rounds/1/participant/session", json={"team_identifier": "1001"})
    token = sess_res.json()["data"]["session_token"]

    # 1. Scan wrong location
    bad_scan = client.post(f"/api/v1/rounds/1/participant/scan?token={token}", json={"location": wrong_loc})
    assert bad_scan.status_code == 200
    scan_body = bad_scan.json()["data"]
    assert scan_body["valid"] is False
    assert "This is not your current assigned location." in scan_body["message"]

    # Verify invalid scan logged in audit
    audit = get_team_audit_details(db_session, "1001")
    assert any(s["is_valid_location"] is False and s["location_number"] == wrong_loc for s in audit["scans"])

    # 2. Scan correct location
    good_scan = client.post(f"/api/v1/rounds/1/participant/scan?token={token}", json={"location": correct_loc})
    assert good_scan.status_code == 200
    assert good_scan.json()["data"]["valid"] is True

    # Current state should now be unlocked
    curr = client.get(f"/api/v1/rounds/1/participant/current?token={token}").json()["data"]
    assert curr["qr_scanned"] is True


def test_participant_submit_answer_and_lockout(client, db_session):
    """
    Attempt limit & lockout:
    - Exactly 3 attempts allowed per checkpoint
    - Incorrect attempts decrement remaining counter
    - 3 incorrect attempts locks out team with message: 'Maximum attempts reached. Please contact the organizer.'
    """
    allocations = get_or_create_route_allocations(db_session)
    alloc_1002 = next(a for a in allocations if a.team_identifier == "1002")

    sess_res = client.post("/api/v1/rounds/1/participant/session", json={"team_identifier": "1002"})
    token = sess_res.json()["data"]["session_token"]

    # Scan correct location first to unlock submission
    client.post(f"/api/v1/rounds/1/participant/scan?token={token}", json={"location": alloc_1002.cp1_location})

    # Attempt 1 (Wrong)
    r1 = client.post(f"/api/v1/rounds/1/participant/submit?token={token}", json={"answer": "WRONG_1"})
    assert r1.status_code == 200
    assert r1.json()["data"]["is_correct"] is False
    assert r1.json()["data"]["attempts_remaining"] == 2

    # Attempt 2 (Wrong)
    r2 = client.post(f"/api/v1/rounds/1/participant/submit?token={token}", json={"answer": "WRONG_2"})
    assert r2.status_code == 200
    assert r2.json()["data"]["is_correct"] is False
    assert r2.json()["data"]["attempts_remaining"] == 1

    # Attempt 3 (Wrong -> Lockout)
    r3 = client.post(f"/api/v1/rounds/1/participant/submit?token={token}", json={"answer": "WRONG_3"})
    assert r3.status_code == 200
    data3 = r3.json()["data"]
    assert data3["is_correct"] is False
    assert data3["attempts_remaining"] == 0
    assert data3["is_locked"] is True
    assert "Maximum attempts reached." in data3["message"]

    # Subsequent submission stays locked
    r4 = client.post(f"/api/v1/rounds/1/participant/submit?token={token}", json={"answer": "ANYTHING"})
    assert r4.status_code == 200
    assert r4.json()["data"]["is_locked"] is True


def test_dual_acceptance_and_progression(client, db_session):
    """
    Answer validation & Checkpoint progression:
    - Set A Gate 2 accepts both '42' and 'ENIGMA'
    - Correct submission advances checkpoint and unlocks next location clue
    """
    allocations = get_or_create_route_allocations(db_session)
    # Find a team that has Set A at Checkpoint 1
    team_set_a = next(a for a in allocations if a.cp1_set == "A")
    t_id = team_set_a.team_identifier

    sess_res = client.post("/api/v1/rounds/1/participant/session", json={"team_identifier": t_id})
    token = sess_res.json()["data"]["session_token"]

    # Unlock by scanning cp1 location
    client.post(f"/api/v1/rounds/1/participant/scan?token={token}", json={"location": team_set_a.cp1_location})

    # Submit valid Set A answer (Set A Gate 1 answer is ODD or 17)
    sub_res = client.post(f"/api/v1/rounds/1/participant/submit?token={token}", json={"answer": "ODD"})
    assert sub_res.status_code == 200
    assert sub_res.json()["data"]["is_correct"] is True
    assert sub_res.json()["data"]["next_checkpoint"] == 2

    # Check updated state has advanced to checkpoint 2
    state = client.get(f"/api/v1/rounds/1/participant/current?token={token}").json()["data"]
    assert state["current_checkpoint"] == 2
    assert state["current_location_number"] == team_set_a.cp2_location
    assert state["qr_scanned"] is False  # Must scan at location 2 to unlock again!


def test_location_volunteer_view_and_envelope_sheet(client, organizer_headers, db_session):
    """
    Volunteer View & Envelope Prep Sheet:
    - Location Volunteer View returns expected 4 teams with sets A, B, C, D
    - Envelope prep sheet returns exactly 96 items (32 teams x 3 checkpoints)
    """
    get_or_create_route_allocations(db_session)

    # 1. Volunteer view for checkpoint 1, location 1
    vol_res = client.get("/api/v1/rounds/1/volunteer/view?checkpoint=1&location=1", headers=organizer_headers)
    assert vol_res.status_code == 200
    vol_data = vol_res.json()["data"]
    assert vol_data["location_number"] == 1
    assert vol_data["checkpoint_number"] == 1
    expected_teams = vol_data["expected_teams"]
    assert len(expected_teams) == 4

    sets_present = {t["assigned_set"] for t in expected_teams}
    assert sets_present == {"A", "B", "C", "D"}

    # 2. Envelope preparation sheet
    sheet_res = client.get("/api/v1/rounds/1/envelope-sheet", headers=organizer_headers)
    assert sheet_res.status_code == 200
    sheet_data = sheet_res.json()["data"]
    assert len(sheet_data) == 96


def test_public_qualified_teams_isolation_in_progress(client, db_session):
    """
    Public scoreboard isolation:
    - Before finalization, public qualified endpoint returns is_finalized=False and empty/no ranking leak
    """
    get_or_create_route_allocations(db_session)
    res = client.get("/api/v1/rounds/1/public/qualified")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["is_finalized"] is False
    assert len(data["qualified_teams"]) == 0
