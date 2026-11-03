from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.axiom import (
    AxiomLoginGuard,
    AxiomProjectAccessAgreement,
    AxiomProjectApplication,
    AxiomProjectTeamSelection,
    AxiomProblemStatement,
    AxiomProfile,
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


def test_signed_access_open_projects_and_publisher_controlled_selection(monkeypatch, client, db_session):
    import app.api.routes.axiom as axiom_routes

    provision_axiom_accounts(db_session)
    publisher, applicant = db_session.query(AxiomProfile).order_by(AxiomProfile.full_name).limit(2).all()
    publisher_headers = {"Authorization": f"Bearer {create_access_token(subject=publisher.account_id, role='PARTICIPANT')}"}
    applicant_headers = {"Authorization": f"Bearer {create_access_token(subject=applicant.account_id, role='PARTICIPANT')}"}

    def sign(profile, headers):
        return client.post("/api/v1/axiom/agreement", headers=headers, json={
            "accepted": True, "full_name": profile.full_name, "college_email": profile.college_email,
        })

    signed = sign(publisher, publisher_headers)
    assert signed.status_code == 200, signed.json()
    assert len(signed.json()["data"]["document_hash"]) == 64
    evidence = db_session.query(AxiomProjectAccessAgreement).filter_by(account_id=publisher.account_id).one()
    assert len(evidence.evidence_seal) == 64
    assert sign(applicant, applicant_headers).status_code == 200

    payload = {
        "title": "Club Knowledge Map", "domain": "Education", "project_track": "PRODUCT",
        "problem_statement": "Build a searchable, maintainable map of the club's reusable knowledge and project decisions.",
        "project_context": "Create a focused internal prototype that helps future members discover prior work, decisions, and useful assets without losing institutional memory.",
        "helpful_skills": "Research, interface design", "submit": True,
        "client_request_id": "publish-request-00000001",
    }
    first = client.post("/api/v1/axiom/projects", headers=publisher_headers, json=payload)
    assert first.status_code == 200, first.json()
    retry = client.post("/api/v1/axiom/projects", headers=publisher_headers, json=payload)
    assert retry.status_code == 200, retry.json()
    assert retry.json()["data"]["id"] == first.json()["data"]["id"]
    payload["title"] = "Accessibility Toolkit"
    payload["client_request_id"] = "publish-request-00000002"
    assert client.post("/api/v1/axiom/projects", headers=publisher_headers, json=payload).status_code == 200
    project_id = first.json()["data"]["id"]
    assert db_session.query(AxiomProblemStatement).filter_by(mentor_account_id=publisher.account_id).count() == 2

    application = client.put(f"/api/v1/axiom/projects/{project_id}/application", headers=applicant_headers, json={
        "proposed_solution": "I would map member needs, prototype the fastest workflow, test it with the core group and document every decision.",
        "contribution": "I can research, build interfaces and test the final flow.",
    })
    assert application.status_code == 200, application.json()
    assert db_session.query(AxiomProjectApplication).count() == 1
    selected = client.put(f"/api/v1/axiom/projects/{project_id}/selections", headers=publisher_headers, json={
        "participant_account_ids": [applicant.account_id],
    })
    assert selected.status_code == 200, selected.json()
    assert selected.json()["data"]["team_size"] == 2
    assert db_session.query(AxiomProjectTeamSelection).count() == 1

    monkeypatch.setattr(axiom_routes, "now_ist", lambda: datetime(2026, 11, 4, 15, 1, tzinfo=ZoneInfo("Asia/Kolkata")))
    assert client.put(f"/api/v1/axiom/projects/{project_id}/selections", headers=publisher_headers, json={"participant_account_ids": []}).status_code == 409
