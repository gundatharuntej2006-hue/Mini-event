from datetime import timedelta, timezone

from app.core.security import get_password_hash
from app.models.core import seed_default_teams
from app.models.event_account import EventAccount, EventRole
from app.models.participant import Participant
from app.models.progression import AuditLog
from app.models.round3_live import (
    Round3AuctionLot, Round3GameAttempt, Round3LiveConfig, Round3LiveTeam,
    Round3TeamSession, Round3PuzzleUse, Round3QualifiedTeam,
)
from app.models.team import Team
from app.api.routes.r3_live import normalize_final_code, utcnow
from app.api.routes.r1_event import _login_attempts
from app.services.round3_puzzles import PUZZLES, is_correct, public_payload


def login(client, login_id, password):
    response = client.post("/api/v1/r1/login", json={"login_id": login_id, "password": password})
    assert response.status_code == 200, response.json()
    return {"Authorization": f"Bearer {response.json()['data']['token']}"}


def reveal_code(client, headers, attempt_id):
    response = client.post(
        f"/api/v1/r3-live/participant/attempts/{attempt_id}/reveal-code",
        headers=headers,
        json={},
    )
    assert response.status_code == 200, response.json()
    code = response.json()["data"]["access_code"]
    assert len(code) == 3 and code.isdigit()
    return code


def test_puzzle_bank_has_275_server_validated_questions():
    assert {table: len(items) for table, items in PUZZLES.items()} == {
        1: 35, 2: 35, 3: 35, 4: 34, 5: 34, 6: 34, 7: 34, 8: 34,
    }
    puzzles = [puzzle for items in PUZZLES.values() for puzzle in items]
    assert len(puzzles) == 275
    assert len({puzzle.key for puzzle in puzzles}) == 275
    for puzzle in puzzles:
        assert puzzle.title and puzzle.story and puzzle.prompt and puzzle.display
        assert is_correct(puzzle, puzzle.answers[0])
        assert not is_correct(puzzle, "")
        public = public_payload(puzzle)
        assert "answers" not in public
        assert len(public["options"]) >= 4
        assert len({item.casefold() for item in public["options"]}) == len(public["options"])
        assert sum(is_correct(puzzle, option) for option in public["options"]) == 1
        assert public["visual_kind"] in {
            "logic", "pattern", "word", "spatial", "deduction", "observation", "sequence", "quick",
        }


def ready(client, db):
    _login_attempts.clear()
    seed_default_teams(db)
    team = db.query(Team).filter(Team.team_number == 17).one()
    other = db.query(Team).filter(Team.team_number == 2).one()
    db.add(EventAccount(login_id="SUPER01", display_name="Super", password_hash=get_password_hash("SuperTest987"), role=EventRole.SUPER_ADMIN))
    for number in range(1, 9):
        db.add(EventAccount(login_id=f"ADMIN{number:02}", display_name=f"Admin {number}", password_hash=get_password_hash("DealerTest987"), role=EventRole.ADMIN))
    for item in (team, other):
        db.add(EventAccount(login_id=f"TEAM{1000 + item.team_number}", display_name=item.name, password_hash=get_password_hash("TeamTest987"), role=EventRole.PARTICIPANT, team_id=item.id))
        db.add(Participant(id=f"part-{item.team_number}", name=f"Player {item.team_number}", email=f"player{item.team_number}@test.local", usn=f"R3TEST{item.team_number}", team_id=item.id))
    db.commit()
    super_headers = login(client, "SUPER01", "SuperTest987")
    overview = client.get("/api/v1/r3-live/control/overview", headers=super_headers)
    assert overview.status_code == 200, overview.json()
    assert len(overview.json()["data"]["teams"]) == 13
    assert [table["room"] for table in overview.json()["data"]["tables"]] == list(range(101, 109))
    return team, other, super_headers


