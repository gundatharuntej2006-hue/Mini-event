import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.team import Team
from app.models.participant import Participant
from app.models.event_settings import EventSettings
from app.models.registration_submission import RegistrationSubmission, SubmissionStatus
from app.core.security import create_access_token


@pytest.fixture
def webhook_secret(db_session: Session) -> str:
    settings = db_session.query(EventSettings).first()
    if not settings:
        settings = EventSettings(
            id=1,
            event_name="EVENT HQ · BMSIT 2026",
            webhook_secret="whsec_test_secret_1234567890abcdef",
            registration_auto_approve=False,
            public_registration_open=True,
        )
        db_session.add(settings)
        db_session.commit()
    elif not getattr(settings, "webhook_secret", None):
        settings.webhook_secret = "whsec_test_secret_1234567890abcdef"
        settings.registration_auto_approve = False
        db_session.commit()
    return settings.webhook_secret


def test_webhook_unauthorized_without_secret(client: TestClient):
    response = client.post(
        "/api/v1/integrations/google-forms/webhook",
        json={"team_name": "Test Squad"},
    )
    assert response.status_code == 401
    assert "Invalid or missing webhook secret" in response.json()["message"]


def test_webhook_unauthorized_with_wrong_secret(client: TestClient):
    response = client.post(
        "/api/v1/integrations/google-forms/webhook",
        headers={"X-Webhook-Secret": "wrong_secret_key"},
        json={"team_name": "Test Squad"},
    )
    assert response.status_code == 401


def test_webhook_manual_review_default(client: TestClient, db_session: Session, webhook_secret: str, organizer_headers: dict):
    # Ensure auto-approval is False (Manual review default)
    event_settings = db_session.query(EventSettings).first()
    event_settings.registration_auto_approve = False
    db_session.commit()

    teams_before = db_session.query(Team).count()
    participants_before = db_session.query(Participant).count()

    payload = {
        "submission_id": "test_gform_manual_001",
        "team_name": "Alpha Titans",
        "leader": {
            "name": "Arun Sharma",
            "usn": "1BY23CS801",
            "email": "arun801@bmsit.in",
            "phone": "9876543210"
        },
        "members": [
            {"name": "Bhavya K", "usn": "1BY23CS802", "email": "bhavya802@bmsit.in", "phone": "9876543211"},
            {"name": "Chirag N", "usn": "1BY23CS803", "email": "chirag803@bmsit.in", "phone": "9876543212"},
            {"name": "Divya R", "usn": "1BY23CS804", "email": "divya804@bmsit.in", "phone": "9876543213"},
            {"name": "Esha P", "usn": "1BY23CS805", "email": "esha805@bmsit.in", "phone": "9876543214"},
        ],
        "consent_given": True,
    }

    response = client.post(
        "/api/v1/integrations/google-forms/webhook",
        headers={"X-Webhook-Secret": webhook_secret},
        json=payload,
    )
    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["status"] == "PENDING"
    assert res_data["team_name"] == "Alpha Titans"
    assert res_data["members_count"] == 5
    assert res_data["created_team_id"] is None

    # Submissions remain PENDING in DB and do not create teams yet!
    assert db_session.query(Team).count() == teams_before
    assert db_session.query(Participant).count() == participants_before

    submission_id = res_data["id"]

    # Now organizer explicitly approves the submission
    approve_res = client.post(
        f"/api/v1/integrations/submissions/{submission_id}/action",
        headers=organizer_headers,
        json={"action": "approve"},
    )
    assert approve_res.status_code == 200
    approved_data = approve_res.json()["data"]
    assert approved_data["status"] == "ACCEPTED"
    assert approved_data["created_team_id"] is not None

    # Database now contains the team and all 5 participants
    assert db_session.query(Team).count() == teams_before + 1
    assert db_session.query(Participant).count() == participants_before + 5

    created_team = db_session.query(Team).filter(Team.id == approved_data["created_team_id"]).first()
    assert created_team is not None
    assert created_team.name == "Alpha Titans"
    assert len(created_team.members) == 5


