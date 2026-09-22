import os
import sys
import getpass
import argparse
from pathlib import Path

# Ensure CLI execution mode flag is active before importing config/session
os.environ["IS_CLI"] = "1"

# Ensure backend root is in sys.path regardless of execution CWD
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.user import User, UserRole
from app.models.team import Team, TeamStatus
from app.models.participant import Participant, ParticipantRole
from app.models.event_settings import EventSettings
from app.core.security import get_password_hash
from app.services.auth_service import ensure_default_organizer
from app.services.dashboard_service import get_or_create_settings


def get_secure_password(provided_password: str | None, prompt: str = "Enter password: ") -> str:
    """Safely obtain password interactively with confirmation if not passed via CLI argument."""
    if provided_password and provided_password.strip():
        pwd = provided_password.strip()
    else:
        pwd = getpass.getpass(prompt)
        confirm = getpass.getpass("Confirm password: ")
        if pwd != confirm:
            print("Error: Passwords do not match.")
            sys.exit(1)

    if len(pwd) < 6:
        print("Error: Password must contain at least 6 characters.")
        sys.exit(1)
    return pwd


def init_db():
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        organizer = ensure_default_organizer(db)
        get_or_create_settings(db)
        if organizer:
            print(f"Database initialized. Default organizer seeded: {organizer.email}")
        else:
            print("Database initialized.")


def create_user_cmd(email: str, password: str | None, name: str, role_str: str):
    try:
        role = UserRole(role_str.upper())
    except ValueError:
        print(f"Error: Invalid role '{role_str}'. Allowed: {[r.value for r in UserRole]}")
        sys.exit(1)

    clean_email = email.lower().strip()
    with SessionLocal() as db:
        existing = db.query(User).filter(User.email == clean_email).first()
        if existing:
            print(f"User '{clean_email}' already exists.")
            return

        final_password = get_secure_password(password, prompt=f"Enter password for {clean_email}: ")
        user = User(
            email=clean_email,
            name=name.strip(),
            hashed_password=get_password_hash(final_password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"User created successfully: {user.email} (Role: {user.role.value}, ID: {user.id})")


def reset_password_cmd(email: str, password: str | None):
    clean_email = email.lower().strip()
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == clean_email).first()
        if not user:
            print(f"Error: User with email '{clean_email}' not found.")
            sys.exit(1)

        final_password = get_secure_password(password, prompt=f"Enter new password for {clean_email}: ")
        user.hashed_password = get_password_hash(final_password)
        db.commit()
        print(f"Password reset successfully for {user.email} (Role: {user.role.value}, ID: {user.id})")


def seed_demo_data():
    print("Seeding initial teams and participants...")
    with SessionLocal() as db:
        Base.metadata.create_all(bind=engine)
        ensure_default_organizer(db)
        get_or_create_settings(db)
        
        # Create 4 demo teams if empty
        if db.query(Team).count() == 0:
            for i in range(1, 5):
                team = Team(
                    team_number=i,
                    name=f"Vanguard Unit {i:02d}",
                    assigned_table=f"Table {i}",
                    status=TeamStatus.REGISTERED,
                    current_round=1,
                )
                db.add(team)
                db.flush()
                
                # Add 5 participants per team
                for p_idx in range(1, 6):
                    part = Participant(
                        name=f"Cadet {i:02d}-{p_idx}",
                        email=f"cadet.{i}.{p_idx}@bmsit.in",
                        usn=f"1BY22CS{i:02d}{p_idx:02d}",
                        phone=f"+91 98765 {i:02d}{p_idx:02d}0",
                        role=ParticipantRole.LEADER if p_idx == 1 else ParticipantRole.MEMBER,
                        checked_in=(p_idx <= 3), # partial checkin
                        team_id=team.id,
                    )
                    db.add(part)
            db.commit()
            print("Successfully seeded 4 demo teams with 20 participants.")
        else:
            print("Database already has teams. Skipping demo seed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EVENT HQ Administrative CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init-db
    subparsers.add_parser("init-db", help="Initialize tables and seed default organizer")

    # create-user
    user_parser = subparsers.add_parser("create-user", help="Create a tournament official account")
    user_parser.add_argument("--email", required=True, help="User email")
    user_parser.add_argument("--password", required=False, default=None, help="User password (prompted securely if omitted)")
    user_parser.add_argument("--name", required=True, help="Full name")
    user_parser.add_argument("--role", default="MARSHAL", help="ORGANIZER, MARSHAL, JUDGE, PUBLIC_PROJECTOR")

    # reset-password
    reset_parser = subparsers.add_parser("reset-password", help="Reset password for an existing tournament official")
    reset_parser.add_argument("--email", required=True, help="User email")
    reset_parser.add_argument("--password", required=False, default=None, help="New password (prompted securely if omitted)")

    # seed-demo
    subparsers.add_parser("seed-demo", help="Seed 4 demo teams with full 5-person squads")

    args = parser.parse_args()

    if args.command == "init-db":
        init_db()
    elif args.command == "create-user":
        create_user_cmd(args.email, args.password, args.name, args.role)
    elif args.command == "reset-password":
        reset_password_cmd(args.email, args.password)
    elif args.command == "seed-demo":
        seed_demo_data()
    else:
        parser.print_help()
