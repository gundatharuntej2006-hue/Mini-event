import secrets
from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import verify_password, get_password_hash
from app.models.user import User, UserRole
from app.schemas.user import UserCreate


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email.lower().strip()).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def create_user(db: Session, user_in: UserCreate) -> User:
    hashed = get_password_hash(user_in.password)
    user = User(
        email=user_in.email.lower().strip(),
        name=user_in.name.strip(),
        hashed_password=hashed,
        role=user_in.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_default_organizer(db: Session) -> Optional[User]:
    """Idempotently seed the initial organizer if configured in environment."""
    if not settings.INITIAL_ORGANIZER_EMAIL or not settings.INITIAL_ORGANIZER_PASSWORD:
        return None

    existing = get_user_by_email(db, settings.INITIAL_ORGANIZER_EMAIL)
    if existing:
        return existing
    
    organizer = User(
        email=settings.INITIAL_ORGANIZER_EMAIL.lower().strip(),
        name=settings.INITIAL_ORGANIZER_NAME.strip(),
        hashed_password=get_password_hash(settings.INITIAL_ORGANIZER_PASSWORD),
        role=UserRole.ORGANIZER,
        is_active=True,
    )
    db.add(organizer)
    db.commit()
    db.refresh(organizer)
    return organizer