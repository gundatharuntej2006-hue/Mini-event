"""
Secret Agent Dossier, Task Workflow & Reward Service for EVENT HQ.
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B & Step 7).

Manages:
- Undercover agent assignment per squad (exactly one active agent per team)
- Confidential agent dossier lifecycle
- Safe, non-disruptive task creation, submission with evidence, and organizer verification
- +50 points wallet reward upon organizer verification (idempotent, no double-bounties)
- Organizer rejection with mandatory audit reason
- Confidentiality protection (identities shielded from public endpoints)
"""

from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.agent import (
    SecretAgentDossier,
    SecretAgentTask,
    AgentDossierStatus,
    AgentTaskStatus,
)
from app.models.team import Team
from app.models.participant import Participant
from app.core.constants import AGENT_TASK_REWARD
from app.services.wallet import award_agent_task_reward
from app.services.audit_service import log_audit_event


# ==============================================================================
# DOMAIN EXCEPTIONS
# ==============================================================================
class SecretAgentError(Exception):
    """Base domain exception for Secret Agent operations."""
    pass


class AgentNotFoundError(SecretAgentError):
    """Raised when a dossier, task, participant, or team is not found."""
    pass


class AgentAssignmentError(SecretAgentError):
    """Raised when undercover agent assignment violates squad isolation or uniqueness."""
    pass


class AgentTaskError(SecretAgentError):
    """Raised when an agent task state transition is invalid."""
    pass


class AgentEvidenceError(SecretAgentError):
    """Raised when task submission is missing mandatory evidence."""
    pass


