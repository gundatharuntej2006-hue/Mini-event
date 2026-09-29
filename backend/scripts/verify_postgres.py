"""
Run the migrations against a real PostgreSQL, the way production will.

Why this exists: the first deploy of this backend failed on migration three
with "column is of type boolean but default expression is of type integer",
and would have failed again on migration five with "type already exists". Both
had been verified — on SQLite, which is what every test in this repo uses.

SQLite is permissive about exactly the things PostgreSQL enforces:

    booleans   SQLite stores them as integers and accepts DEFAULT 0.
               Postgres has a real boolean and rejects an integer default.
    enums      SQLite has no enum type; it stores them as VARCHAR, so
               re-declaring one costs nothing. Postgres creates a TYPE, and
               creating it twice is an error.
    ALTER      SQLite cannot ALTER a column, so alembic's batch_alter_table
               rebuilds the table. Postgres alters in place and will reject
               things the rebuild silently allowed.

A unit suite on SQLite cannot see any of that. This can, because it runs the
migrations against the same database engine Render provisions.

    python scripts/verify_postgres.py

Needs Docker. Brings up a throwaway Postgres on a high port, runs every
migration forward, back one, forward again, boots the app against it, checks
/health, and removes the container whether it passed or not. Nothing touches
a real database.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
CONTAINER = "evhq-verify-pg"
PORT = 55433
PG_IMAGE = "postgres:18-alpine"  # the major version Render provisions
DSN = f"postgresql+psycopg://postgres:verifypw@localhost:{PORT}/eventhq"

# The app refuses to start without one; its value is irrelevant here.
ENV = {
    **os.environ,
    "SECRET_KEY": "verification-only-secret-key-not-used-anywhere-0123456789",
    "DATABASE_URL": DSN,
}


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=str(BACKEND), env=ENV, text=True, **kw)


def docker(*args, check=True):
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=check)


def start_postgres():
    subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)
    docker(
        "run", "-d", "--name", CONTAINER,
        "-e", "POSTGRES_PASSWORD=verifypw",
        "-e", "POSTGRES_DB=eventhq",
        "-p", f"{PORT}:5432",
        PG_IMAGE,
    )
    print(f"  postgres starting on {PORT} ...", end="", flush=True)
    for _ in range(90):
        ready = subprocess.run(
            ["docker", "exec", CONTAINER, "pg_isready", "-U", "postgres"],
            capture_output=True,
        )
        if ready.returncode == 0:
            print(" ready")
            return
        time.sleep(1)
    raise SystemExit("\npostgres did not become ready within 90s")


def step(label, cmd):
    print(f"\n=== {label} ===")
    result = run(cmd, capture_output=True)
    tail = (result.stdout + result.stderr).strip().splitlines()
    for line in tail[-14:]:
        print("  " + line)
    if result.returncode != 0:
        raise SystemExit(f"\nFAILED: {label}")


def main():
    if subprocess.run(["docker", "ps"], capture_output=True).returncode != 0:
        raise SystemExit(
            "Docker is not running. Start Docker Desktop and try again — this "
            "check needs a real PostgreSQL, which is the entire point of it."
        )

    py = sys.executable
    try:
        print("=== bringing up PostgreSQL ===")
        start_postgres()

        step("migrate to head", [py, "-m", "alembic", "upgrade", "head"])
        # Down and up again: a migration that only works on an empty database
        # passes the first check and fails the first time anyone rolls back.
        step("downgrade one", [py, "-m", "alembic", "downgrade", "-1"])
        step("back up to head", [py, "-m", "alembic", "upgrade", "head"])

        step("boot the app and check /health", [
            py, "-c",
            "from fastapi.testclient import TestClient\n"
            "from app.main import app\n"
            "with TestClient(app) as c:\n"
            "    r = c.get('/api/v1/health')\n"
            "    assert r.status_code == 200, r.text\n"
            "    body = r.json()['data']\n"
            "    assert body['database'] == 'healthy', body\n"
            "    print('health:', body)\n",
        ])

        print("\nPostgreSQL verification passed. "
              "Migrations apply forward and back, and the app boots against them.")
    finally:
        subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)
        print(f"({CONTAINER} removed)")


if __name__ == "__main__":
    main()
