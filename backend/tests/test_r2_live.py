from datetime import datetime, timezone

from app.core.security import get_password_hash
from app.models.core import seed_default_teams
from app.models.event_account import EventAccount, EventRole, Round1FinishOutcome
from app.models.participant import Participant
from app.models.team import Team


def login(client, login_id: str, password: str) -> dict:
    response = client.post("/api/v1/r1/login", json={"login_id": login_id, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['token']}"}


def seed_round2_ready_roster(db_session):
    seed_default_teams(db_session)
    teams = db_session.query(Team).order_by(Team.team_number).all()
    super_password = "SuperRound2Test987"
    db_session.add(EventAccount(login_id="SUPER01", display_name="Super Admin", password_hash=get_password_hash(super_password), role=EventRole.SUPER_ADMIN))
    for number in range(1, 9):
        db_session.add(EventAccount(login_id=f"ADMIN{number:02}", display_name=f"Admin {number}", password_hash=get_password_hash(f"AdminRound2{number:02}"), role=EventRole.ADMIN, location_number=number))
    for rank, team in enumerate(teams[:16], start=1):
        points = 140 - 5 * (rank - 1)
        team.total_score = 400 + points
        team.is_qualified_for_next_round = True
        team.current_round = 2
        db_session.add(Round1FinishOutcome(team_id=team.id, team_identifier=str(1000 + team.team_number), rank=rank, is_qualified=True, completed_at=datetime.now(timezone.utc), points_snapshot=team.total_score))
        for member in range(1, 6):
            db_session.add(Participant(id=f"part-{team.team_number}-{member}", name=f"Member {team.team_number}-{member}", email=f"member{team.team_number}-{member}@test.local", usn=f"USN{team.team_number:02}{member}", team_id=team.id))
    db_session.commit()
    return teams, super_password


def test_round2_generates_16_mixed_tables_assigns_admins_and_scores(client, db_session):
    teams, super_password = seed_round2_ready_roster(db_session)
    super_headers = login(client, "SUPER01", super_password)
    generated = client.post("/api/v1/r2/control/generate", headers=super_headers)
    assert generated.status_code == 200
    overview = client.get("/api/v1/r2/control/overview", headers=super_headers).json()["data"]
    assert overview["generated"] is True
    assert len(overview["tables"]) == 16
    assert all(len(table["players"]) == 5 for table in overview["tables"])
    assert all(len({player["team_id"] for player in table["players"]}) == 5 for table in overview["tables"])
    assert {table["admin_login_id"] for table in overview["tables"]} == {f"ADMIN{i:02}" for i in range(1, 9)}
    assert all(sum(table["admin_login_id"] == admin for table in overview["tables"]) == 2 for admin in {f"ADMIN{i:02}" for i in range(1, 9)})

    admin_headers = login(client, "ADMIN01", "AdminRound201")
    admin_tables = client.get("/api/v1/r2/admin/tables", headers=admin_headers).json()["data"]["tables"]
    assert len(admin_tables) == 2
    table = admin_tables[0]
    scores = [{"participant_id": player["participant_id"], "outcome": "WIN" if index == 0 else "LOSS"} for index, player in enumerate(table["players"])]
    assert client.post(f"/api/v1/r2/admin/tables/{table['table_number']}/scores", headers=admin_headers, json={"scores": scores}).status_code == 200
    overview = client.get("/api/v1/r2/control/overview", headers=super_headers).json()["data"]
    winning_team_id = table["players"][0]["team_id"]
    winner = next(item for item in overview["standings"] if item["team_id"] == winning_team_id)
    assert winner["cabo_points"] == 40
    assert client.post("/api/v1/r2/control/apply-rank-awards", headers=super_headers).status_code == 200
    overview = client.get("/api/v1/r2/control/overview", headers=super_headers).json()["data"]
    winner = next(item for item in overview["standings"] if item["team_id"] == winning_team_id)
    assert winner["rank"] == 1
    assert winner["rank_award"] == 80
    assert winner["total_points"] == winner["r1_points"] + 120


def test_super_admin_can_change_admin_password(client, db_session):
    seed_default_teams(db_session)
    super_password = "SuperPasswordTest987"
    db_session.add_all([
        EventAccount(login_id="SUPER01", display_name="Super", password_hash=get_password_hash(super_password), role=EventRole.SUPER_ADMIN),
        EventAccount(login_id="ADMIN01", display_name="Admin", password_hash=get_password_hash("OldPassword987"), role=EventRole.ADMIN, location_number=1),
    ])
    db_session.commit()
    super_headers = login(client, "SUPER01", super_password)
    response = client.post("/api/v1/r1/control/accounts/password", headers=super_headers, json={
        "current_super_password": super_password, "target_login_id": "ADMIN01", "new_password": "asymp001", "new_password_confirmation": "asymp001", "reason": "Event setup",
    })
    assert response.status_code == 200
    assert login(client, "ADMIN01", "asymp001")
