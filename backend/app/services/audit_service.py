from sqlalchemy.orm import Session
from typing import Optional, Any
from app.models.progression import AuditLog

def log_audit_event(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_id: str,
    actor_role: str,
    round_number: Optional[int] = None,
    details: Optional[Any] = None
) -> AuditLog:
    role_str = actor_role.value if hasattr(actor_role, "value") else str(actor_role)
    entry = AuditLog(
        action=action,
        round_number=round_number,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        actor_role=role_str,
        details=details
    )
    db.add(entry)
    # Does not commit immediately so it participates in outer transaction
    return entry
