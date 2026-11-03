import hashlib
import hmac
import json
import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.routes.r1_event import current_account, require_roles
from app.core.security import get_password_hash, verify_password
from app.core.config import settings
from app.db.session import get_db
from app.models.axiom import (
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


router = APIRouter(prefix="/axiom", tags=["Project Axiom"])
IST = ZoneInfo("Asia/Kolkata")
TEAM_FINALIZATION_DEADLINE = datetime(2026, 11, 4, 15, 0, tzinfo=IST)
ACCESS_AGREEMENT_VERSION = "axiom-project-access-v2"
ACCESS_AGREEMENT_TEXT = """PROJECT AXIOM — CONFIDENTIAL PROJECT ACCESS ACKNOWLEDGEMENT

Project statements, solution approaches, research directions, product concepts, documents and discussions shown in this workspace are confidential internal Club Asymptotes material. They remain the intellectual property of their respective authors and/or Club Asymptotes unless a separate written agreement says otherwise.

By signing, I agree that I will use these materials only to participate in Project Axiom. I will not copy, reproduce, publish, forward, distribute, submit, commercialise, present as my own, or use any project material outside Project Axiom without prior written permission from the author and Club Asymptotes. I will write my own proposal and contribution statements. I understand that access is personal to my signed-in college account, and that this acknowledgement, the agreement version, signing time and integrity evidence will be retained for programme records.

I confirm that the name and college email entered below identify me, that I have read this acknowledgement, and that selecting “Sign and access projects” is my electronic acknowledgement of these terms."""


class StatementInput(BaseModel):
    title: str = Field(min_length=4, max_length=140)
    domain: str = Field(min_length=2, max_length=100)
    project_track: Literal["RESEARCH", "PRODUCT"]
    problem_statement: str = Field(min_length=20, max_length=1200)
    project_context: str = Field(min_length=20, max_length=2400)
    helpful_skills: str = Field(default="", max_length=600)
    submit: bool = False
    # Optional only for rolling-deploy compatibility with an already-open old
    # browser bundle. The current client always sends this idempotency key.
    client_request_id: str | None = Field(default=None, min_length=16, max_length=64)


class SelfPasswordChangeInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=72)
    new_password_confirmation: str = Field(min_length=8, max_length=72)


class AgreementInput(BaseModel):
    accepted: bool
    full_name: str = Field(min_length=2, max_length=120)
    college_email: str = Field(min_length=6, max_length=255)


class ProjectApplicationInput(BaseModel):
    proposed_solution: str = Field(min_length=20, max_length=1400)
    contribution: str = Field(min_length=10, max_length=900)


class ProjectSelectionInput(BaseModel):
    participant_account_ids: list[str] = Field(default_factory=list, max_length=3)


def now_ist() -> datetime:
    return datetime.now(IST)


def profile_for(db: Session, account: EventAccount) -> AxiomProfile:
    profile = db.get(AxiomProfile, account.id)
    if not profile or not profile.is_program_active:
        raise HTTPException(status_code=403, detail="This account is not part of the active Project Axiom roster.")
    return profile


def participant_profile_for(db: Session, account: EventAccount) -> AxiomProfile:
    profile = profile_for(db, account)
    is_participant = (
        profile.roster_type == AxiomRosterType.MEMBER
        or profile.role_choice == AxiomRoleChoice.PARTICIPANT
    )
    if not is_participant:
        raise HTTPException(status_code=403, detail="This workspace is available to Project Axiom participants.")
    return profile


def word_count(value: str) -> int:
    return len([part for part in value.strip().split() if part])


