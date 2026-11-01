import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.routes.r1_event import current_account, require_roles
from app.core.security import get_password_hash, verify_password
from app.db.session import get_db
from app.models.axiom import (
    AxiomOriginalityAgreement,
    AxiomProblemStatement,
    AxiomProfile,
    AxiomProjectPreference,
    AxiomRoleChoice,
    AxiomRosterType,
    AxiomStatementStatus,
)
from app.models.event_account import EventAccount, EventPasswordVerifier, EventRole


router = APIRouter(prefix="/axiom", tags=["Project Axiom"])
IST = ZoneInfo("Asia/Kolkata")
MENTOR_DECISION_DEADLINE = datetime(2026, 11, 2, 12, 0, tzinfo=IST)
STATEMENT_DEADLINE = datetime(2026, 11, 3, 15, 0, tzinfo=IST)
PREFERENCE_DEADLINE = datetime(2026, 11, 3, 18, 0, tzinfo=IST)


class RoleChoiceInput(BaseModel):
    choice: Literal["MENTOR", "PARTICIPANT", "OPTED_OUT"]
    confirmed: bool


class StatementInput(BaseModel):
    title: str = Field(min_length=4, max_length=140)
    domain: str = Field(min_length=2, max_length=100)
    project_track: Literal["RESEARCH", "PRODUCT"]
    problem_statement: str = Field(min_length=20, max_length=1200)
    project_context: str = Field(min_length=20, max_length=2400)
    helpful_skills: str = Field(default="", max_length=600)
    submit: bool = False


class SelfPasswordChangeInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=72)
    new_password_confirmation: str = Field(min_length=8, max_length=72)


class AgreementInput(BaseModel):
    accepted: bool


class PreferenceItemInput(BaseModel):
    statement_id: str = Field(min_length=3, max_length=40)
    preference_rank: int = Field(ge=1, le=3)
    proposed_solution: str = Field(min_length=20, max_length=1400)
    contribution: str = Field(min_length=10, max_length=900)


class PreferencesInput(BaseModel):
    preferences: list[PreferenceItemInput] = Field(min_length=1, max_length=3)


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


def statement_data(statement: AxiomProblemStatement | None) -> dict | None:
    if not statement:
        return None
    return {
        "title": statement.title,
        "domain": statement.domain,
        "project_track": statement.project_track,
        "problem_statement": statement.problem_statement,
        "project_context": statement.project_context,
        "helpful_skills": statement.helpful_skills,
        "status": statement.status.value,
        "submitted_at": statement.submitted_at.isoformat() if statement.submitted_at else None,
    }


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
    account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)),
    db: Session = Depends(get_db),
):
    participant_profile_for(db, account)
    if not payload.accepted:
        raise HTTPException(status_code=400, detail="You must accept the originality agreement to view project statements.")
    agreement = db.get(AxiomOriginalityAgreement, account.id)
    if not agreement:
        agreement = AxiomOriginalityAgreement(account_id=account.id, agreement_version="axiom-v1")
        db.add(agreement)
    db.commit()
    return {"success": True, "data": {"accepted": True}, "message": "Originality agreement accepted."}


@router.get("/projects")
def participant_projects(
    account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)),
    db: Session = Depends(get_db),
):
    participant_profile_for(db, account)
    agreement = db.get(AxiomOriginalityAgreement, account.id)
    window_open = now_ist() >= STATEMENT_DEADLINE
    statements = []
    if agreement and window_open:
        submitted = db.query(AxiomProblemStatement).filter(
            AxiomProblemStatement.status == AxiomStatementStatus.SUBMITTED
        ).order_by(AxiomProblemStatement.title).all()
        for statement in submitted:
            mentor = db.get(AxiomProfile, statement.mentor_account_id)
            statements.append({
                "id": statement.id,
                "mentor_name": mentor.full_name if mentor else "Project mentor",
                **(statement_data(statement) or {}),
            })
    preferences = db.query(AxiomProjectPreference).filter(
        AxiomProjectPreference.participant_account_id == account.id
    ).order_by(AxiomProjectPreference.preference_rank).all()
    return {
        "success": True,
        "data": {
            "agreement_accepted": bool(agreement),
            "window_open": window_open,
            "window_closed": now_ist() > PREFERENCE_DEADLINE,
            "projects": statements,
            "preferences": [{
                "statement_id": item.statement_id,
                "preference_rank": item.preference_rank,
                "proposed_solution": item.proposed_solution,
                "contribution": item.contribution,
            } for item in preferences],
        },
        "message": "Project selection workspace loaded.",
    }


