import hmac
import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import utc_now
from app.models.event_settings import EventSettings
from app.models.registration_submission import RegistrationSubmission, SubmissionStatus
from app.models.team import Team
from app.models.participant import Participant, ParticipantRole
from app.schemas.team import TeamCreate, TeamMemberInput
from app.schemas.integration import (
    ExternalRegistrationInput,
    ExternalParticipantInput,
    SubmissionResponse,
    SubmissionMetricsResponse,
    IntegrationSettingsResponse,
)
from app.services.team_service import create_team
from app.services.dashboard_service import get_or_create_settings


def verify_webhook_secret(db: Session, provided_secret: Optional[str]) -> bool:
    if not provided_secret:
        return False
    
    event_settings = get_or_create_settings(db)
    active_secret = getattr(event_settings, "webhook_secret", None) or settings.GOOGLE_FORMS_WEBHOOK_SECRET
    
    if not active_secret:
        return False
    
    return hmac.compare_digest(provided_secret.strip(), active_secret.strip())


def parse_and_normalize_members(
    payload: Dict[str, Any]
) -> Tuple[str, List[Dict[str, Any]], bool]:
    """
    Parses both structured JSON and raw Google Form field submissions into:
    (team_name, normalized_5_members_list, consent_given)
    """
    team_name = ""
    members: List[Dict[str, Any]] = []
    consent_given = False

    # 1. Check if structured format with 'leader' and 'members'
    if "team_name" in payload:
        team_name = str(payload.get("team_name", "")).strip()

    consent_given = bool(
        payload.get("consent_given")
        or payload.get("consent")
        or payload.get("agreement")
        or payload.get("declaration")
        or True  # fallback if submitted via valid form
    )

    if "leader" in payload and isinstance(payload["leader"], dict):
        leader = payload["leader"]
        members.append({
            "name": str(leader.get("name", "")).strip(),
            "usn": str(leader.get("usn", "")).strip().upper(),
            "email": str(leader.get("email", "")).strip().lower(),
            "phone": str(leader.get("phone", "")).strip() if leader.get("phone") else None,
            "role": ParticipantRole.LEADER,
        })
        
        other_members = payload.get("members", [])
        if isinstance(other_members, list):
            for m in other_members:
                if isinstance(m, dict):
                    members.append({
                        "name": str(m.get("name", "")).strip(),
                        "usn": str(m.get("usn", "")).strip().upper(),
                        "email": str(m.get("email", "")).strip().lower(),
                        "phone": str(m.get("phone", "")).strip() if m.get("phone") else None,
                        "role": ParticipantRole.MEMBER,
                    })

    # 2. Check if direct list of 5 members under 'members'
    elif "members" in payload and isinstance(payload["members"], list) and len(payload["members"]) == 5:
        for m in payload["members"]:
            role_val = ParticipantRole.LEADER if str(m.get("role", "")).lower() == "leader" else ParticipantRole.MEMBER
            members.append({
                "name": str(m.get("name", "")).strip(),
                "usn": str(m.get("usn", "")).strip().upper(),
                "email": str(m.get("email", "")).strip().lower(),
                "phone": str(m.get("phone", "")).strip() if m.get("phone") else None,
                "role": role_val,
            })

    # 3. Flexible Google Form question field mapping (e.g. from Google Sheets or Form trigger)
    else:
        norm_payload = {
            re.sub(r'[^a-z0-9]', '', str(k).lower()): str(v).strip()
            for k, v in payload.items()
            if v is not None and str(v).strip()
        }

        def find_field(predicate) -> str:
            for nk, val in norm_payload.items():
                if predicate(nk):
                    return val
            return ""

        # Extract Team Name
        if not team_name:
            team_name = find_field(
                lambda k: ("teamname" in k or "squadname" in k or k in ("team", "squad")) and "leader" not in k
            )

        # Extract Leader fields
        leader_name = (
            payload.get("Leader Name")
            or payload.get("leader_name")
            or payload.get("Leader Full Name")
            or find_field(lambda k: ("leader" in k or "member1" in k or "participant1" in k) and ("name" in k or "full" in k) and "teamname" not in k)
            or find_field(lambda k: k in ("leader", "teamleader", "member1", "participant1"))
        )
        leader_usn = (
            payload.get("Leader USN")
            or payload.get("leader_usn")
            or find_field(lambda k: ("leader" in k or "member1" in k or "participant1" in k) and "usn" in k)
        )
        leader_email = (
            payload.get("Leader Email")
            or payload.get("leader_email")
            or find_field(lambda k: ("leader" in k or "member1" in k or "participant1" in k) and ("email" in k or "mail" in k))
        )
        leader_phone = (
            payload.get("Leader Phone")
            or payload.get("leader_phone")
            or find_field(lambda k: ("leader" in k or "member1" in k or "participant1" in k) and ("phone" in k or "mobile" in k or "contact" in k or "tel" in k))
        )

        if leader_name and leader_usn:
            members.append({
                "name": str(leader_name).strip(),
                "usn": str(leader_usn).strip().upper(),
                "email": str(leader_email).strip().lower(),
                "phone": str(leader_phone).strip() if leader_phone else None,
                "role": ParticipantRole.LEADER,
            })

        # Extract Members 2 to 5
        for i in range(2, 6):
            m_name = (
                payload.get(f"Member {i} Name")
                or payload.get(f"Member {i} Full Name")
                or payload.get(f"member_{i}_name")
                or payload.get(f"Participant {i} Name")
                or find_field(lambda k, idx=i: (f"member{idx}" in k or f"participant{idx}" in k or f"cadet{idx}" in k) and ("name" in k or "full" in k or k in (f"member{idx}", f"participant{idx}")))
            )
            m_usn = (
                payload.get(f"Member {i} USN")
                or payload.get(f"member_{i}_usn")
                or payload.get(f"Participant {i} USN")
                or find_field(lambda k, idx=i: (f"member{idx}" in k or f"participant{idx}" in k or f"cadet{idx}" in k) and "usn" in k)
            )
            m_email = (
                payload.get(f"Member {i} Email")
                or payload.get(f"member_{i}_email")
                or payload.get(f"Participant {i} Email")
                or find_field(lambda k, idx=i: (f"member{idx}" in k or f"participant{idx}" in k or f"cadet{idx}" in k) and ("email" in k or "mail" in k))
            )
            m_phone = (
                payload.get(f"Member {i} Phone")
                or payload.get(f"member_{i}_phone")
                or payload.get(f"Participant {i} Phone")
                or find_field(lambda k, idx=i: (f"member{idx}" in k or f"participant{idx}" in k or f"cadet{idx}" in k) and ("phone" in k or "mobile" in k or "contact" in k or "tel" in k))
            )

            if m_name and m_usn:
                members.append({
                    "name": str(m_name).strip(),
                    "usn": str(m_usn).strip().upper(),
                    "email": str(m_email).strip().lower(),
                    "phone": str(m_phone).strip() if m_phone else None,
                    "role": ParticipantRole.MEMBER,
                })

    return team_name, members, consent_given