def normalized_identity(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def access_agreement_for(db: Session, account_id: str) -> AxiomProjectAccessAgreement | None:
    return db.query(AxiomProjectAccessAgreement).filter(
        AxiomProjectAccessAgreement.account_id == account_id,
        AxiomProjectAccessAgreement.agreement_version == ACCESS_AGREEMENT_VERSION,
    ).first()


def agreement_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hmac_seal(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def statement_data(statement: AxiomProblemStatement | None) -> dict | None:
    if not statement:
        return None
    return {
        "id": statement.id,
        "statement_slot": statement.statement_slot,
        "title": statement.title,
        "domain": statement.domain,
        "project_track": statement.project_track,
        "problem_statement": statement.problem_statement,
        "project_context": statement.project_context,
        "helpful_skills": statement.helpful_skills,
        "status": statement.status.value,
        "submitted_at": statement.submitted_at.isoformat() if statement.submitted_at else None,
    }


def deadlines_data() -> dict[str, str]:
    return {
        "team_finalization": TEAM_FINALIZATION_DEADLINE.isoformat(),
    }


def create_statement_for_author(
    *, db: Session, account: EventAccount, payload: StatementInput
) -> AxiomProblemStatement:
    if word_count(payload.problem_statement) > 44:
        raise HTTPException(status_code=400, detail="The problem statement must be 44 words or fewer.")
    if word_count(payload.project_context) > 88:
        raise HTTPException(status_code=400, detail="The project explanation must be 88 words or fewer.")
    if payload.client_request_id:
        existing = db.query(AxiomProblemStatement).filter(
            AxiomProblemStatement.mentor_account_id == account.id,
            AxiomProblemStatement.client_request_id == payload.client_request_id,
        ).first()
        if existing:
            return existing
    statement = AxiomProblemStatement(
        id=f"axps-{uuid.uuid4().hex[:18]}", mentor_account_id=account.id,
        client_request_id=payload.client_request_id,
    )
    db.add(statement)
    statement.title = payload.title.strip()
    statement.domain = payload.domain.strip()
    statement.project_track = payload.project_track
    statement.problem_statement = payload.problem_statement.strip()
    statement.project_context = payload.project_context.strip()
    statement.helpful_skills = payload.helpful_skills.strip()
    statement.status = AxiomStatementStatus.SUBMITTED
    statement.submitted_at = now_ist()
    try:
        db.commit()
    except IntegrityError:
        # The first identical retry may have committed while this request was
        # in flight. Return that project instead of surfacing a 500 or creating
        # a duplicate.
        db.rollback()
        if payload.client_request_id:
            existing = db.query(AxiomProblemStatement).filter(
                AxiomProblemStatement.mentor_account_id == account.id,
                AxiomProblemStatement.client_request_id == payload.client_request_id,
            ).first()
            if existing:
                return existing
        raise
    db.refresh(statement)
    return statement


@router.post("/password")
def change_own_password(
    payload: SelfPasswordChangeInput,
    account: EventAccount = Depends(current_account),
    db: Session = Depends(get_db),
):
    """Let an active Axiom account replace its initial credential safely."""
    if account.role != EventRole.SUPER_ADMIN:
        profile_for(db, account)
    if payload.new_password != payload.new_password_confirmation:
        raise HTTPException(status_code=400, detail="The two new password entries do not match.")
    if not verify_password(payload.current_password, account.password_hash):
        raise HTTPException(status_code=401, detail="Your current password is incorrect.")
    if verify_password(payload.new_password, account.password_hash):
        raise HTTPException(status_code=400, detail="Choose a new password that is different from your current password.")

    account.password_hash = get_password_hash(payload.new_password)
    db.query(EventPasswordVerifier).filter(
        EventPasswordVerifier.account_id == account.id
    ).delete(synchronize_session=False)
    profile = db.get(AxiomProfile, account.id)
    if profile:
        profile.must_change_password = False
    db.commit()
    return {
        "success": True,
        "data": {"login_id": account.login_id},
        "message": "Password changed. Use the new password for every future login.",
    }


@router.post("/agreement")
def accept_originality_agreement(
    payload: AgreementInput,
    request: Request,
    account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)),
    db: Session = Depends(get_db),
):
    participant_profile_for(db, account)
    profile = participant_profile_for(db, account)
    if not payload.accepted:
        raise HTTPException(status_code=400, detail="You must accept and sign the project-access acknowledgement to view project statements.")
    if normalized_identity(payload.college_email) != normalized_identity(profile.college_email):
        raise HTTPException(status_code=400, detail="Enter the same college email used for this account.")
    if normalized_identity(payload.full_name) != normalized_identity(profile.full_name):
        raise HTTPException(status_code=400, detail="Enter your full name exactly as shown on this Project Axiom account.")
    agreement = access_agreement_for(db, account.id)
    if not agreement:
        signed_at = now_ist()
        document_hash = agreement_hash(ACCESS_AGREEMENT_TEXT)
        signature_hash = agreement_hash(
            f"{profile.account_id}|{profile.college_email.lower()}|{profile.full_name}|{document_hash}|{signed_at.isoformat()}"
        )
        client_ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "unknown"))
        user_agent = request.headers.get("user-agent", "unknown")
        evidence_payload = {
            "account_id": account.id,
            "signed_email": profile.college_email.lower(),
            "signer_name": profile.full_name,
            "agreement_version": ACCESS_AGREEMENT_VERSION,
            "document_hash": document_hash,
            "signature_hash": signature_hash,
            "signed_at": signed_at.isoformat(),
            "ip_hash": hmac_seal({"ip": client_ip}),
            "user_agent_hash": hmac_seal({"user_agent": user_agent}),
        }
        agreement = AxiomProjectAccessAgreement(
            id=f"axag-{uuid.uuid4().hex[:18]}",
            account_id=account.id,
            signed_email=profile.college_email.lower(),
            signer_name=profile.full_name,
            agreement_version=ACCESS_AGREEMENT_VERSION,
            document_hash=document_hash,
            signature_hash=signature_hash,
            ip_hash=evidence_payload["ip_hash"],
            user_agent_hash=evidence_payload["user_agent_hash"],
            signed_at=signed_at,
            evidence_seal=hmac_seal(evidence_payload),
        )
        db.add(agreement)
    db.commit()
    return {
        "success": True,
        "data": {
            "accepted": True,
            "agreement_version": agreement.agreement_version,
            "document_hash": agreement.document_hash,
            "evidence_id": agreement.id,
            "signed_at": agreement.signed_at.isoformat(),
        },
        "message": "Project-access acknowledgement signed and securely recorded.",
    }


