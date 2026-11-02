from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.axiom import (
    AxiomLoginGuard,
    AxiomOriginalityAgreement,
    AxiomProblemStatement,
    AxiomProfile,
    AxiomProjectPreference,
    AxiomRoleChoice,
    AxiomRosterType,
    AxiomStatementStatus,
)
from app.models.event_account import EventAccount, EventPasswordVerifier, EventRole
from app.models.user import User
from app.services.axiom_bootstrap_service import load_axiom_roster, provision_axiom_accounts


def test_axiom_roster_contains_only_approved_club_members():
    roster = load_axiom_roster()
    names = {item["name"] for item in roster["people"]}
    emails = {item["email"] for item in roster["people"]}

    assert len(roster["people"]) == 24
    assert len(names) == 24
    assert len(emails) == 24
    assert "Archisha Gupta" not in names
    assert sum(item["roster_type"] == "MENTOR_CANDIDATE" for item in roster["people"]) == 7
    assert sum(item["roster_type"] == "MEMBER" for item in roster["people"]) == 17


def test_provisioning_pauses_legacy_accounts_and_keeps_super01(db_session):
    db_session.add_all([
        EventAccount(
            login_id="SUPER01",
            display_name="Old super",
            password_hash="old",
            role=EventRole.SUPER_ADMIN,
            is_active=True,
        ),
        EventAccount(
            login_id="SUPER02",
            display_name="Retired super",
            password_hash="old",
            role=EventRole.SUPER_ADMIN,
            is_active=True,
        ),
        EventAccount(
            login_id="ADMIN01",
            display_name="Retired admin",
            password_hash="old",
            role=EventRole.ADMIN,
            is_active=True,
        ),
    ])
    db_session.commit()

    result = provision_axiom_accounts(db_session)

    assert result["applied"] is True
    assert db_session.query(EventAccount).filter(EventAccount.is_active.is_(True)).count() == 25
    super01 = db_session.query(EventAccount).filter(EventAccount.login_id == "SUPER01").one()
    assert super01.role == EventRole.SUPER_ADMIN
    assert super01.is_active is True
    assert verify_password("1td24ai057", super01.password_hash)
    assert db_session.query(EventAccount).filter(EventAccount.login_id == "SUPER02").one().is_active is False
    assert db_session.query(EventAccount).filter(EventAccount.login_id == "ADMIN01").one().is_active is False
    assert db_session.query(User).filter(User.is_active.is_(True)).count() == 0

    profiles = db_session.query(AxiomProfile).all()
    assert len(profiles) == 24
    assert sum(p.roster_type == AxiomRosterType.MENTOR_CANDIDATE for p in profiles) == 7
    assert sum(p.roster_type == AxiomRosterType.MEMBER for p in profiles) == 17
    assert all("archisha" not in p.full_name.lower() for p in profiles)

    tharun = db_session.query(EventAccount).filter(
        EventAccount.login_id == "24UG1BYAI038@BMSIT.IN"
    ).one()
    assert verify_password("9030847016", tharun.password_hash)
    tharun_profile = db_session.get(AxiomProfile, tharun.id)
    assert tharun_profile.roster_type == AxiomRosterType.MEMBER
    assert tharun_profile.role_choice == AxiomRoleChoice.PARTICIPANT


def test_provisioning_is_idempotent(db_session):
    first = provision_axiom_accounts(db_session)
    second = provision_axiom_accounts(db_session)

    assert first["applied"] is True
    assert second["applied"] is False
    assert db_session.query(AxiomProfile).count() == 24
    assert db_session.query(EventPasswordVerifier).count() == 0


def test_axiom_member_can_replace_initial_password(client, db_session):
    provision_axiom_accounts(db_session)
    account = db_session.query(EventAccount).filter(
        EventAccount.login_id == "24UG1BYAI038@BMSIT.IN"
    ).one()
    token = create_access_token(subject=account.id, role=account.role.value)

    response = client.post(
        "/api/v1/axiom/password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "9030847016",
            "new_password": "AxiomFuture42",
            "new_password_confirmation": "AxiomFuture42",
        },
    )

    assert response.status_code == 200
    db_session.refresh(account)
    assert verify_password("AxiomFuture42", account.password_hash)
    assert not verify_password("9030847016", account.password_hash)
    assert db_session.get(AxiomProfile, account.id).must_change_password is False


def test_later_roster_version_preserves_user_changed_passwords(monkeypatch, db_session):
    import app.services.axiom_bootstrap_service as bootstrap_service

    provision_axiom_accounts(db_session)
    member = db_session.query(EventAccount).filter(
        EventAccount.login_id == "24UG1BYAI038@BMSIT.IN"
    ).one()
    member.password_hash = get_password_hash("MemberChanged42")
    member_profile = db_session.get(AxiomProfile, member.id)
    member_profile.must_change_password = False

    super01 = db_session.query(EventAccount).filter(EventAccount.login_id == "SUPER01").one()
    super01.password_hash = get_password_hash("SuperChanged42")
    db_session.commit()

    next_roster = load_axiom_roster()
    next_roster["version"] = "axiom-roster-future-version"
    monkeypatch.setattr(bootstrap_service, "load_axiom_roster", lambda: next_roster)
    provision_axiom_accounts(db_session)

    db_session.refresh(member)
    db_session.refresh(super01)
    assert verify_password("MemberChanged42", member.password_hash)
    assert verify_password("SuperChanged42", super01.password_hash)
    assert db_session.get(AxiomProfile, member.id).must_change_password is False