def validate_members_roster(db: Session, team_name: str, members: List[Dict[str, Any]]) -> Optional[str]:
    """
    Returns an error message if invalid, or None if completely valid.
    """
    if not team_name or not team_name.strip():
        return "Team name is required."

    if len(members) != 5:
        return f"A squad must have exactly 5 participants (found {len(members)})."

    leaders = [m for m in members if m.get("role") == ParticipantRole.LEADER]
    if len(leaders) != 1:
        return f"A squad must have exactly one leader (found {len(leaders)})."

    for i, m in enumerate(members, 1):
        if not m.get("name") or not str(m.get("name")).strip():
            return f"Participant {i} full name is required."
        if not m.get("usn") or not str(m.get("usn")).strip():
            return f"Participant {i} USN is required."
        if not m.get("email") or not str(m.get("email")).strip():
            return f"Participant {i} institutional email is required."

    # Intra-form uniqueness
    usns = [str(m["usn"]).strip().upper() for m in members]
    if len(usns) != len(set(usns)):
        return "Duplicate USN detected among squad members."

    emails = [str(m["email"]).strip().lower() for m in members]
    if len(emails) != len(set(emails)):
        return "Duplicate institutional email detected among squad members."

    # Database capacity check
    current_team_count = db.query(func.count(Team.id)).scalar() or 0
    if current_team_count >= 32:
        return "Tournament capacity reached. Maximum of 32 squads can be registered."

    # Database team name collision check
    existing_team = db.query(Team).filter(Team.name.ilike(team_name.strip())).first()
    if existing_team:
        return f"A team named '{team_name.strip()}' is already registered."

    # Database duplicate USN check
    for usn in usns:
        existing_p = db.query(Participant).filter(Participant.usn == usn).first()
        if existing_p:
            return f"Participant with USN '{usn}' is already registered."

    # Database duplicate email check
    for email in emails:
        existing_p = db.query(Participant).filter(Participant.email.ilike(email)).first()
        if existing_p:
            return f"Participant with email '{email}' is already registered."

    return None