@router.get("/projects")
def participant_projects(
    account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)),
    db: Session = Depends(get_db),
):
    participant_profile_for(db, account)
    agreement = access_agreement_for(db, account.id)
    statements = []
    if agreement:
        submitted = db.query(AxiomProblemStatement, AxiomProfile.full_name).join(
            AxiomProfile, AxiomProfile.account_id == AxiomProblemStatement.mentor_account_id
        ).filter(
            AxiomProblemStatement.status == AxiomStatementStatus.SUBMITTED
        ).order_by(AxiomProblemStatement.title).all()
        for statement, publisher_name in submitted:
            statements.append({
                "id": statement.id,
                "publisher_name": publisher_name or "Project publisher",
                "is_publisher": statement.mentor_account_id == account.id,
                **(statement_data(statement) or {}),
            })
    applications = db.query(AxiomProjectApplication).filter(
        AxiomProjectApplication.participant_account_id == account.id
    ).all()
    return {
        "success": True,
        "data": {
            "agreement_accepted": bool(agreement),
            "selection_open": now_ist() <= TEAM_FINALIZATION_DEADLINE,
            "team_finalization_deadline": TEAM_FINALIZATION_DEADLINE.isoformat(),
            "projects": statements,
            "applications": [{
                "statement_id": item.statement_id,
                "proposed_solution": item.proposed_solution,
                "contribution": item.contribution,
            } for item in applications],
        },
        "message": "Open project workspace loaded.",
    }


@router.post("/projects")
def create_participant_project(
    payload: StatementInput,
    account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)),
    db: Session = Depends(get_db),
):
    participant_profile_for(db, account)
    if not access_agreement_for(db, account.id):
        raise HTTPException(status_code=403, detail="Sign the project-access acknowledgement before publishing a project.")
    statement = create_statement_for_author(db=db, account=account, payload=payload)
    return {"success": True, "data": statement_data(statement), "message": "Project published. You can now review applications to it."}