# ==============================================================================
# AGENT DOSSIER ASSIGNMENT
# ==============================================================================
def assign_secret_agent(
    db: Session,
    team_id: str,
    participant_id: str,
    codename: Optional[str] = None,
    actor: Optional[str] = None,
) -> SecretAgentDossier:
    """
    Assigns an undercover secret agent to a team.
    Rules:
    - Participant must belong to the specified team.
    - Exactly one active secret agent per team.
    - Same participant cannot be assigned to multiple active dossiers.
    - Status set to ACTIVE.
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise AgentNotFoundError(f"Team '{team_id}' not found.")

    participant = db.query(Participant).filter(Participant.id == participant_id).first()
    if not participant:
        raise AgentNotFoundError(f"Participant '{participant_id}' not found.")

    if participant.team_id != team_id:
        raise AgentAssignmentError(
            f"Participant '{participant.name}' (ID: {participant_id}) does not belong to team '{team_id}'."
        )

    # Check for existing active agent in this team
    existing_team_dossier = (
        db.query(SecretAgentDossier)
        .filter(
            SecretAgentDossier.team_id == team_id,
            SecretAgentDossier.status == AgentDossierStatus.ACTIVE,
        )
        .first()
    )
    if existing_team_dossier:
        raise AgentAssignmentError(
            f"Team '{team_id}' already has an active Secret Agent dossier ({existing_team_dossier.id})."
        )

    # Check for participant assigned as active agent in any squad
    existing_participant_dossier = (
        db.query(SecretAgentDossier)
        .filter(
            SecretAgentDossier.participant_id == participant_id,
            SecretAgentDossier.status == AgentDossierStatus.ACTIVE,
        )
        .first()
    )
    if existing_participant_dossier:
        raise AgentAssignmentError(
            f"Participant '{participant_id}' is already assigned as an active Secret Agent in another squad."
        )

    dossier = SecretAgentDossier(
        team_id=team_id,
        participant_id=participant_id,
        codename=codename.strip() if codename else None,
        status=AgentDossierStatus.ACTIVE,
        assigned_at=datetime.now(timezone.utc),
    )
    db.add(dossier)
    db.flush()

    log_audit_event(
        db=db,
        action="SECRET_AGENT_ASSIGNED",
        entity_type="SecretAgentDossier",
        entity_id=dossier.id,
        actor_id=actor or "system",
        actor_role="ORGANIZER",
        round_number=3,
        details={"team_id": team_id, "dossier_id": dossier.id}
    )

    db.commit()
    db.refresh(dossier)
    return dossier


def get_secret_agent_dossier(db: Session, team_id: str) -> Optional[SecretAgentDossier]:
    """Retrieves the SecretAgentDossier for a team (Organizer / Lead Marshal access only)."""
    return db.query(SecretAgentDossier).filter(SecretAgentDossier.team_id == team_id).first()


# ==============================================================================
# AGENT TASK LIFECYCLE
# ==============================================================================
def create_agent_task(
    db: Session,
    team_id: str,
    task_description: str,
    reward_points: float = AGENT_TASK_REWARD,
    actor: Optional[str] = None,
) -> SecretAgentTask:
    """
    Creates a new undercover task/mission for the squad's secret agent.
    Task starts in ASSIGNED status.
    """
    if not task_description or not task_description.strip():
        raise AgentTaskError("Task description cannot be empty.")

    dossier = (
        db.query(SecretAgentDossier)
        .filter(
            SecretAgentDossier.team_id == team_id,
            SecretAgentDossier.status == AgentDossierStatus.ACTIVE,
        )
        .first()
    )
    if not dossier:
        raise AgentNotFoundError(f"Team '{team_id}' does not have an active Secret Agent dossier.")

    task = SecretAgentTask(
        dossier_id=dossier.id,
        task_description=task_description.strip(),
        reward_points=float(reward_points),
        status=AgentTaskStatus.ASSIGNED,
        assigned_at=datetime.now(timezone.utc),
    )
    db.add(task)
    db.flush()

    log_audit_event(
        db=db,
        action="AGENT_TASK_CREATED",
        entity_type="SecretAgentTask",
        entity_id=task.id,
        actor_id=actor or "system",
        actor_role="ORGANIZER",
        round_number=3,
        details={"team_id": team_id, "task_id": task.id}
    )

    db.commit()
    db.refresh(task)
    return task


def submit_agent_task(
    db: Session,
    task_id: str,
    evidence_reference: str,
    actor: Optional[str] = None,
) -> SecretAgentTask:
    """
    Submits proof/evidence of task completion.
    Transitions task from ASSIGNED -> SUBMITTED.
    Requires non-empty evidence_reference (text, image URL, or organizer reference).
    """
    if not evidence_reference or not evidence_reference.strip():
        raise AgentEvidenceError("Task submission requires non-empty evidence_reference.")

    task = db.query(SecretAgentTask).filter(SecretAgentTask.id == task_id).first()
    if not task:
        raise AgentNotFoundError(f"Secret Agent task '{task_id}' not found.")

    if task.status != AgentTaskStatus.ASSIGNED:
        raise AgentTaskError(
            f"Cannot submit task in '{task.status.value}' status. Must be in 'ASSIGNED' status."
        )

    now = datetime.now(timezone.utc)
    task.evidence_reference = evidence_reference.strip()
    task.status = AgentTaskStatus.SUBMITTED
    task.submitted_at = now
    task.updated_at = now

    log_audit_event(
        db=db,
        action="AGENT_TASK_SUBMITTED",
        entity_type="SecretAgentTask",
        entity_id=task.id,
        actor_id=actor or "agent",
        actor_role="PARTICIPANT",
        round_number=3,
        details={"task_id": task.id}
    )

    db.commit()
    db.refresh(task)
    return task


def verify_agent_task(
    db: Session,
    task_id: str,
    actor: str,
    notes: Optional[str] = None,
) -> SecretAgentTask:
    """
    Organizer reviews submitted evidence and approves completion.
    Transitions task from SUBMITTED -> VERIFIED.
    Awards canonical AGENT_TASK_REWARD (+50 points) to the team's tournament wallet.
    Idempotent: Repeated calls return existing verified task without awarding double points.
    """
    task = db.query(SecretAgentTask).filter(SecretAgentTask.id == task_id).first()
    if not task:
        raise AgentNotFoundError(f"Secret Agent task '{task_id}' not found.")

    # Idempotency check: if already verified, return safely
    if task.status == AgentTaskStatus.VERIFIED:
        return task

    if task.status != AgentTaskStatus.SUBMITTED:
        raise AgentTaskError(
            f"Cannot verify task in '{task.status.value}' status. Must be in 'SUBMITTED' status."
        )

    now = datetime.now(timezone.utc)
    task.status = AgentTaskStatus.VERIFIED
    task.verified_at = now
    task.organizer_id = actor
    task.updated_at = now

    # Award points to team wallet via safe WalletService
    team_id = task.dossier.team_id
    award_agent_task_reward(
        db=db,
        team_id=team_id,
        task_id=task.id,
        reward_amount=task.reward_points,
        description=f"Secret Agent Mission Verified (+{task.reward_points:.1f} pts)",
        created_by=actor,
    )

    log_audit_event(
        db=db,
        action="AGENT_TASK_VERIFIED",
        entity_type="SecretAgentTask",
        entity_id=task.id,
        actor_id=actor,
        actor_role="ORGANIZER",
        round_number=3,
        details={"task_id": task.id, "team_id": team_id, "reward_points": task.reward_points}
    )

    db.commit()
    db.refresh(task)
    return task


def reject_agent_task(
    db: Session,
    task_id: str,
    rejection_reason: str,
    actor: str,
) -> SecretAgentTask:
    """
    Organizer rejects task submission with mandatory audit justification.
    Transitions task from SUBMITTED -> REJECTED.
    No points are awarded.
    """
    if not rejection_reason or not rejection_reason.strip():
        raise AgentTaskError("Rejection reason is mandatory and cannot be empty.")

    task = db.query(SecretAgentTask).filter(SecretAgentTask.id == task_id).first()
    if not task:
        raise AgentNotFoundError(f"Secret Agent task '{task_id}' not found.")

    if task.status != AgentTaskStatus.SUBMITTED:
        raise AgentTaskError(
            f"Cannot reject task in '{task.status.value}' status. Must be in 'SUBMITTED' status."
        )

    now = datetime.now(timezone.utc)
    task.status = AgentTaskStatus.REJECTED
    task.rejection_reason = rejection_reason.strip()
    task.organizer_id = actor
    task.updated_at = now

    log_audit_event(
        db=db,
        action="AGENT_TASK_REJECTED",
        entity_type="SecretAgentTask",
        entity_id=task.id,
        actor_id=actor,
        actor_role="ORGANIZER",
        round_number=3,
        details={"task_id": task.id, "reason": rejection_reason.strip()}
    )

    db.commit()
    db.refresh(task)
    return task


def get_team_agent_tasks(db: Session, team_id: str) -> List[SecretAgentTask]:
    """Retrieves all tasks for a team's Secret Agent dossier."""
    dossier = db.query(SecretAgentDossier).filter(SecretAgentDossier.team_id == team_id).first()
    if not dossier:
        return []
    return dossier.tasks
