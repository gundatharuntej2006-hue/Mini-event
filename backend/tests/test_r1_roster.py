from app.api.routes.r1_event import event_config
from app.core.security import get_password_hash
from app.models.event_account import EventAccount, EventRole
from app.models.participant import Participant, ParticipantRole
from app.models.team import Team
from app.services.round1_service import get_or_create_route_allocations


def login(client, login_id: str, password: str) -> dict:
    response = client.post("/api/v1/r1/login", json={"login_id": login_id, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['token']}"}


def test_super_admin_can_correct_an_existing_five_member_roster(client, db_session):
    team = Team(id="team-1017", team_number=17, name="Aura 999+")
    db_session.add(team)
    members = [
        Participant(id=f"part-1017-{index}", name=f"Old Member {index}", email=f"old{index}@bmsit.in", usn=f"1BY25CS{700 + index}", team_id=team.id, role=ParticipantRole.LEADER if index == 1 else ParticipantRole.MEMBER)
        for index in range(1, 6)
    ]
    super_password = "RosterTest987"
    db_session.add_all(members + [
        EventAccount(login_id="SUPER01", display_name="Super Admin 1", password_hash=get_password_hash(super_password), role=EventRole.SUPER_ADMIN),
        EventAccount(login_id="TEAM1017", display_name=team.name, password_hash=get_password_hash("ParticipantTest987"), role=EventRole.PARTICIPANT, team_id=team.id),
    ])
    db_session.commit()
    event_config(db_session)
    get_or_create_route_allocations(db_session)

    response = client.post("/api/v1/r1/control/roster/team", headers=login(client, "SUPER01", super_password), json={
        "current_super_password": super_password,
        "team_identifier": "TEAM1017",
        "team_name": "Sentinel",
        "members": [
            {"participant_id": member.id, "name": name}
            for member, name in zip(members, ["Ujjwal Kumar Gupta", "Kumar Satyam", "Arnav Atul", "Nalin Sharma", "Ishan Verma"])
        ],
        "reason": "Corrected event roster",
    })

    assert response.status_code == 200
    assert db_session.query(Team).filter(Team.id == team.id).one().name == "Sentinel"
    assert [member.name for member in db_session.query(Participant).filter(Participant.team_id == team.id).order_by(Participant.id).all()] == ["Ujjwal Kumar Gupta", "Kumar Satyam", "Arnav Atul", "Nalin Sharma", "Ishan Verma"]
    assert db_session.query(EventAccount).filter(EventAccount.login_id == "TEAM1017").one().display_name == "Sentinel"