@router.put("/projects/{statement_id}/application")
def apply_to_project(
    statement_id: str,
    payload: ProjectApplicationInput,
    account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)),
    db: Session = Depends(get_db),
):
    participant_profile_for(db, account)
    if not access_agreement_for(db, account.id):
        raise HTTPException(status_code=403, detail="Sign the project-access acknowledgement before applying.")
    if word_count(payload.proposed_solution) + word_count(payload.contribution) > 88:
        raise HTTPException(status_code=400, detail="Your solution and contribution together must be 88 words or fewer.")
    statement = db.get(AxiomProblemStatement, statement_id)
    if not statement or statement.status != AxiomStatementStatus.SUBMITTED:
        raise HTTPException(status_code=404, detail="This project is not available.")
    if statement.mentor_account_id == account.id:
        raise HTTPException(status_code=400, detail="You already own this project and do not need to apply to it.")
    application = db.query(AxiomProjectApplication).filter(
        AxiomProjectApplication.participant_account_id == account.id,
        AxiomProjectApplication.statement_id == statement_id,
    ).first()
    if not application:
        application = AxiomProjectApplication(
            id=f"axapp-{uuid.uuid4().hex[:18]}", participant_account_id=account.id, statement_id=statement_id,
            proposed_solution=payload.proposed_solution.strip(), contribution=payload.contribution.strip(),
        )
        db.add(application)
    else:
        application.proposed_solution = payload.proposed_solution.strip()
        application.contribution = payload.contribution.strip()
    db.commit()
    return {"success": True, "data": {"statement_id": statement_id}, "message": "Your application has been recorded."}


@router.get("/me")
def me(account: EventAccount = Depends(current_account), db: Session = Depends(get_db)):
    if account.role == EventRole.SUPER_ADMIN:
        return {
            "success": True,
            "data": {
                "display_name": account.display_name,
                "is_super_admin": True,
                "deadlines": {
                    **deadlines_data(),
                },
            },
            "message": "Project Axiom control account loaded.",
        }

    profile = profile_for(db, account)
    statements = db.query(AxiomProblemStatement).filter(
        AxiomProblemStatement.mentor_account_id == account.id
    ).order_by(AxiomProblemStatement.statement_slot).all()
    return {
        "success": True,
        "data": {
            "display_name": profile.full_name,
            "college_email": profile.college_email,
            "roster_type": profile.roster_type.value,
            "role_choice": profile.role_choice.value,
            "must_change_password": profile.must_change_password,
            # `statement` is retained for older browsers during the rollout.
            "statement": statement_data(statements[0]) if statements else None,
            "statements": [statement_data(statement) for statement in statements],
            "deadlines": deadlines_data(),
        },
        "message": "Project Axiom profile loaded.",
    }


@router.get("/my-projects")
def my_projects(
    account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)),
    db: Session = Depends(get_db),
):
    participant_profile_for(db, account)
    if not access_agreement_for(db, account.id):
        raise HTTPException(status_code=403, detail="Sign the project-access acknowledgement before opening project applications.")
    projects = db.query(AxiomProblemStatement).filter(
        AxiomProblemStatement.mentor_account_id == account.id,
        AxiomProblemStatement.status == AxiomStatementStatus.SUBMITTED,
    ).order_by(AxiomProblemStatement.created_at.desc()).all()
    result = []
    for project in projects:
        applications = db.query(AxiomProjectApplication, AxiomProfile.full_name).join(
            AxiomProfile, AxiomProfile.account_id == AxiomProjectApplication.participant_account_id
        ).filter(AxiomProjectApplication.statement_id == project.id).order_by(
            AxiomProjectApplication.created_at
        ).all()
        selected_ids = {
            item.participant_account_id for item in db.query(AxiomProjectTeamSelection).filter(
                AxiomProjectTeamSelection.statement_id == project.id
            ).all()
        }
        result.append({
            **(statement_data(project) or {}),
            "applications": [{
                "account_id": application.participant_account_id,
                "name": name,
                "proposed_solution": application.proposed_solution,
                "contribution": application.contribution,
                "selected": application.participant_account_id in selected_ids,
            } for application, name in applications],
            "selection_open": now_ist() <= TEAM_FINALIZATION_DEADLINE,
        })
    return {"success": True, "data": {"projects": result, "team_finalization_deadline": TEAM_FINALIZATION_DEADLINE.isoformat()}, "message": "Your project applications loaded."}


