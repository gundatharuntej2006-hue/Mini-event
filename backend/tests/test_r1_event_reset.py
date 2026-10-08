from app.core.security import get_password_hash
from app.models.core import seed_default_teams
from app.api.routes.r1_event import event_config, record_finish
from app.models.event_account import EventAccount, EventRole, Round1FinishOutcome, Round1Override, Round1SecretAgentSelection
from app.models.round1 import Round1RouteAllocationModel
from app.models.team import Team
from app.services.round1_service import get_or_create_route_allocations


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
    assert client.post("/api/v1/r1/participant/secret-agent", headers=participant_headers, json={"agent_name": "Test Agent"}).status_code == 200
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
    assert state["secret_agent_submitted"] is False
    assert db_session.query(Round1Override).filter(Round1Override.action == "RESET").count() == 1
    assert db_session.query(Round1SecretAgentSelection).count() == 0


def test_final_submission_records_rank_points_and_pdf_report(client, db_session):
    seed_default_teams(db_session)
    team = db_session.query(Team).filter(Team.team_number == 1).one()
    super_password = "SuperReportTest987"
    participant_password = "ParticipantReport987"
    db_session.add_all([
        EventAccount(login_id="SUPER01", display_name="Super Admin 1", password_hash=get_password_hash(super_password), role=EventRole.SUPER_ADMIN),
        EventAccount(login_id="TEAM1001", display_name=team.name, password_hash=get_password_hash(participant_password), role=EventRole.PARTICIPANT, team_id=team.id),
    ])
    db_session.commit()
    super_headers = login(client, "SUPER01", super_password)
    participant_headers = login(client, "TEAM1001", participant_password)

    assert client.post("/api/v1/r1/control/start", headers=super_headers).status_code == 200
    assert client.post("/api/v1/r1/participant/secret-agent", headers=participant_headers, json={"agent_name": "Agent One"}).status_code == 200
    assert client.post("/api/v1/r1/participant/scan", headers=participant_headers, json={"location": 1}).status_code == 200
    allocation = db_session.query(Round1RouteAllocationModel).filter(Round1RouteAllocationModel.team_id == team.id).one()
    allocation.cp1_completed = True
    allocation.cp2_completed = True
    db_session.commit()

    assert client.post("/api/v1/r1/participant/scan", headers=participant_headers, json={"location": allocation.cp3_location}).status_code == 200
    final = client.post("/api/v1/r1/participant/answer", headers=participant_headers, json={"answer": "ODD-42"})
    assert final.status_code == 200
    assert final.json()["data"]["state"]["complete"] is True
    outcome = db_session.query(Round1FinishOutcome).one()
    assert outcome.rank == 1
    assert outcome.is_qualified is True
    assert outcome.points_snapshot == 540
    assert db_session.query(Team).filter(Team.id == team.id).one().total_score == 540
    report = client.get("/api/v1/r1/control/report.pdf", headers=super_headers)
    assert report.status_code == 200
    assert report.headers["content-type"].startswith("application/pdf")
    assert report.content.startswith(b"%PDF")


def test_sixteenth_finisher_deactivates_remaining_participant_accounts(db_session):
    seed_default_teams(db_session)
    teams = db_session.query(Team).order_by(Team.team_number).all()
    for team in teams:
        db_session.add(EventAccount(
            login_id=f"TEAM{1000 + team.team_number}", display_name=team.name,
            password_hash=get_password_hash("TestOnly123"), role=EventRole.PARTICIPANT, team_id=team.id,
        ))
    db_session.commit()
    event_config(db_session)
    get_or_create_route_allocations(db_session)
    allocations = db_session.query(Round1RouteAllocationModel).order_by(Round1RouteAllocationModel.team_identifier).all()

    for allocation in allocations[:16]:
        allocation.cp3_completed = True
        record_finish(db_session, allocation)
    db_session.commit()

    outcomes = db_session.query(Round1FinishOutcome).order_by(Round1FinishOutcome.rank).all()
    accounts = db_session.query(EventAccount).filter(EventAccount.role == EventRole.PARTICIPANT).order_by(EventAccount.login_id).all()
    assert len(outcomes) == 16
    assert all(item.is_qualified for item in outcomes)
    assert [item.rank for item in outcomes] == list(range(1, 17))
    assert sum(account.is_active for account in accounts) == 16
    assert sum(not account.is_active for account in accounts) == 16