def process_external_registration(
    db: Session,
    raw_payload: Dict[str, Any],
    source: str = "google_forms"
) -> RegistrationSubmission:
    """
    Processes an incoming registration from Google Forms or the public web form.
    Idempotent, validates roster, adheres to manual review / auto-approval configuration.
    """
    event_settings = get_or_create_settings(db)
    
    # 1. Parse and normalize
    team_name, members, consent_given = parse_and_normalize_members(raw_payload)
    
    # 2. Extract or compute external submission ID for idempotency
    external_id = raw_payload.get("submission_id") or raw_payload.get("response_id")
    if not external_id:
        leader = members[0] if members else {}
        hash_input = f"{team_name}:{leader.get('usn', '')}:{len(members)}"
        external_id = hashlib.sha256(hash_input.encode()).hexdigest()[:24]

    # Check for existing submission
    existing = (
        db.query(RegistrationSubmission)
        .filter(RegistrationSubmission.external_submission_id == external_id)
        .first()
    )
    if existing:
        # Idempotent response
        return existing

    leader = next((m for m in members if m.get("role") == ParticipantRole.LEADER), (members[0] if members else {}))
    leader_name = leader.get("name", "Unknown Leader")
    leader_usn = leader.get("usn", "UNKNOWN")
    leader_email = leader.get("email", "unknown@bmsit.in")
    leader_phone = leader.get("phone")

    # 3. Validate
    validation_error = validate_members_roster(db, team_name, members)
    
    # Determine approval mode: User specified default is MANUAL REVIEW (registration_auto_approve is False)
    auto_approve = getattr(event_settings, "registration_auto_approve", False)

    # Prepare submission record
    submission = RegistrationSubmission(
        id=str(uuid.uuid4()),
        source=source,
        external_submission_id=external_id,
        team_name=team_name or "Unnamed Squad",
        leader_name=leader_name,
        leader_usn=leader_usn,
        leader_email=leader_email,
        leader_phone=leader_phone,
        members_count=len(members),
        consent_given=consent_given,
        raw_payload={
            "team_name": team_name,
            "members": members,
            "consent_given": consent_given,
            "original_payload": raw_payload,
        },
        auto_approved=False,
        submitted_at=utc_now(),
    )

    if validation_error:
        # Reject submission with recorded error for organizer inspection
        submission.status = SubmissionStatus.REJECTED.value
        submission.error_message = validation_error
        submission.processed_at = utc_now()
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return submission

    if auto_approve:
        # If auto-approval is explicitly enabled by Organizer in Event Settings
        try:
            team_create = TeamCreate(
                name=team_name,
                members=[TeamMemberInput(**m) for m in members]
            )
            created_team = create_team(db, team_create)
            submission.status = SubmissionStatus.ACCEPTED.value
            submission.created_team_id = created_team.id
            submission.auto_approved = True
            submission.processed_at = utc_now()
        except Exception as ex:
            submission.status = SubmissionStatus.REJECTED.value
            submission.error_message = str(ex)
            submission.processed_at = utc_now()
    else:
        # DEFAULT: Manual Review mode! Submissions remain PENDING until explicitly approved
        submission.status = SubmissionStatus.PENDING.value
        submission.processed_at = None

    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


