import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.axiom import (
    AxiomBootstrapState,
    AxiomProfile,
    AxiomRoleChoice,
    AxiomRosterType,
)
from app.models.event_account import EventAccount, EventPasswordVerifier, EventRole
from app.models.user import User


ROSTER_PATH = Path(__file__).resolve().parents[1] / "db" / "axiom_roster.json"


def load_axiom_roster() -> dict:
    with ROSTER_PATH.open("r", encoding="utf-8") as source:
        return json.load(source)


def provision_axiom_accounts(db: Session) -> dict:
    """Apply the approved Axiom roster exactly once for the declared version.

    Old event accounts are paused, not deleted, so historical ODDyssey records
    and their foreign keys remain intact.
    """
    roster = load_axiom_roster()
    version = roster["version"]
    state = db.get(AxiomBootstrapState, 1)
    if state and state.version == version:
        return {"applied": False, "version": version, "people": len(roster["people"])}

    # Pause both legacy authentication systems. Project Axiom uses EventAccount
    # credentials, with only SUPER01 retaining privileged access.
    db.query(User).update({User.is_active: False}, synchronize_session=False)
    db.query(EventAccount).update({EventAccount.is_active: False}, synchronize_session=False)

    super_data = roster["super_admin"]
    super_account = db.query(EventAccount).filter(
        EventAccount.login_id == super_data["login_id"]
    ).first()
    super_account_existed = super_account is not None
    if not super_account:
        super_account = EventAccount(login_id=super_data["login_id"])
        db.add(super_account)
    super_account.display_name = super_data["display_name"]
    # The first Axiom migration replaces the old event credential. Later roster
    # versions must preserve a password the super admin changed in the portal.
    if state is None or not super_account_existed:
        super_account.password_hash = super_data["password_hash"]
    super_account.role = EventRole.SUPER_ADMIN
    super_account.team_id = None
    super_account.location_number = None
    super_account.is_active = True
    db.flush()
    db.query(EventPasswordVerifier).filter(
        EventPasswordVerifier.account_id == super_account.id
    ).delete(synchronize_session=False)

    approved_emails: set[str] = set()
    for person in roster["people"]:
        email = person["email"].strip().lower()
        login_id = email.upper()
        approved_emails.add(email)

        account = db.query(EventAccount).filter(EventAccount.login_id == login_id).first()
        account_created = account is None
        if not account:
            account = EventAccount(login_id=login_id)
            db.add(account)
        profile = None if account_created else db.get(AxiomProfile, account.id)
        should_apply_initial_password = account_created or not profile or profile.must_change_password
        if should_apply_initial_password:
            account.password_hash = person["password_hash"]
        account.display_name = person["name"].strip()
        account.role = EventRole.PARTICIPANT
        account.team_id = None
        account.location_number = None
        account.is_active = True
        db.flush()

        db.query(EventPasswordVerifier).filter(
            EventPasswordVerifier.account_id == account.id
        ).delete(synchronize_session=False)

        if not profile:
            profile = AxiomProfile(account_id=account.id)
            db.add(profile)
            profile.role_choice = AxiomRoleChoice.PENDING
            profile.must_change_password = True
        profile.full_name = person["name"].strip()
        profile.college_email = email
        profile.roster_type = AxiomRosterType(person["roster_type"])
        profile.is_program_active = True

        # The decision window has closed.  Anyone who did not make a choice
        # joins the participant pool.  The roster can also explicitly place a
        # person in that pool (used for Tharun Tej for this cycle).
        if profile.roster_type == AxiomRosterType.MEMBER or profile.role_choice == AxiomRoleChoice.PENDING:
            profile.role_choice = AxiomRoleChoice.PARTICIPANT

    # Anyone removed from the approved Axiom roster remains in historical
    # event records but has no current programme access.
    for profile in db.query(AxiomProfile).all():
        if profile.college_email not in approved_emails:
            profile.is_program_active = False
            account = db.get(EventAccount, profile.account_id)
            if account:
                account.is_active = False

    if not state:
        state = AxiomBootstrapState(id=1, version=version)
        db.add(state)
    else:
        state.version = version
    db.commit()
    return {"applied": True, "version": version, "people": len(roster["people"])}