def test_private_setup_and_auction_game_flow(client, db_session, monkeypatch):
    team, other, super_headers = ready(client, db_session)
    team_headers = login(client, "TEAM1017", "TeamTest987")
    other_headers = login(client, "TEAM1002", "TeamTest987")
    assert client.get("/api/v1/r3-live/control/overview", headers=team_headers).status_code == 403
    assert client.get("/api/v1/r3-live/control/puzzle-bank", headers=team_headers).status_code == 403
    private_bank = client.get("/api/v1/r3-live/control/puzzle-bank", headers=super_headers)
    assert private_bank.status_code == 200, private_bank.json()
    assert private_bank.json()["data"]["total"] == 275
    assert private_bank.json()["data"]["game_seconds"] == 75
    assert private_bank.json()["data"]["tables"][0]["puzzles"][0]["answers"] == ["divya"]
    private = client.get("/api/v1/r3-live/participant/state", headers=team_headers)
    assert private.status_code == 200, private.json()
    assert private.json()["data"]["team"]["opening_points"] == 1370
    assert "teams" not in private.json()["data"]
    for number in range(1, 9):
        response = client.post(f"/api/v1/r3-live/control/tables/{number}", headers=super_headers, json={"game_name": f"Game {number}", "max_points": 20, "is_enabled": True})
        assert response.status_code == 200, response.json()
    started = client.post("/api/v1/r3-live/control/start", headers=super_headers)
    assert started.status_code == 200, started.json()
    assert db_session.get(Team, team.id).total_score == 1370
    public_roster = client.get("/api/v1/teams").json()["data"]
    assert all(item["totalScore"] is None for item in public_roster)
    team_headers = login(client, "TEAM1017", "TeamTest987")
    other_headers = login(client, "TEAM1002", "TeamTest987")
    assert client.get("/api/v1/r3-live/participant/state", headers=team_headers).status_code == 200
    assert client.get("/api/v1/r3-live/participant/state", headers=other_headers).status_code == 200

    spun = client.post("/api/v1/r3-live/participant/assign", headers=team_headers, json={"participant_id": "part-17"})
    assert spun.status_code == 200, spun.json()
    attempt_id = spun.json()["data"]["id"]
    assert spun.json()["data"]["status"] == "RESERVED"
    assert spun.json()["data"]["table_number"] == 1
    assert "access_code" not in spun.json()["data"]
    busy = client.post("/api/v1/r3-live/participant/assign", headers=other_headers, json={"participant_id": "part-2"})
    assert busy.status_code == 200, busy.json()
    assert busy.json()["data"]["table_number"] == 2
    dealer_headers = login(client, "ADMIN01", "DealerTest987")
    assert client.post(f"/api/v1/r3-live/admin/attempts/{attempt_id}/start", headers=other_headers).status_code == 403
    assert client.post(f"/api/v1/r3-live/admin/attempts/{attempt_id}/unlock", headers=dealer_headers, json={"access_code": "999"}).status_code == 409
    access_code = reveal_code(client, team_headers, attempt_id)
    assert client.post(f"/api/v1/r3-live/admin/attempts/{attempt_id}/unlock", headers=dealer_headers, json={"access_code": "999"}).status_code == 403
    unlocked = client.post(f"/api/v1/r3-live/admin/attempts/{attempt_id}/unlock", headers=dealer_headers, json={"access_code": access_code})
    assert unlocked.status_code == 200, unlocked.json()
    assert unlocked.json()["data"]["puzzle"]["key"] == "1A"
    scored = client.post(f"/api/v1/r3-live/admin/attempts/{attempt_id}/answer", headers=dealer_headers, json={"answer": "DIVYA"})
    assert scored.status_code == 200, scored.json()
    assert scored.json()["data"]["correct"] is True
    assert db_session.get(Team, team.id).total_score == 1390
    assert db_session.query(Round3PuzzleUse).count() == 2
    next_state = client.get("/api/v1/r3-live/participant/state", headers=other_headers).json()["data"]
    assert next_state["team"]["attempt"]["status"] == "RESERVED"
    assert next_state["team"]["balance"] == 1315

    lot = db_session.query(Round3AuctionLot).filter(Round3AuctionLot.level == 1, Round3AuctionLot.token_number == 1).one()
    assert client.post(f"/api/v1/r3-live/control/lots/{lot.id}/configure", headers=super_headers, json={"opening_bid": 20, "description": "A sealed case clue for the legal round", "clue_text": "The security clock was six minutes slow."}).status_code == 200
    assert client.post(f"/api/v1/r3-live/control/lots/{lot.id}/open", headers=super_headers).status_code == 200
    before_lot = client.get("/api/v1/r3-live/participant/state", headers=other_headers).json()["data"]["lots"][0]
    assert before_lot["clue_text"] is None
    assert client.post(f"/api/v1/r3-live/participant/lots/{lot.id}/bid", headers=team_headers, json={"amount": 25}).status_code == 200
    assert client.post(f"/api/v1/r3-live/participant/lots/{lot.id}/bid", headers=other_headers, json={"amount": 24}).status_code == 409
    assert client.post(f"/api/v1/r3-live/control/lots/{lot.id}/close", headers=super_headers).status_code == 200
    after = client.get("/api/v1/r3-live/participant/state", headers=team_headers).json()["data"]
    assert after["team"]["balance"] == 1365
    assert after["lots"][0]["clue_text"] == "The security clock was six minutes slow."
    loser_lot = client.get("/api/v1/r3-live/participant/state", headers=other_headers).json()["data"]["lots"][0]
    assert loser_lot["clue_text"] is None
    assert db_session.get(Team, team.id).total_score == 1365
    assert "winner_team_id" not in after["team"]


