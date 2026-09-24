"""
Secret Agent Dossier & Mission Management API Endpoints for EVENT HQ.
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Endpoints:
- POST /secret-agents/{team_id}/assign
- GET  /secret-agents/{team_id}/dossier
- POST /secret-agents/{team_id}/tasks
- GET  /secret-agents/{team_id}/tasks
- POST /secret-agents/tasks/{task_id}/submit
- POST /secret-agents/tasks/{task_id}/verify
- POST /secret-agents/tasks/{task_id}/reject
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import require_role, get_current_user
from app.models.user import User, UserRole
from app.schemas.common import ApiResponse
from app.schemas.tournament_extensions import (
    SecretAgentDossierResponse,
    SecretAgentTaskResponse,
    SecretAgentAssignRequest,
    SecretAgentTaskCreate,
    SecretAgentTaskSubmitRequest,
    SecretAgentTaskVerifyRequest,
    SecretAgentTaskRejectRequest,
)
from app.services import secret_agent_service
from app.services.secret_agent_service import (
    SecretAgentError,
    AgentNotFoundError,
    AgentAssignmentError,
    AgentTaskError,
    AgentEvidenceError,
)

router = APIRouter(prefix="/secret-agents", tags=["Secret Agents Track"])


@router.post("/{team_id}/assign", response_model=ApiResponse[SecretAgentDossierResponse])
def assign_undercover_agent(
    team_id: str,
    payload: SecretAgentAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    """
    Assigns an undercover secret agent to a squad.
    CONFIDENTIAL: Restricted strictly to organizers and lead marshals.
    """
    try:
        dossier = secret_agent_service.assign_secret_agent(
            db=db,
            team_id=team_id,
            participant_id=payload.participant_id,
            codename=payload.codename,
            actor=current_user.email,
        )
        return ApiResponse(
            data=dossier,
            message="Secret agent assigned successfully"
        )
    except AgentAssignmentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{team_id}/dossier", response_model=ApiResponse[SecretAgentDossierResponse])
def get_dossier(
    team_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    """
    Retrieves the confidential Secret Agent dossier for a squad.
    CONFIDENTIAL: Restricted strictly to organizers and lead marshals.
    """
    dossier = secret_agent_service.get_secret_agent_dossier(db, team_id)
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No secret agent dossier found for team '{team_id}'"
        )
    return ApiResponse(
        data=dossier,
        message="Secret agent dossier retrieved"
    )


@router.post("/{team_id}/tasks", response_model=ApiResponse[SecretAgentTaskResponse])
def create_task(
    team_id: str,
    payload: SecretAgentTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    """
    Creates a new undercover mission for the squad's secret agent.
    """
    try:
        task = secret_agent_service.create_agent_task(
            db=db,
            team_id=team_id,
            task_description=payload.task_description,
            reward_points=payload.reward_points,
            actor=current_user.email,
        )
        return ApiResponse(
            data=task,
            message="Agent task created successfully"
        )
    except AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AgentTaskError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{team_id}/tasks", response_model=ApiResponse[List[SecretAgentTaskResponse]])
def list_tasks(
    team_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    """
    Retrieves all tasks for a squad's secret agent.
    CONFIDENTIAL: Restricted strictly to organizers and lead marshals.
    """
    tasks = secret_agent_service.get_team_agent_tasks(db, team_id)
    return ApiResponse(
        data=tasks,
        message=f"Retrieved {len(tasks)} agent tasks"
    )


@router.post("/tasks/{task_id}/submit", response_model=ApiResponse[SecretAgentTaskResponse])
def submit_task_evidence(
    task_id: str,
    payload: SecretAgentTaskSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submits evidence of task completion. Transitions task to SUBMITTED status.
    """
    try:
        task = secret_agent_service.submit_agent_task(
            db=db,
            task_id=task_id,
            evidence_reference=payload.evidence_reference,
            actor=current_user.email,
        )
        return ApiResponse(
            data=task,
            message="Agent task evidence submitted for organizer review"
        )
    except AgentEvidenceError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AgentTaskError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/tasks/{task_id}/verify", response_model=ApiResponse[SecretAgentTaskResponse])
def verify_task(
    task_id: str,
    payload: SecretAgentTaskVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    """
    Organizer reviews submitted evidence, approves completion, and awards +50 points to team wallet.
    """
    try:
        task = secret_agent_service.verify_agent_task(
            db=db,
            task_id=task_id,
            actor=current_user.email,
            notes=payload.notes,
        )
        return ApiResponse(
            data=task,
            message=f"Task verified successfully. Awarded +{task.reward_points:.1f} points to team wallet."
        )
    except AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AgentTaskError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/tasks/{task_id}/reject", response_model=ApiResponse[SecretAgentTaskResponse])
def reject_task(
    task_id: str,
    payload: SecretAgentTaskRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER, UserRole.MARSHAL])),
):
    """
    Organizer rejects task submission with mandatory audit justification.
    """
    try:
        task = secret_agent_service.reject_agent_task(
            db=db,
            task_id=task_id,
            rejection_reason=payload.rejection_reason,
            actor=current_user.email,
        )
        return ApiResponse(
            data=task,
            message="Task submission rejected"
        )
    except AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AgentTaskError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
