from app.core.security import get_password_hash
from app.models.core import seed_default_teams
from app.models.event_account import EventAccount, EventRole, Round1Override
from app.models.team import Team


def login(client, login_id: str, password: str) -> dict:
    response = client.post("/api/v1/r1/login", json={"login_id": login_id, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['token']}"}


def test_super_admin_reset_requires_confirmation_and_clears_progress(client, db_session):
    seed_default_teams(db_session)
    team = db_session.query(Team).filter(Team.team_number == 1).one()
    super_password = "SuperResetTest987"
    participant_password = "ParticipantTest987"
    db_session.add_all([
        EventAccount(login_id="SUPER01", display_name="Super Admin 1", password_hash=get_password_hash(super_password), role=EventRole.SUPER_ADMIN),
        EventAccount(login_id="TEAM1001", display_name=team.name, password_hash=get_password_hash(participant_password), role=EventRole.PARTICIPANT, team_id=team.id),
    ])
    db_session.commit()

    super_headers = login(client, "SUPER01", super_password)
    participant_headers = login(client, "TEAM1001", participant_password)

    assert client.post("/api/v1/r1/control/start", headers=super_headers).status_code == 200
    assert client.post("/api/v1/r1/participant/scan", headers=participant_headers, json={"location": 1}).status_code == 200
    assert client.post("/api/v1/r1/participant/answer", headers=participant_headers, json={"answer": "ODD"}).status_code == 200

    mismatch = client.post("/api/v1/r1/control/reset", headers=super_headers, json={
        "password": super_password, "password_confirmation": "different", "confirmed": True, "reason": "Test reset",
    })
    assert mismatch.status_code == 400

    reset = client.post("/api/v1/r1/control/reset", headers=super_headers, json={
        "password": super_password, "password_confirmation": super_password, "confirmed": True, "reason": "Testing complete",
    })
    assert reset.status_code == 200

    state = client.get("/api/v1/r1/participant/state", headers=participant_headers).json()["data"]
    assert state["round_started"] is False
    assert state["checkpoint"] == 1
    assert state["attempts_used"] == 0
    assert db_session.query(Round1Override).filter(Round1Override.action == "RESET").count() == 1