def test_super_admin_reset_requires_double_password_and_preserves_setup(client, db_session):
    team, _, super_headers = ready(client, db_session)
    protected = {
        "password": "SuperTest987",
        "password_confirmation": "DifferentPassword987",
        "confirmed": True,
        "reason": "Testing complete",
    }
    mismatch = client.post("/api/v1/r3-live/control/reset", headers=super_headers, json=protected)
    assert mismatch.status_code == 400
    protected["password_confirmation"] = protected["password"] = "WrongPassword987"
    wrong = client.post("/api/v1/r3-live/control/reset", headers=super_headers, json=protected)
    assert wrong.status_code == 401
    protected["password_confirmation"] = protected["password"] = "SuperTest987"
    protected["confirmed"] = False
    unconfirmed = client.post("/api/v1/r3-live/control/reset", headers=super_headers, json=protected)
    assert unconfirmed.status_code == 400

    for number in range(1, 9):
        response = client.post(
            f"/api/v1/r3-live/control/tables/{number}",
            headers=super_headers,
            json={
                "game_name": f"Reset-proof game {number}",
                "max_points": 20,
                "is_enabled": True,
                "room_number": 150 if number == 1 else 100 + number,
            },
        )
        assert response.status_code == 200, response.json()
    assert client.post("/api/v1/r3-live/control/start", headers=super_headers).status_code == 200
    team_headers = login(client, "TEAM1017", "TeamTest987")
    attempt = client.post(
        "/api/v1/r3-live/participant/assign",
        headers=team_headers,
        json={"participant_id": "part-17"},
    )
    assert attempt.status_code == 200, attempt.json()
    assert db_session.query(Round3GameAttempt).count() == 1
    assert db_session.query(Round3PuzzleUse).count() == 1

    lot = db_session.query(Round3AuctionLot).filter(
        Round3AuctionLot.level == 1, Round3AuctionLot.token_number == 1
    ).one()
    configured = client.post(
        f"/api/v1/r3-live/control/lots/{lot.id}/configure",
        headers=super_headers,
        json={
            "opening_bid": 5,
            "description": "Preserved public clue teaser",
            "clue_text": "Preserved private clue text",
        },
    )
    assert configured.status_code == 200, configured.json()
    assert client.post(f"/api/v1/r3-live/control/lots/{lot.id}/open", headers=super_headers).status_code == 200
    assert client.post(
        f"/api/v1/r3-live/participant/lots/{lot.id}/bid",
        headers=team_headers,
        json={"amount": 10},
    ).status_code == 200

    protected["confirmed"] = True
    reset = client.post("/api/v1/r3-live/control/reset", headers=super_headers, json=protected)
    assert reset.status_code == 200, reset.json()
    assert reset.json()["data"]["cleared"]["attempts"] == 1
    assert db_session.query(Round3GameAttempt).count() == 0
    assert db_session.query(Round3PuzzleUse).count() == 0
    assert db_session.query(Round3TeamSession).count() == 0
    assert db_session.get(Team, team.id).total_score == 1370
    audit = db_session.query(AuditLog).filter(AuditLog.action == "ROUND3_RESET_TO_SETUP").one()
    assert audit.details["reason"] == "Testing complete"

    overview = client.get("/api/v1/r3-live/control/overview", headers=super_headers).json()["data"]
    assert overview["started"] is False
    assert overview["questions"]["used"] == 0
    assert overview["tables"][0]["room"] == 150
    assert overview["tables"][0]["game_name"] == "Reset-proof game 1"
    assert overview["lots"][0]["status"] == "DRAFT"
    assert overview["lots"][0]["description"] == "Preserved public clue teaser"
    assert overview["lots"][0]["clue_text"] == "Preserved private clue text"


