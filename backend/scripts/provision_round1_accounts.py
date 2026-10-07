"""One-time, local-only creator for live Round 1 credentials.

Run this only after DATABASE_URL points to the event database. It prints each
credential once for the organizer to copy into sealed envelopes; passwords are
stored as bcrypt hashes and are never written into source control.
"""

import secrets
import string
import sys
from pathlib import Path

# Permit both `python scripts/provision_round1_accounts.py` and module execution.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.event_account import EventAccount, EventRole
from app.models.team import Team

ALPHANUMERIC = string.ascii_letters + string.digits


def new_password() -> str:
    # No punctuation, per event request; 12 mixed alphanumeric characters.
    return "".join(secrets.choice(ALPHANUMERIC) for _ in range(12))


def create_account(db, login_id: str, display_name: str, role: EventRole, password: str, team_id: str | None = None, location_number: int | None = None):
    db.add(EventAccount(
        login_id=login_id, display_name=display_name, password_hash=get_password_hash(password),
        role=role, team_id=team_id, location_number=location_number,
    ))
    return login_id, password


def main() -> int:
    db = SessionLocal()
    try:
        if db.query(EventAccount).count():
            print("Event accounts already exist. Refusing to replace live credentials.", file=sys.stderr)
            return 1
        credentials = []
        for index in range(1, 4):
            password = new_password()
            credentials.append(create_account(db, f"SUPER{index:02}", f"Super Admin {index}", EventRole.SUPER_ADMIN, password))
        for index in range(1, 9):
            password = new_password()
            credentials.append(create_account(db, f"ADMIN{index:02}", f"Location {index} Admin", EventRole.ADMIN, password, location_number=index))
        teams = db.query(Team).order_by(Team.team_number).all()
        if len(teams) != 32:
            raise RuntimeError(f"Expected 32 seeded teams, found {len(teams)}. Start the application once before provisioning accounts.")
        for team in teams:
            password = new_password()
            credentials.append(create_account(db, f"TEAM{1000 + team.team_number}", team.name, EventRole.PARTICIPANT, password, team_id=team.id))
        db.commit()
        print("Save these credentials in a secure organizer-only place. This is the only plaintext output.")
        for login_id, password in credentials:
            print(f"{login_id}\t{password}")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
