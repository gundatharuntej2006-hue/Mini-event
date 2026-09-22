from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import require_role, get_current_user
from app.models.user import User, UserRole
from app.models.registration_submission import RegistrationSubmission, SubmissionStatus
from app.schemas.common import ApiResponse
from app.schemas.integration import (
    SubmissionResponse,
    SubmissionMetricsResponse,
    IntegrationSettingsResponse,
    IntegrationSettingsUpdate,
    SubmissionActionInput,
)
from app.services.integration_service import (
    verify_webhook_secret,
    process_external_registration,
    approve_submission,
    reject_submission,
    retry_submission,
    get_submission_metrics,
    regenerate_webhook_secret,
    serialize_submission,
)
from app.services.dashboard_service import get_or_create_settings

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.post("/google-forms/webhook", response_model=ApiResponse[SubmissionResponse])
async def google_forms_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
    authorization: Optional[str] = Header(None),
):
    """
    Secure webhook endpoint for Google Forms and Google Sheets Apps Script integration.
    Requires secret verification via X-Webhook-Secret header.
    """
    secret_candidate = x_webhook_secret
    if not secret_candidate and authorization and authorization.startswith("Bearer "):
        secret_candidate = authorization[7:]

    if not verify_webhook_secret(db, secret_candidate):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing webhook secret. Access denied."
        )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload received."
        )

    submission = process_external_registration(db, payload, source="google_forms")
    serialized = serialize_submission(submission)

    if submission.status == SubmissionStatus.REJECTED.value:
        return ApiResponse(
            success=False,
            data=serialized,
            message=f"Submission rejected: {submission.error_message}"
        )
    elif submission.status == SubmissionStatus.ACCEPTED.value:
        return ApiResponse(
            success=True,
            data=serialized,
            message="Google Form squad registration accepted and added to tournament roster."
        )
    else:
        return ApiResponse(
            success=True,
            data=serialized,
            message="Google Form registration received and queued for Organizer review."
        )


@router.post("/registration/public-submit", response_model=ApiResponse[SubmissionResponse])
async def public_registration_submit(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public self-registration endpoint for teams filling out the Event HQ web registration form.
    """
    event_settings = get_or_create_settings(db)
    if not getattr(event_settings, "public_registration_open", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public team registration is currently closed by tournament organizers."
        )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload received."
        )

    submission = process_external_registration(db, payload, source="public_web")
    serialized = serialize_submission(submission)

    if submission.status == SubmissionStatus.REJECTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration error: {submission.error_message}"
        )

    msg = (
        "Squad registered successfully and added to tournament!"
        if submission.status == SubmissionStatus.ACCEPTED.value
        else "Squad registration submitted successfully! Your submission is pending Organizer review."
    )

    return ApiResponse(
        success=True,
        data=serialized,
        message=msg
    )


@router.get("/settings", response_model=ApiResponse[IntegrationSettingsResponse])
def get_integration_settings(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER])),
):
    """
    Returns Google Forms webhook URL, secret token, and submission statistics for Organizer review.
    """
    event_settings = get_or_create_settings(db)
    metrics = get_submission_metrics(db)

    base_url = str(request.base_url).rstrip("/")
    webhook_url = f"{base_url}/api/v1/integrations/google-forms/webhook"

    return ApiResponse(
        data=IntegrationSettingsResponse(
            webhook_url=webhook_url,
            webhook_secret=getattr(event_settings, "webhook_secret", ""),
            registration_auto_approve=getattr(event_settings, "registration_auto_approve", False),
            public_registration_open=getattr(event_settings, "public_registration_open", True),
            metrics=metrics,
        ),
        message="Integration settings retrieved"
    )


@router.patch("/settings", response_model=ApiResponse[IntegrationSettingsResponse])
def update_integration_settings(
    update_in: IntegrationSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER])),
):
    event_settings = get_or_create_settings(db)

    if update_in.registration_auto_approve is not None:
        event_settings.registration_auto_approve = update_in.registration_auto_approve

    if update_in.public_registration_open is not None:
        event_settings.public_registration_open = update_in.public_registration_open

    if update_in.regenerate_secret:
        regenerate_webhook_secret(db)

    db.commit()
    db.refresh(event_settings)

    metrics = get_submission_metrics(db)
    base_url = str(request.base_url).rstrip("/")
    webhook_url = f"{base_url}/api/v1/integrations/google-forms/webhook"

    return ApiResponse(
        data=IntegrationSettingsResponse(
            webhook_url=webhook_url,
            webhook_secret=getattr(event_settings, "webhook_secret", ""),
            registration_auto_approve=getattr(event_settings, "registration_auto_approve", False),
            public_registration_open=getattr(event_settings, "public_registration_open", True),
            metrics=metrics,
        ),
        message="Integration settings updated successfully"
    )


@router.get("/submissions", response_model=ApiResponse[List[SubmissionResponse]])
def list_submissions(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    query = db.query(RegistrationSubmission)
    if status_filter:
        query = query.filter(RegistrationSubmission.status == status_filter.upper())

    submissions = (
        query.order_by(RegistrationSubmission.submitted_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return ApiResponse(
        data=[serialize_submission(s) for s in submissions],
        message=f"Retrieved {len(submissions)} registration submissions"
    )


@router.post("/submissions/{submission_id}/action", response_model=ApiResponse[SubmissionResponse])
def handle_submission_action(
    submission_id: str,
    action_in: SubmissionActionInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER])),
):
    act = action_in.action.lower().strip()
    if act == "approve":
        submission = approve_submission(db, submission_id, current_user.email)
        msg = f"Squad '{submission.team_name}' approved and registered in tournament roster."
    elif act == "reject":
        submission = reject_submission(db, submission_id, action_in.reason, current_user.email)
        msg = f"Submission for '{submission.team_name}' rejected."
    elif act == "retry":
        submission = retry_submission(db, submission_id, current_user.email)
        msg = f"Squad '{submission.team_name}' registration re-attempted and approved."
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown action '{action_in.action}'. Must be 'approve', 'reject', or 'retry'."
        )

    return ApiResponse(
        data=serialize_submission(submission),
        message=msg
    )


@router.post("/google-forms/test-payload", response_model=ApiResponse[SubmissionResponse])
def test_google_forms_simulation(
    test_payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER])),
):
    """
    Organizer simulation tool to trigger a test Google Form submission directly from Event HQ.
    """
    payload = test_payload or {
        "submission_id": f"sim_{uuid.uuid4().hex[:12]}",
        "team_name": f"Simulated Squad {uuid.uuid4().hex[:4].upper()}",
        "leader": {
            "name": "Simulated Leader",
            "usn": f"1BY23CS{secrets.randbelow(899)+100}",
            "email": f"sim_leader_{secrets.randbelow(999)}@bmsit.in",
            "phone": "9876543210"
        },
        "members": [
            {
                "name": f"Simulated Cadet {i}",
                "usn": f"1BY23CS{secrets.randbelow(899)+100}",
                "email": f"sim_cadet_{i}_{secrets.randbelow(999)}@bmsit.in",
                "phone": f"987654321{i}"
            }
            for i in range(2, 6)
        ],
        "consent_given": True
    }

    submission = process_external_registration(db, payload, source="google_forms")
    return ApiResponse(
        data=serialize_submission(submission),
        message="Simulation submission processed"
    )