def test_three_active_team_logins_and_code_normalization(client, db_session):
    ready(client, db_session)
    super_headers = login(client, "SUPER01", "SuperTest987")
    for number in range(1, 9):
        client.post(f"/api/v1/r3-live/control/tables/{number}", headers=super_headers, json={"game_name": f"Game {number}", "max_points": 20, "is_enabled": True})
    client.post("/api/v1/r3-live/control/start", headers=super_headers)
    sessions = [login(client, "TEAM1017", "TeamTest987") for _ in range(3)]
    fourth = client.post("/api/v1/r1/login", json={"login_id": "TEAM1017", "password": "TeamTest987"})
    assert fourth.status_code == 409
    assert client.post("/api/v1/r3-live/participant/signout", headers=sessions[0]).status_code == 200
    assert client.post("/api/v1/r1/login", json={"login_id": "TEAM1017", "password": "TeamTest987"}).status_code == 200
    assert normalize_final_code("ODD ECHO")
    assert normalize_final_code("odd echo")
    assert normalize_final_code("OdDeChO")
    assert not normalize_final_code("ODD-ECHO")


def test_custom_dealer_assignment_and_admin_creation(client, db_session):
    ready(client, db_session)
    super_headers = login(client, "SUPER01", "SuperTest987")
    created = client.post("/api/v1/r3-live/control/admins", headers=super_headers, json={
        "login_id": "ADMIN09", "display_name": "Reserve Dealer", "password": "ReservePass987",
    })
    assert created.status_code == 200, created.json()
    updated = client.post("/api/v1/r3-live/control/tables/1", headers=super_headers, json={
        "table_number": 21, "room_number": 3, "game_mode": "OFFLINE",
        "admin_login_id": "ADMIN09", "game_name": "Physical puzzle desk",
        "max_points": 35, "is_enabled": True,
    })
    assert updated.status_code == 409
    for number in range(1, 9):
        response = client.post(f"/api/v1/r3-live/control/tables/{number}", headers=super_headers,
                               json={"game_name": f"Game {number}", "max_points": 20, "is_enabled": True})
        assert response.status_code == 200, response.json()
    assert client.post("/api/v1/r3-live/control/start", headers=super_headers).status_code == 200
    reserve = client.post("/api/v1/r3-live/control/admins", headers=super_headers, json={
        "login_id": "ADMIN10", "display_name": "Live Reserve", "password": "ReservePass987",
    })
    assert reserve.status_code == 200, reserve.json()
    handoff = client.post("/api/v1/r3-live/control/tables/1/dealer", headers=super_headers,
                          json={"admin_login_id": "ADMIN10", "room_number": 4})
    assert handoff.status_code == 200, handoff.json()
    new_headers = login(client, "ADMIN10", "ReservePass987")
    assert client.get("/api/v1/r3-live/admin/table", headers=new_headers).json()["data"]["room"] == 4
    old_headers = login(client, "ADMIN01", "DealerTest987")
    assert client.get("/api/v1/r3-live/admin/table", headers=old_headers).json()["data"]["assigned"] is False