@router.put("/preferences")
def save_participant_preferences(
    payload: PreferencesInput,
    account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)),
    db: Session = Depends(get_db),
):
    participant_profile_for(db, account)
    if not db.get(AxiomOriginalityAgreement, account.id):
        raise HTTPException(status_code=403, detail="Accept the originality agreement before submitting preferences.")
    if now_ist() < STATEMENT_DEADLINE:
        raise HTTPException(status_code=409, detail="Project preferences open on 3 November at 3:00 PM IST.")
    if now_ist() > PREFERENCE_DEADLINE:
        raise HTTPException(status_code=409, detail="Project preferences closed on 3 November at 6:00 PM IST.")

    statement_ids = [item.statement_id for item in payload.preferences]
    ranks = [item.preference_rank for item in payload.preferences]
    if len(set(statement_ids)) != len(statement_ids) or len(set(ranks)) != len(ranks):
        raise HTTPException(status_code=400, detail="Choose different projects and use each preference rank only once.")
    if sorted(ranks) != list(range(1, len(ranks) + 1)):
        raise HTTPException(status_code=400, detail="Preference ranks must start at 1 without gaps.")
    for item in payload.preferences:
        if word_count(item.proposed_solution) + word_count(item.contribution) > 88:
            raise HTTPException(status_code=400, detail="Each project response must be 88 words or fewer in total.")
        statement = db.get(AxiomProblemStatement, item.statement_id)
        if not statement or statement.status != AxiomStatementStatus.SUBMITTED:
            raise HTTPException(status_code=404, detail="One selected project is not available.")

    db.query(AxiomProjectPreference).filter(
        AxiomProjectPreference.participant_account_id == account.id
    ).delete(synchronize_session=False)
    for item in payload.preferences:
        db.add(AxiomProjectPreference(
            id=f"axpref-{uuid.uuid4().hex[:16]}",
            participant_account_id=account.id,
            statement_id=item.statement_id,
            preference_rank=item.preference_rank,
            proposed_solution=item.proposed_solution.strip(),
            contribution=item.contribution.strip(),
        ))
    db.commit()
    return {
        "success": True,
        "data": {"saved": len(payload.preferences)},
        "message": "Your ranked project preferences have been saved.",
    }


@router.get("/me")
def me(account: EventAccount = Depends(current_account), db: Session = Depends(get_db)):
    if account.role == EventRole.SUPER_ADMIN:
        return {
            "success": True,
            "data": {
                "display_name": account.display_name,
                "is_super_admin": True,
                "deadlines": {
                    "mentor_decision": MENTOR_DECISION_DEADLINE.isoformat(),
                    "statement": STATEMENT_DEADLINE.isoformat(),
                    "preference": PREFERENCE_DEADLINE.isoformat(),
                },
            },
            "message": "Project Axiom control account loaded.",
        }

    profile = profile_for(db, account)
    statement = db.query(AxiomProblemStatement).filter(
        AxiomProblemStatement.mentor_account_id == account.id
    ).first()
    return {
        "success": True,
        "data": {
            "display_name": profile.full_name,
            "college_email": profile.college_email,
            "roster_type": profile.roster_type.value,
            "role_choice": profile.role_choice.value,
            "must_change_password": profile.must_change_password,
            "statement": statement_data(statement),
            "deadlines": {
                "mentor_decision": MENTOR_DECISION_DEADLINE.isoformat(),
                "statement": STATEMENT_DEADLINE.isoformat(),
                "preference": PREFERENCE_DEADLINE.isoformat(),
            },
        },
        "message": "Project Axiom profile loaded.",
    }


@router.post("/role-choice")
def choose_role(
    payload: RoleChoiceInput,
    account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)),
    db: Session = Depends(get_db),
):
    profile = profile_for(db, account)
    if profile.roster_type != AxiomRosterType.MENTOR_CANDIDATE:
        raise HTTPException(status_code=403, detail="Only mentor candidates make this decision.")
    if now_ist() > MENTOR_DECISION_DEADLINE:
        raise HTTPException(status_code=409, detail="The mentor decision window closed on 2 November at 12:00 PM IST.")
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Please confirm your final selection.")
    profile.role_choice = AxiomRoleChoice(payload.choice)
    db.commit()
    return {"success": True, "data": {"role_choice": profile.role_choice.value}, "message": "Your Project Axiom decision has been saved."}


