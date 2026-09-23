import os
import pytest

# Ensure isolated test environment configuration before any app imports
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "test_environment_secret_key_minimum_32_characters_length_ok"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.core import seed_default_teams
from app.core.security import get_password_hash, create_access_token
from app.services.dashboard_service import get_or_create_settings

# In-memory SQLite for high-speed isolated test execution
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    # Initialize settings and test users
    get_or_create_settings(session)
    
    organizer = User(
        email="test_organizer@bmsit.in",
        name="Test Organizer",
        hashed_password=get_password_hash("OrganizerSecret123"),
        role=UserRole.ORGANIZER,
        is_active=True,
    )
    marshal = User(
        email="test_marshal@bmsit.in",
        name="Test Marshal",
        hashed_password=get_password_hash("MarshalSecret123"),
        role=UserRole.MARSHAL,
        is_active=True,
    )
    judge = User(
        email="test_judge@bmsit.in",
        name="Test Judge",
        hashed_password=get_password_hash("JudgeSecret123"),
        role=UserRole.JUDGE,
        is_active=True,
    )
    projector = User(
        email="test_projector@bmsit.in",
        name="Public Projector",
        hashed_password=get_password_hash("ProjectorSecret123"),
        role=UserRole.PUBLIC_PROJECTOR,
        is_active=True,
    )
    session.add_all([organizer, marshal, judge, projector])
    session.commit()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def auto_seed_round_teams_if_needed(request, db_session: Session):
    """Automatically seeds the 32 standard squads for round test files."""
    node_id = getattr(request.node, "nodeid", "")
    if "tests/rounds" in node_id.replace("\\", "/"):
        seed_default_teams(db_session)


@pytest.fixture
def organizer_token(db_session: Session) -> str:
    user = db_session.query(User).filter(User.role == UserRole.ORGANIZER).first()
    return create_access_token(subject=user.id, role=user.role.value)


@pytest.fixture
def marshal_token(db_session: Session) -> str:
    user = db_session.query(User).filter(User.role == UserRole.MARSHAL).first()
    return create_access_token(subject=user.id, role=user.role.value)


@pytest.fixture
def judge_token(db_session: Session) -> str:
    user = db_session.query(User).filter(User.role == UserRole.JUDGE).first()
    return create_access_token(subject=user.id, role=user.role.value)


@pytest.fixture
def projector_token(db_session: Session) -> str:
    user = db_session.query(User).filter(User.role == UserRole.PUBLIC_PROJECTOR).first()
    return create_access_token(subject=user.id, role=user.role.value)


@pytest.fixture
def organizer_headers(organizer_token: str) -> dict:
    return {"Authorization": f"Bearer {organizer_token}"}


@pytest.fixture
def marshal_headers(marshal_token: str) -> dict:
    return {"Authorization": f"Bearer {marshal_token}"}


@pytest.fixture
def judge_headers(judge_token: str) -> dict:
    return {"Authorization": f"Bearer {judge_token}"}


@pytest.fixture
def projector_headers(projector_token: str) -> dict:
    return {"Authorization": f"Bearer {projector_token}"}