def test_game_started_at_market_deadline_keeps_full_seventy_five_seconds(client, db_session, monkeypatch):
    team, other, super_headers = ready(client, db_session)
    for number in range(1, 9):
        response = client.post(f"/api/v1/r3-live/control/tables/{number}", headers=super_headers,
                               json={"game_name": f"Game {number}", "max_points": 20, "is_enabled": True})
        assert response.status_code == 200, response.json()
    assert client.post("/api/v1/r3-live/control/start", headers=super_headers).status_code == 200
    deadline = db_session.get(Round3LiveConfig, 1).ends_at.replace(tzinfo=timezone.utc)
    monkeypatch.setattr("app.api.routes.r3_live.utcnow", lambda: deadline)
    team_headers = login(client, "TEAM1017", "TeamTest987")
    other_headers = login(client, "TEAM1002", "TeamTest987")
    dealer_headers = login(client, "ADMIN01", "DealerTest987")
    db_session.query(Round3TeamSession).update({Round3TeamSession.last_seen_at: deadline})
    db_session.commit()
    spun = client.post("/api/v1/r3-live/participant/assign", headers=team_headers, json={"participant_id": "part-17"})
    assert spun.status_code == 200, spun.json()
    attempt_id = spun.json()["data"]["id"]
    access_code = reveal_code(client, team_headers, attempt_id)
    waiting = client.post("/api/v1/r3-live/participant/assign", headers=other_headers, json={"participant_id": "part-2"})
    assert waiting.status_code == 200, waiting.json()
    assert client.post(f"/api/v1/r3-live/admin/attempts/{attempt_id}/unlock", headers=dealer_headers, json={"access_code": access_code}).status_code == 200
    monkeypatch.setattr("app.api.routes.r3_live.utcnow", lambda: deadline + timedelta(seconds=70))
    state = client.get("/api/v1/r3-live/participant/state", headers=team_headers)
    assert state.status_code == 200, state.json()
    assert state.json()["data"]["team"]["attempt"]["status"] == "ACTIVE"
    scored = client.post(f"/api/v1/r3-live/admin/attempts/{attempt_id}/answer",
                         headers=dealer_headers, json={"answer": "Divya"})
    assert scored.status_code == 200, scored.json()
    assert db_session.get(Team, team.id).total_score == 1390
    client.get("/api/v1/r3-live/participant/state", headers=other_headers)
    queued = db_session.query(Round3GameAttempt).filter(Round3GameAttempt.team_id == other.id).one()
    assert queued.status == "EXPIRED"


def test_station_answer_is_locked_after_seventy_five_seconds(client, db_session, monkeypatch):
    team, _, super_headers = ready(client, db_session)
    for number in range(1, 9):
        client.post(f"/api/v1/r3-live/control/tables/{number}", headers=super_headers,
                    json={"game_name": f"Puzzle {number}", "max_points": 20, "is_enabled": True})
    client.post("/api/v1/r3-live/control/start", headers=super_headers)
    team_headers = login(client, "TEAM1017", "TeamTest987")
    admin_headers = login(client, "ADMIN01", "DealerTest987")
    assigned = client.post("/api/v1/r3-live/participant/assign", headers=team_headers,
                           json={"participant_id": "part-17"}).json()["data"]
    assigned["access_code"] = reveal_code(client, team_headers, assigned["id"])
    unlocked = client.post(f"/api/v1/r3-live/admin/attempts/{assigned['id']}/unlock", headers=admin_headers,
                           json={"access_code": assigned["access_code"]})
    assert unlocked.status_code == 200, unlocked.json()
    attempt = db_session.get(Round3GameAttempt, assigned["id"])
    started = attempt.started_at.replace(tzinfo=timezone.utc)
    monkeypatch.setattr("app.api.routes.r3_live.utcnow", lambda: started + timedelta(seconds=76))
    expired = client.post(f"/api/v1/r3-live/admin/attempts/{assigned['id']}/answer", headers=admin_headers,
                          json={"answer": "Divya"})
    assert expired.status_code == 409, expired.json()
    db_session.refresh(attempt)
    assert attempt.status == "COMPLETE"
    assert attempt.points == 0
    assert db_session.get(Team, team.id).total_score == 1370


