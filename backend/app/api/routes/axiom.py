import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.routes.r1_event import current_account, require_roles
from app.db.session import get_db
from app.models.axiom import (
    AxiomProblemStatement,
    AxiomProfile,
    AxiomRoleChoice,
    AxiomRosterType,
    AxiomStatementStatus,
)
from app.models.event_account import EventAccount, EventRole


router = APIRouter(prefix="/axiom", tags=["Project Axiom"])
IST = ZoneInfo("Asia/Kolkata")
MENTOR_DECISION_DEADLINE = datetime(2026, 10, 27, 18, 0, tzinfo=IST)
STATEMENT_DEADLINE = datetime(2026, 11, 3, 18, 0, tzinfo=IST)
PREFERENCE_DEADLINE = datetime(2026, 11, 5, 18, 0, tzinfo=IST)


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


def now_ist() -> datetime:
    return datetime.now(IST)


def profile_for(db: Session, account: EventAccount) -> AxiomProfile:
    profile = db.get(AxiomProfile, account.id)
    if not profile or not profile.is_program_active:
        raise HTTPException(status_code=403, detail="This account is not part of the active Project Axiom roster.")
    return profile


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
        raise HTTPException(status_code=409, detail="The mentor decision window closed on 27 October at 6:00 PM IST.")
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
        raise HTTPException(status_code=409, detail="Problem-statement submissions closed on 3 November at 6:00 PM IST.")
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
            "people": people,
        },
        "message": "Project Axiom overview loaded.",
    }
