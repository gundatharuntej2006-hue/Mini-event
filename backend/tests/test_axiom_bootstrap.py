from app.core.security import verify_password
from app.models.axiom import AxiomProfile, AxiomRosterType
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
    assert sum(item["roster_type"] == "MENTOR_CANDIDATE" for item in roster["people"]) == 8
    assert sum(item["roster_type"] == "MEMBER" for item in roster["people"]) == 16


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
    assert sum(p.roster_type == AxiomRosterType.MENTOR_CANDIDATE for p in profiles) == 8
    assert sum(p.roster_type == AxiomRosterType.MEMBER for p in profiles) == 16
    assert all("archisha" not in p.full_name.lower() for p in profiles)

    tharun = db_session.query(EventAccount).filter(
        EventAccount.login_id == "24UG1BYAI038@BMSIT.IN"
    ).one()
    assert verify_password("9030847016", tharun.password_hash)


def test_provisioning_is_idempotent(db_session):
    first = provision_axiom_accounts(db_session)
    second = provision_axiom_accounts(db_session)

    assert first["applied"] is True
    assert second["applied"] is False
    assert db_session.query(AxiomProfile).count() == 24
    assert db_session.query(EventPasswordVerifier).count() == 0