@router.put("/projects/{statement_id}/selections")
def select_project_members(
    statement_id: str,
    payload: ProjectSelectionInput,
    account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)),
    db: Session = Depends(get_db),
):
    participant_profile_for(db, account)
    if now_ist() > TEAM_FINALIZATION_DEADLINE:
        raise HTTPException(status_code=409, detail="Team selections closed at 3:00 PM on 4 November 2026.")
    project = db.get(AxiomProblemStatement, statement_id)
    if not project or project.mentor_account_id != account.id:
        raise HTTPException(status_code=403, detail="Only the person who published this project can select its members.")
    selected_ids = list(dict.fromkeys(payload.participant_account_ids))
    if len(selected_ids) > 3:
        raise HTTPException(status_code=400, detail="Select at most three applicants. With you, the project team can have at most four people.")
    applicants = {
        item.participant_account_id for item in db.query(AxiomProjectApplication).filter(
            AxiomProjectApplication.statement_id == statement_id
        ).all()
    }
    if not set(selected_ids).issubset(applicants):
        raise HTTPException(status_code=400, detail="Members can only be selected from people who applied to this project.")
    db.query(AxiomProjectTeamSelection).filter(
        AxiomProjectTeamSelection.statement_id == statement_id
    ).delete(synchronize_session=False)
    for participant_account_id in selected_ids:
        db.add(AxiomProjectTeamSelection(
            id=f"axsel-{uuid.uuid4().hex[:18]}", statement_id=statement_id,
            participant_account_id=participant_account_id, selected_by_account_id=account.id,
        ))
    db.commit()
    return {"success": True, "data": {"selected": len(selected_ids), "team_size": len(selected_ids) + 1}, "message": "Project members selected."}


@router.get("/control/overview")
def control_overview(
    account: EventAccount = Depends(require_roles(EventRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
):
    profiles = db.query(AxiomProfile).filter(AxiomProfile.is_program_active.is_(True)).all()
    counts = {choice.value: 0 for choice in AxiomRoleChoice}
    for profile in profiles:
        counts[profile.role_choice.value] += 1
    statements = db.query(func.count(AxiomProblemStatement.id)).filter(
        AxiomProblemStatement.status == AxiomStatementStatus.SUBMITTED
    ).scalar() or 0
    preference_count = db.query(func.count(AxiomProjectApplication.id)).scalar() or 0
    submitted_projects = db.query(AxiomProblemStatement).filter(
        AxiomProblemStatement.status == AxiomStatementStatus.SUBMITTED
    ).order_by(AxiomProblemStatement.title).all()
    profiles_by_id = {profile.account_id: profile for profile in profiles}
    assignments: dict[str, list[dict]] = {item.id: [] for item in submitted_projects}
    selections = db.query(AxiomProjectTeamSelection).filter(
        AxiomProjectTeamSelection.statement_id.in_(assignments.keys()) if assignments else False
    ).all() if assignments else []
    for selection in selections:
        participant = profiles_by_id.get(selection.participant_account_id)
        if participant:
            assignments[selection.statement_id].append({"name": participant.full_name, "preference_rank": 0})
    people = [{
        "name": profile.full_name,
        "email": profile.college_email,
        "roster_type": profile.roster_type.value,
        "role_choice": profile.role_choice.value,
    } for profile in sorted(profiles, key=lambda item: item.full_name.lower())]
    return {
        "success": True,
        "data": {
            "total": len(profiles),
            "mentor_candidates": sum(p.roster_type == AxiomRosterType.MENTOR_CANDIDATE for p in profiles),
            "members": sum(p.roster_type == AxiomRosterType.MEMBER for p in profiles),
            "choices": counts,
            "submitted_statements": int(statements),
            "preference_count": int(preference_count),
            "matching_preview": [{
                "statement_id": project.id,
                "title": project.title,
                "track": project.project_track,
                "team_lead_name": db.get(AxiomProfile, project.mentor_account_id).full_name if db.get(AxiomProfile, project.mentor_account_id) else "Project publisher",
                "members": assignments.get(project.id, []),
            } for project in submitted_projects],
            "people": people,
        },
        "message": "Project Axiom overview loaded.",
    }