def approve_submission(db: Session, submission_id: str, organizer_email: str) -> RegistrationSubmission:
    submission = db.query(RegistrationSubmission).filter(RegistrationSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    if submission.status == SubmissionStatus.ACCEPTED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Submission has already been accepted.")

    payload = submission.raw_payload or {}
    team_name = payload.get("team_name") or submission.team_name
    members_data = payload.get("members", [])

    # Re-validate against current live DB
    validation_error = validate_members_roster(db, team_name, members_data)
    if validation_error:
        submission.error_message = validation_error
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=validation_error)

    # Execute atomic team and 5 participants creation
    try:
        team_create = TeamCreate(
            name=team_name,
            members=[TeamMemberInput(**m) for m in members_data]
        )
        created_team = create_team(db, team_create)
        submission.status = SubmissionStatus.ACCEPTED.value
        submission.created_team_id = created_team.id
        submission.reviewed_by = organizer_email
        submission.error_message = None
        submission.processed_at = utc_now()
        db.commit()
        db.refresh(submission)
        return submission
    except Exception as ex:
        db.rollback()
        detail = getattr(ex, "detail", str(ex))
        submission.error_message = detail
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create squad: {detail}")


def reject_submission(db: Session, submission_id: str, reason: Optional[str], organizer_email: str) -> RegistrationSubmission:
    submission = db.query(RegistrationSubmission).filter(RegistrationSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found.")

    submission.status = SubmissionStatus.REJECTED.value
    submission.error_message = reason or "Rejected by Organizer."
    submission.reviewed_by = organizer_email
    submission.processed_at = utc_now()
    db.commit()
    db.refresh(submission)
    return submission


def retry_submission(db: Session, submission_id: str, organizer_email: str) -> RegistrationSubmission:
    """
    Allows re-attempting registration for a rejected or pending submission.
    """
    return approve_submission(db, submission_id, organizer_email)


def get_submission_metrics(db: Session) -> SubmissionMetricsResponse:
    total = db.query(func.count(RegistrationSubmission.id)).scalar() or 0
    accepted = (
        db.query(func.count(RegistrationSubmission.id))
        .filter(RegistrationSubmission.status == SubmissionStatus.ACCEPTED.value)
        .scalar() or 0
    )
    pending = (
        db.query(func.count(RegistrationSubmission.id))
        .filter(RegistrationSubmission.status == SubmissionStatus.PENDING.value)
        .scalar() or 0
    )
    rejected = (
        db.query(func.count(RegistrationSubmission.id))
        .filter(RegistrationSubmission.status == SubmissionStatus.REJECTED.value)
        .scalar() or 0
    )

    last_sub = (
        db.query(RegistrationSubmission.submitted_at)
        .order_by(RegistrationSubmission.submitted_at.desc())
        .first()
    )
    last_processed = (
        db.query(RegistrationSubmission.processed_at)
        .filter(RegistrationSubmission.processed_at.isnot(None))
        .order_by(RegistrationSubmission.processed_at.desc())
        .first()
    )

    return SubmissionMetricsResponse(
        total_submissions=total,
        accepted_count=accepted,
        pending_count=pending,
        rejected_count=rejected,
        last_submission_at=last_sub[0].isoformat() if last_sub and last_sub[0] else None,
        last_sync_at=last_processed[0].isoformat() if last_processed and last_processed[0] else None,
    )


def regenerate_webhook_secret(db: Session) -> str:
    new_secret = "whsec_" + secrets.token_hex(24)
    event_settings = get_or_create_settings(db)
    event_settings.webhook_secret = new_secret
    event_settings.updated_at = utc_now()
    db.commit()
    db.refresh(event_settings)
    return new_secret


def serialize_submission(submission: RegistrationSubmission) -> SubmissionResponse:
    return SubmissionResponse(
        id=submission.id,
        source=submission.source,
        external_submission_id=submission.external_submission_id,
        team_name=submission.team_name,
        leader_name=submission.leader_name,
        leader_usn=submission.leader_usn,
        leader_email=submission.leader_email,
        leader_phone=submission.leader_phone,
        members_count=submission.members_count,
        consent_given=submission.consent_given,
        status=submission.status,
        error_message=submission.error_message,
        created_team_id=submission.created_team_id,
        raw_payload=submission.raw_payload or {},
        auto_approved=submission.auto_approved,
        submitted_at=submission.submitted_at.isoformat() if submission.submitted_at else "",
        processed_at=submission.processed_at.isoformat() if submission.processed_at else None,
        reviewed_by=submission.reviewed_by,
    )