def test_axiom_login_locks_for_twelve_hours_after_ten_failures(monkeypatch, client, db_session):
    import app.api.routes.r1_event as login_routes

    provision_axiom_accounts(db_session)
    account = db_session.query(EventAccount).filter(
        EventAccount.login_id == "24UG1BYAI038@BMSIT.IN"
    ).one()

    async def reject_password(_account, _password):
        return False

    monkeypatch.setattr(login_routes, "guard_login_rate", lambda _login_id: None)
    monkeypatch.setattr(login_routes, "verify_event_password", reject_password)
    for _ in range(10):
        response = client.post(
            "/api/v1/r1/login",
            json={"login_id": account.login_id, "password": "definitely-wrong"},
        )
        assert response.status_code == 401

    guard = db_session.get(AxiomLoginGuard, account.id)
    assert guard is not None
    assert guard.locked_until is not None
    locked = client.post(
        "/api/v1/r1/login",
        json={"login_id": account.login_id, "password": "9030847016"},
    )
    assert locked.status_code == 423


def test_participant_accepts_agreement_and_saves_ranked_project_response(
    monkeypatch, client, db_session
):
    import app.api.routes.axiom as axiom_routes

    provision_axiom_accounts(db_session)
    mentor = db_session.query(AxiomProfile).filter(
        AxiomProfile.roster_type == AxiomRosterType.MENTOR_CANDIDATE
    ).first()
    participant = db_session.query(AxiomProfile).filter(
        AxiomProfile.roster_type == AxiomRosterType.MEMBER
    ).first()
    assert mentor is not None and participant is not None

    mentor.role_choice = AxiomRoleChoice.MENTOR
    statement = AxiomProblemStatement(
        id="axps-test-project",
        mentor_account_id=mentor.account_id,
        title="Internal Knowledge Atlas",
        domain="Knowledge systems",
        project_track="PRODUCT",
        problem_statement="Build a searchable map of the club's reusable knowledge and project decisions.",
        project_context="Create a small, maintainable prototype that helps future teams find what already exists and understand why earlier choices were made.",
        helpful_skills="Research, interface design, writing",
        status=AxiomStatementStatus.SUBMITTED,
        submitted_at=datetime(2026, 11, 3, 15, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
    )
    db_session.add(statement)
    db_session.commit()

    account = db_session.get(EventAccount, participant.account_id)
    token = create_access_token(subject=account.id, role=account.role.value)
    headers = {"Authorization": f"Bearer {token}"}
    agreement = client.post(
        "/api/v1/axiom/agreement", headers=headers, json={"accepted": True}
    )
    assert agreement.status_code == 200
    assert db_session.get(AxiomOriginalityAgreement, account.id) is not None

    monkeypatch.setattr(
        axiom_routes,
        "now_ist",
        lambda: datetime(2026, 11, 3, 16, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
    )
    projects = client.get("/api/v1/axiom/projects", headers=headers)
    assert projects.status_code == 200
    assert projects.json()["data"]["projects"][0]["id"] == statement.id

    saved = client.put(
        "/api/v1/axiom/preferences",
        headers=headers,
        json={
            "preferences": [{
                "statement_id": statement.id,
                "preference_rank": 1,
                "proposed_solution": "I would interview core members, define a lightweight taxonomy, and prototype a fast searchable archive.",
                "contribution": "I can structure information, test the interface, and document the final workflow.",
            }]
        },
    )
    assert saved.status_code == 200
    preference = db_session.query(AxiomProjectPreference).one()
    assert preference.participant_account_id == account.id
    assert preference.statement_id == statement.id
    assert preference.preference_rank == 1


def test_team_lead_can_submit_two_briefs_and_participant_can_publish_one_call(
    monkeypatch, client, db_session
):
    import app.api.routes.axiom as axiom_routes

    provision_axiom_accounts(db_session)
    lead = db_session.query(AxiomProfile).filter(
        AxiomProfile.roster_type == AxiomRosterType.MENTOR_CANDIDATE
    ).first()
    participant = db_session.query(AxiomProfile).filter(
        AxiomProfile.roster_type == AxiomRosterType.MEMBER
    ).first()
    assert lead is not None and participant is not None
    lead.role_choice = AxiomRoleChoice.MENTOR
    db_session.commit()
    monkeypatch.setattr(
        axiom_routes, "now_ist", lambda: datetime(2026, 11, 3, 12, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    )
    lead_headers = {"Authorization": f"Bearer {create_access_token(subject=lead.account_id, role='PARTICIPANT')}"}
    participant_headers = {"Authorization": f"Bearer {create_access_token(subject=participant.account_id, role='PARTICIPANT')}"}
    payload = {
        "title": "Club Knowledge Map", "domain": "Education", "project_track": "PRODUCT",
        "problem_statement": "Build a searchable, maintainable map of the club's reusable knowledge and project decisions.",
        "project_context": "Create a focused internal prototype that helps future members discover prior work, decisions, and useful assets without losing institutional memory.",
        "helpful_skills": "Research, interface design", "submit": True,
    }
    assert client.put("/api/v1/axiom/team-lead/statements/1", headers=lead_headers, json=payload).status_code == 200
    payload["title"] = "Accessibility Toolkit"
    assert client.put("/api/v1/axiom/team-lead/statements/2", headers=lead_headers, json=payload).status_code == 200
    payload["title"] = "Participant Innovation Call"
    response = client.put("/api/v1/axiom/participant/statement", headers=participant_headers, json=payload)
    assert response.status_code == 200, response.json()
    assert db_session.query(AxiomProblemStatement).filter(AxiomProblemStatement.mentor_account_id == lead.account_id).count() == 2
    assert db_session.query(AxiomProblemStatement).filter(AxiomProblemStatement.mentor_account_id == participant.account_id).count() == 1