def test_automatic_station_cooldowns_and_wrong_answer_zero(client, db_session):
    team, _, super_headers = ready(client, db_session)
    for number in range(1, 9):
        response = client.post(f"/api/v1/r3-live/control/tables/{number}", headers=super_headers,
                               json={"game_name": f"Puzzle {number}", "max_points": 10 + number, "is_enabled": True})
        assert response.status_code == 200, response.json()
    assert client.post("/api/v1/r3-live/control/start", headers=super_headers).status_code == 200
    team_headers = login(client, "TEAM1017", "TeamTest987")

    first = client.post("/api/v1/r3-live/participant/assign", headers=team_headers, json={"participant_id": "part-17"}).json()["data"]
    assert first["table_number"] == 1
    first["access_code"] = reveal_code(client, team_headers, first["id"])
    admin1 = login(client, "ADMIN01", "DealerTest987")
    client.post(f"/api/v1/r3-live/admin/attempts/{first['id']}/unlock", headers=admin1, json={"access_code": first["access_code"]})
    result = client.post(f"/api/v1/r3-live/admin/attempts/{first['id']}/answer", headers=admin1, json={"answer": "definitely wrong"})
    assert result.status_code == 200
    assert result.json()["data"]["correct"] is False
    assert result.json()["data"]["awarded"] == 0.0

    second = client.post("/api/v1/r3-live/participant/assign", headers=team_headers, json={"participant_id": "part-17"}).json()["data"]
    assert second["table_number"] != 1  # team and player cooldown both block the immediate repeat
    second["access_code"] = reveal_code(client, team_headers, second["id"])
    admin2 = login(client, "ADMIN02", "DealerTest987")
    client.post(f"/api/v1/r3-live/admin/attempts/{second['id']}/unlock", headers=admin2, json={"access_code": second["access_code"]})
    client.post(f"/api/v1/r3-live/admin/attempts/{second['id']}/answer", headers=admin2, json={"answer": "mirror"})

    third = client.post("/api/v1/r3-live/participant/assign", headers=team_headers, json={"participant_id": "part-17"}).json()["data"]
    assert third["table_number"] not in {first["table_number"], second["table_number"]}
    state = client.get("/api/v1/r3-live/participant/state", headers=team_headers).json()["data"]
    assert state["team"]["games_completed"] == 2
    assert state["team"]["members"][0]["games_completed"] == 2
    assert db_session.get(Team, team.id).total_score == 1382  # 1370 + table 2's 12 points


def test_super_admin_chooses_and_locks_round4_field(client, db_session):
    _team, _other, super_headers = ready(client, db_session)
    changed = client.post(
        "/api/v1/r3-live/control/qualification-count",
        headers=super_headers,
        json={"qualifying_count": 5},
    )
    assert changed.status_code == 200, changed.json()
    for number in range(1, 9):
        response = client.post(
            f"/api/v1/r3-live/control/tables/{number}",
            headers=super_headers,
            json={"game_name": f"Puzzle {number}", "max_points": 20, "is_enabled": True},
        )
        assert response.status_code == 200, response.json()
    assert client.post("/api/v1/r3-live/control/start", headers=super_headers).status_code == 200
    assert client.post("/api/v1/r3-live/control/close", headers=super_headers).status_code == 200
    locked = client.post("/api/v1/r3-live/control/qualifications/finalize", headers=super_headers)
    assert locked.status_code == 200, locked.json()
    assert db_session.query(Round3QualifiedTeam).count() == 5
    overview = client.get("/api/v1/r3-live/control/overview", headers=super_headers).json()["data"]
    assert overview["qualification"]["count"] == 5
    assert overview["qualification"]["finalized"] is True
    assert len(overview["qualification"]["qualified_team_ids"]) == 5
