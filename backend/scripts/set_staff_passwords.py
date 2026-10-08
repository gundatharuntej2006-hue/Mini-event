"""One-time interactive updater for live super-admin and admin passwords.

Run only from the Render backend Shell. Passwords are read without echoing,
hashed with bcrypt, and never written to source control or command history.
"""

import sys
from getpass import getpass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.event_account import EventAccount, EventRole


def prompt_twice(label: str) -> str:
    first = getpass(f"{label}: ")
    second = getpass(f"Confirm {label.lower()}: ")
    if first != second:
        raise ValueError("The password entries did not match.")
    if len(first) < 8:
        raise ValueError("Passwords must contain at least 8 characters.")
    return first


def main() -> int:
    db = SessionLocal()
    try:
        super_password = prompt_twice("New shared password for SUPER01, SUPER02, and SUPER03")
        admin_passwords = {f"ADMIN{number:02}": prompt_twice(f"New password for ADMIN{number:02}") for number in range(1, 9)}
        supers = db.query(EventAccount).filter(EventAccount.role == EventRole.SUPER_ADMIN).order_by(EventAccount.login_id).all()
        if [account.login_id for account in supers] != ["SUPER01", "SUPER02", "SUPER03"]:
            raise RuntimeError("Expected exactly SUPER01, SUPER02, and SUPER03. No changes were made.")
        admins = {account.login_id: account for account in db.query(EventAccount).filter(EventAccount.role == EventRole.ADMIN).all()}
        if set(admin_passwords) != set(admins):
            raise RuntimeError("Expected exactly ADMIN01 through ADMIN08. No changes were made.")
        for account in supers:
            account.password_hash = get_password_hash(super_password)
        for login_id, password in admin_passwords.items():
            admins[login_id].password_hash = get_password_hash(password)
        db.commit()
        print("Updated passwords for 3 super admins and 8 admins. No plaintext passwords were stored.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