def test_webhook_idempotency(client: TestClient, db_session: Session, webhook_secret: str):
    payload = {
        "submission_id": "test_idempotent_sub_01",
        "team_name": "Idempotent Squad",
        "leader": {
            "name": "Leader One",
            "usn": "1BY23CS811",
            "email": "lead811@bmsit.in",
        },
        "members": [
            {"name": "M2", "usn": "1BY23CS812", "email": "m812@bmsit.in"},
            {"name": "M3", "usn": "1BY23CS813", "email": "m813@bmsit.in"},
            {"name": "M4", "usn": "1BY23CS814", "email": "m814@bmsit.in"},
            {"name": "M5", "usn": "1BY23CS815", "email": "m815@bmsit.in"},
        ],
        "consent_given": True,
    }

    res1 = client.post(
        "/api/v1/integrations/google-forms/webhook",
        headers={"X-Webhook-Secret": webhook_secret},
        json=payload,
    )
    assert res1.status_code == 200
    sub_id1 = res1.json()["data"]["id"]

    # Re-submit exact same submission ID
    res2 = client.post(
        "/api/v1/integrations/google-forms/webhook",
        headers={"X-Webhook-Secret": webhook_secret},
        json=payload,
    )
    assert res2.status_code == 200
    sub_id2 = res2.json()["data"]["id"]
    assert sub_id1 == sub_id2


def test_webhook_validation_rejection(client: TestClient, db_session: Session, webhook_secret: str):
    # Squad with only 3 members (invalid)
    payload_invalid = {
        "submission_id": "test_invalid_sub_01",
        "team_name": "Short Squad",
        "leader": {
            "name": "Leader Only",
            "usn": "1BY23CS821",
            "email": "lead821@bmsit.in",
        },
        "members": [
            {"name": "M2", "usn": "1BY23CS822", "email": "m822@bmsit.in"},
            {"name": "M3", "usn": "1BY23CS823", "email": "m823@bmsit.in"},
        ],
        "consent_given": True,
    }

    res = client.post(
        "/api/v1/integrations/google-forms/webhook",
        headers={"X-Webhook-Secret": webhook_secret},
        json=payload_invalid,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "REJECTED"
    assert "exactly 5 participants" in data["error_message"]


def test_public_registration_endpoint(client: TestClient, db_session: Session):
    payload = {
        "team_name": "Web Registered Unit",
        "leader": {
            "name": "Web Leader",
            "usn": "1BY23CS831",
            "email": "weblead@bmsit.in",
            "phone": "9988776655",
        },
        "members": [
            {"name": "Cadet 2", "usn": "1BY23CS832", "email": "wcadet2@bmsit.in"},
            {"name": "Cadet 3", "usn": "1BY23CS833", "email": "wcadet3@bmsit.in"},
            {"name": "Cadet 4", "usn": "1BY23CS834", "email": "wcadet4@bmsit.in"},
            {"name": "Cadet 5", "usn": "1BY23CS835", "email": "wcadet5@bmsit.in"},
        ],
        "consent_given": True,
    }

    res = client.post(
        "/api/v1/integrations/registration/public-submit",
        json=payload,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "PENDING"
    assert data["source"] == "public_web"


def test_organizer_settings_and_metrics(client: TestClient, organizer_headers: dict):
    res = client.get(
        "/api/v1/integrations/settings",
        headers=organizer_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "/api/v1/integrations/google-forms/webhook" in data["webhook_url"]
    assert data["webhook_secret"] != ""
    assert "metrics" in data
    assert data["registration_auto_approve"] is False


def test_raw_google_forms_field_mapping(client: TestClient, db_session: Session, webhook_secret: str):
    raw_payload = {
        "submission_id": "gform_raw_test_999",
        "Team Name": "Vanguard Squad",
        "Team Leader - Full Name": "Valerie Lead",
        "Team Leader - BMSIT USN": "1BY23CS991",
        "Team Leader - Email": "valerie991@bmsit.in",
        "Team Leader - Phone": "9876500001",
        "Member 2 - Full Name": "Victor Two",
        "Member 2 - BMSIT USN": "1BY23CS992",
        "Member 2 - Email": "victor992@bmsit.in",
        "Member 3 - Full Name": "Vera Three",
        "Member 3 - BMSIT USN": "1BY23CS993",
        "Member 3 - Email": "vera993@bmsit.in",
        "Member 4 - Full Name": "Vincent Four",
        "Member 4 - BMSIT USN": "1BY23CS994",
        "Member 4 - Email": "vincent994@bmsit.in",
        "Member 5 - Full Name": "Violet Five",
        "Member 5 - BMSIT USN": "1BY23CS995",
        "Member 5 - Email": "violet995@bmsit.in",
        "Consent": "I confirm all 5 members are eligible BMSIT students"
    }

    res = client.post(
        "/api/v1/integrations/google-forms/webhook",
        headers={"X-Webhook-Secret": webhook_secret},
        json=raw_payload,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "PENDING"
    assert data["team_name"] == "Vanguard Squad"
    assert data["leader_name"] == "Valerie Lead"
    assert data["leader_usn"] == "1BY23CS991"
    assert data["members_count"] == 5

