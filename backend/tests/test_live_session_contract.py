from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.routes.r1_event import current_account, me
from app.api.routes.axiom import SelfPasswordChangeInput, change_own_password
from app.api.routes.r3_live import ResetInput, reset_round
from app.core.security import create_access_token, get_password_hash
from app.models.axiom import AxiomProfile, AxiomRoleChoice, AxiomRosterType
from app.models.event_account import EventAccount, EventRole


def test_live_me_reports_authoritative_experience_and_expiry(db_session):
    axiom = EventAccount(
        login_id="AXIOM_SESSION_TEST",
        display_name="Axiom Session Test",
        password_hash=get_password_hash("local-test-password"),
        role=EventRole.PARTICIPANT,
        is_active=True,
    )
    event = EventAccount(
        login_id="EVENT_SESSION_TEST",
        display_name="Event Session Test",
        password_hash=get_password_hash("local-test-password"),
        role=EventRole.ADMIN,
        is_active=True,
    )
    ended_team = EventAccount(
        login_id="ENDED_TEAM_TEST",
        display_name="Ended Event Team",
        password_hash=get_password_hash("local-test-password"),
        role=EventRole.PARTICIPANT,
        is_active=False,
    )
    db_session.add_all([axiom, event, ended_team])
    db_session.flush()
    db_session.add(AxiomProfile(
        account_id=axiom.id,
        full_name="Axiom Session Test",
        college_email="session-test@local.invalid",
        roster_type=AxiomRosterType.MEMBER,
        role_choice=AxiomRoleChoice.PARTICIPANT,
        is_program_active=True,
        must_change_password=False,
        skills="",
    ))
    db_session.commit()

    for account, experience in ((axiom, "axiom"), (event, "event")):
        token = create_access_token(account.id, account.role.value)
        verified = current_account(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), db_session)
        data = me(verified, db_session)["data"]
        assert data["experience"] == experience
        assert data["role"] == account.role.value

    expired = create_access_token(axiom.id, axiom.role.value, expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as error:
        current_account(HTTPAuthorizationCredentials(scheme="Bearer", credentials=expired), db_session)
    assert error.value.status_code == 401

    axiom.is_active = False
    db_session.commit()
    axiom_token = create_access_token(axiom.id, axiom.role.value)
    with pytest.raises(HTTPException) as error:
        current_account(HTTPAuthorizationCredentials(scheme="Bearer", credentials=axiom_token), db_session)
    assert error.value.status_code == 401

    axiom.is_active = True
    db_session.get(AxiomProfile, axiom.id).is_program_active = False
    db_session.commit()
    with pytest.raises(HTTPException) as error:
        current_account(HTTPAuthorizationCredentials(scheme="Bearer", credentials=axiom_token), db_session)
    assert error.value.status_code == 401

    ended_token = create_access_token(ended_team.id, ended_team.role.value)
    with pytest.raises(HTTPException) as error:
        current_account(HTTPAuthorizationCredentials(scheme="Bearer", credentials=ended_token), db_session)
    assert error.value.status_code == 403


def test_wrong_action_password_does_not_invalidate_bearer(db_session):
    account = EventAccount(
        login_id="CONFIRMATION_TEST",
        display_name="Confirmation Test",
        password_hash=get_password_hash("correct-password"),
        role=EventRole.SUPER_ADMIN,
        is_active=True,
    )
    db_session.add(account)
    db_session.commit()
    token = create_access_token(account.id, account.role.value)

    with pytest.raises(HTTPException) as error:
        change_own_password(SelfPasswordChangeInput(
            current_password="wrong-password",
            new_password="replacement-password",
            new_password_confirmation="replacement-password",
        ), account, db_session)
    assert error.value.status_code == 403

    with pytest.raises(HTTPException) as error:
        reset_round(ResetInput(
            password="wrong-password",
            password_confirmation="wrong-password",
            confirmed=True,
            reason="Session contract test",
        ), account, db_session)
    assert error.value.status_code == 403

    verified = current_account(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), db_session)
    assert verified.id == account.id