@router.put("/mentor/statement")
def save_statement(
    payload: StatementInput,
    account: EventAccount = Depends(require_roles(EventRole.PARTICIPANT)),
    db: Session = Depends(get_db),
):
    profile = profile_for(db, account)
    if profile.role_choice != AxiomRoleChoice.MENTOR:
        raise HTTPException(status_code=403, detail="Choose the mentor role before creating a problem statement.")
    if now_ist() > STATEMENT_DEADLINE:
        raise HTTPException(status_code=409, detail="Problem-statement submissions closed on 3 November at 3:00 PM IST.")
    if word_count(payload.problem_statement) > 44:
        raise HTTPException(status_code=400, detail="The problem statement must be 44 words or fewer.")
    if word_count(payload.project_context) > 88:
        raise HTTPException(status_code=400, detail="The project explanation must be 88 words or fewer.")
    statement = db.query(AxiomProblemStatement).filter(
        AxiomProblemStatement.mentor_account_id == account.id
    ).first()
    if not statement:
        statement = AxiomProblemStatement(
            id=f"axps-{uuid.uuid4().hex[:18]}", mentor_account_id=account.id
        )
        db.add(statement)
    statement.title = payload.title.strip()
    statement.domain = payload.domain.strip()
    statement.project_track = payload.project_track
    statement.problem_statement = payload.problem_statement.strip()
    statement.project_context = payload.project_context.strip()
    statement.helpful_skills = payload.helpful_skills.strip()
    statement.status = AxiomStatementStatus.SUBMITTED if payload.submit else AxiomStatementStatus.DRAFT
    statement.submitted_at = now_ist() if payload.submit else None
    db.commit()
    db.refresh(statement)
    return {"success": True, "data": statement_data(statement), "message": "Problem statement submitted." if payload.submit else "Draft saved."}


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
    preference_count = db.query(func.count(AxiomProjectPreference.id)).scalar() or 0
    submitted_projects = db.query(AxiomProblemStatement).filter(
        AxiomProblemStatement.status == AxiomStatementStatus.SUBMITTED
    ).order_by(AxiomProblemStatement.title).all()
    assignments: dict[str, list[dict]] = {item.id: [] for item in submitted_projects}
    assigned_accounts: set[str] = set()
    preference_rows = db.query(AxiomProjectPreference).order_by(
        AxiomProjectPreference.preference_rank,
        AxiomProjectPreference.created_at,
    ).all()
    # Preference-fit preview only: honour first choices first, cap normal teams
    # at three, then allow one four-person team if the roster requires it.
    for preference in preference_rows:
        if preference.participant_account_id in assigned_accounts:
            continue
        if preference.statement_id not in assignments or len(assignments[preference.statement_id]) >= 3:
            continue
        participant = db.get(AxiomProfile, preference.participant_account_id)
        if not participant:
            continue
        assignments[preference.statement_id].append({
            "name": participant.full_name,
            "preference_rank": preference.preference_rank,
        })
        assigned_accounts.add(preference.participant_account_id)
    unassigned_ids = []
    for preference in preference_rows:
        if preference.participant_account_id not in assigned_accounts and preference.participant_account_id not in unassigned_ids:
            unassigned_ids.append(preference.participant_account_id)
    overflow_used = False
    for participant_id in unassigned_ids:
        options = [row for row in preference_rows if row.participant_account_id == participant_id]
        available = [row for row in options if row.statement_id in assignments and len(assignments[row.statement_id]) < (4 if not overflow_used else 3)]
        if not available:
            continue
        selected = min(available, key=lambda row: (len(assignments[row.statement_id]), row.preference_rank))
        participant = db.get(AxiomProfile, participant_id)
        if participant:
            assignments[selected.statement_id].append({"name": participant.full_name, "preference_rank": selected.preference_rank})
            assigned_accounts.add(participant_id)
            if len(assignments[selected.statement_id]) == 4:
                overflow_used = True
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
                "members": assignments.get(project.id, []),
            } for project in submitted_projects],
            "people": people,
        },
        "message": "Project Axiom overview loaded.",
    }
