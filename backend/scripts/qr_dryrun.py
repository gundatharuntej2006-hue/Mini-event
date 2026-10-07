"""
Dry run for the DEPLOYED lineage (upstream/main): QR checkpoints + the ladder.

scripts/rehearsal.py cannot run here - it was written against the rules-engine
branch and asserts endpoints and constants this build does not carry. This
script asserts only what main actually ships, so a FAIL here is a real defect
rather than a branch difference.

Run it:
    cd backend
    <venv>/Scripts/python scripts/qr_dryrun.py
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("SECRET_KEY", "dryrun_only_secret_key_at_least_32_characters")
_DB = Path(tempfile.gettempdir()) / "eventhq_qr_dryrun.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB.as_posix()}"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import get_password_hash  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

FAILURES = []


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + ("" if ok else f"\n        -> {str(detail)[:260]}"))
    if not ok:
        FAILURES.append(label)
    return ok


def note(text):
    print(f"  ..    {text}")


def section(title):
    print(f"\n{title}\n{'-' * len(title)}")


def data(resp):
    try:
        return resp.json().get("data")
    except Exception:  # noqa: BLE001
        return None


def finalized(resp):
    """A finalize endpoint answers 200 with can_finalize:false when it refuses."""
    if resp.status_code != 200:
        return False, resp.text[:260]
    d = data(resp) or {}
    if isinstance(d, dict) and d.get("can_finalize") is False:
        return False, "; ".join(f"{i.get('code')}: {i.get('message')}" for i in (d.get("issues") or []))[:300]
    return True, d


Base.metadata.create_all(bind=engine)
client = TestClient(app)


def _user(email, role):
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == email).first():
            db.add(User(email=email, name=email.split("@")[0].title(),
                        hashed_password=get_password_hash("DryRunPass123!"), role=role))
            db.commit()
    finally:
        db.close()
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "DryRunPass123!"})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['data']['accessToken']}"}


ORG = _user("dryrun.organizer@bmsit.in", UserRole.ORGANIZER)
try:
    MARSHAL = _user("dryrun.marshal@bmsit.in", UserRole.MARSHAL)
except Exception:  # noqa: BLE001
    MARSHAL = ORG
BASE_TIME = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)

# ------------------------------------------------------------ registration
section("Registration: 32 squads x 5")
teams = []
for t in range(32):
    tid = data(client.post("/api/v1/teams", json={"name": f"Squad {t + 1:02d}"}, headers=ORG))["id"]
    teams.append(tid)
    for m in range(5):
        client.post("/api/v1/participants", json={
            "name": f"Squad {t + 1:02d} Player {m + 1}",
            "email": f"q{t + 1:02d}p{m + 1}@bmsit.in",
            "usn": f"1BM26CS{t * 5 + m + 1:03d}",
            "teamId": tid,
        }, headers=ORG)
check("32 squads registered", len(teams) == 32, len(teams))

roster = data(client.get("/api/teams", headers=ORG)) or []
ident = {}
for r in roster:
    ident[r["id"]] = str(r.get("teamNumber") or "")
note(f"team identifiers look like: {[v for v in list(ident.values())[:3]]}")

# ------------------------------------------------------------ QR: the parts a phone hits
section("QR checkpoints (what a participant's phone actually calls)")

# The gates refuse every scan until an organiser presses start. That guard is
# correct and is itself worth asserting - a QR mounted on a wall is live the
# moment it is printed, so the server has to be the thing that says "not yet".
r_early = client.post("/api/rounds/1/gates/1/checkin", json={"team_identifier": ident.get(teams[0])})
check("a gate QR is refused BEFORE the organiser starts Round 1",
      r_early.status_code >= 400 and "not been started" in r_early.text,
      f"HTTP {r_early.status_code} {r_early.text[:160]}")

r = client.post("/api/rounds/1/start", headers=ORG)
check("the organiser can start Round 1", r.status_code == 200, f"HTTP {r.status_code} {r.text[:200]}")

r = client.get("/api/rounds/1/teams/public-list")
pub = data(r) or []
check("squad list for the QR gate page loads WITHOUT a login", r.status_code == 200 and len(pub) == 32,
      f"HTTP {r.status_code}, {len(pub)} squads")

for g in (1, 2, 3):
    r = client.get(f"/api/rounds/1/gates/{g}/public")
    check(f"Gate {g} public checkpoint page loads without a login",
          r.status_code == 200 and data(r), f"HTTP {r.status_code} {r.text[:120]}")

first_team = teams[0]
# Take the identifier from the public squad list rather than inventing one:
# that list is literally what the QR gate page shows a participant to pick
# from, so it is the only spelling a real phone can send.
if pub:
    note(f"public-list entry keys: {sorted(pub[0].keys())[:9]}")
    note(f"public-list first entry: {str(pub[0])[:180]}")
first_ident = None
if pub:
    e = pub[0]
    for k in ("team_identifier", "teamIdentifier", "team_number", "teamNumber", "id", "team_id"):
        if e.get(k):
            first_ident = str(e[k])
            break
first_ident = first_ident or ident.get(first_team) or "1"
note(f"using team_identifier={first_ident!r} for the QR scans")

def _stamp(d):
    """The check-in response spells its timestamp differently per build."""
    if not isinstance(d, dict):
        return None
    # official_scanned_at FIRST: scanned_at is the time of *this* scan and is
    # meant to move, while official_scanned_at is the one that counts and must
    # survive a re-scan. Reading the wrong one reports a bug that isn't there.
    for k in ("official_scanned_at", "officialScannedAt", "checked_in_at",
              "checkedInAt", "scanned_at", "scannedAt"):
        if d.get(k):
            return d[k]
    return None


r = client.post("/api/rounds/1/gates/1/checkin", json={"team_identifier": first_ident})
ok = r.status_code == 200
check("a squad can check in at Gate 1 by scanning the QR", ok, f"HTTP {r.status_code} {r.text[:200]}")
if ok:
    note(f"gate check-in response keys: {sorted((data(r) or {}).keys())}")
first_stamp = _stamp(data(r)) if ok else None

r2 = client.post("/api/rounds/1/gates/1/checkin", json={"team_identifier": first_ident})
second_stamp = _stamp(data(r2))
check("a second scan of the same QR keeps the FIRST official timestamp",
      r2.status_code == 200 and first_stamp and first_stamp == second_stamp,
      f"first={first_stamp} second={second_stamp}")
check("the re-scan is flagged as a duplicate, not counted again",
      (data(r2) or {}).get("is_duplicate") is True,
      f"is_duplicate={(data(r2) or {}).get('is_duplicate')}")

r = client.post("/api/rounds/1/gates/1/checkin", json={"team_identifier": "9999"})
check("an unregistered squad is refused at the gate", r.status_code >= 400 or (data(r) or {}) == {},
      f"HTTP {r.status_code} {r.text[:160]}")

for g in (2, 3):
    r = client.post(f"/api/rounds/1/gates/{g}/checkin", json={"team_identifier": first_ident})
    check(f"a squad can check in at Gate {g}", r.status_code == 200, f"HTTP {r.status_code} {r.text[:160]}")

for tid in teams[1:12]:
    client.post("/api/rounds/1/gates/1/checkin", json={"team_identifier": ident.get(tid)})

feed = data(client.get("/api/rounds/1/checkins", headers=ORG)) or []
check("the organiser's live scan feed shows the check-ins", len(feed) >= 12, f"{len(feed)} records")
g1 = data(client.get("/api/rounds/1/checkins?gate=1", headers=ORG)) or []
check("the scan feed can be filtered to one gate", len(g1) >= 12 and len(g1) <= len(feed),
      f"gate1={len(g1)} all={len(feed)}")

# ------------------------------------------------------------ QR: the location-scan game
section("QR location scans (the campus clue hunt)")

r = client.post("/api/rounds/1/allocations/generate", headers=ORG)
check("per-squad location allocations generate", r.status_code == 200, f"HTTP {r.status_code} {r.text[:160]}")
allocs = data(client.get("/api/rounds/1/allocations", headers=ORG)) or {}
alist = allocs.get("allocations") if isinstance(allocs, dict) else allocs
check("every squad gets an allocation", bool(alist) and len(alist) == 32, f"{len(alist or [])} allocations")

# The participant session keys off the ALLOCATION identifier (a 4-digit code
# like 1001), not the team number the gate page uses. Two different spellings
# of "which squad are you" in the same round is worth knowing about.
alloc_ident = None
if alist:
    note(f"allocation entry keys: {sorted(alist[0].keys())[:10]}")
    for k in ("team_identifier", "teamIdentifier", "team_number", "teamNumber"):
        if alist[0].get(k):
            alloc_ident = str(alist[0][k])
            break
note(f"gate page uses {first_ident!r}; allocations use {alloc_ident!r}")

r = client.post("/api/rounds/1/participant/session",
                json={"team_identifier": alloc_ident or first_ident})
sess = data(r) or {}
token = sess.get("session_token") or sess.get("sessionToken") or sess.get("token")
check("a participant device signs in with just the 4-digit squad ID (no password)",
      r.status_code == 200 and bool(token), f"HTTP {r.status_code} {r.text[:200]}")

if token:
    cur = data(client.get(f"/api/rounds/1/participant/current?token={token}")) or {}
    check("the phone is told its current checkpoint only", bool(cur), str(cur)[:160])
    # The scan takes an integer location number, not a string code, and the
    # phone learns its own number from /participant/current.
    expected = cur.get("current_location_number")
    note(f"current checkpoint payload keys: {sorted(cur.keys())[:8]}")
    wrong = (expected + 1) if isinstance(expected, int) else 99
    if wrong == expected:
        wrong = expected + 2

    r = client.post(f"/api/rounds/1/participant/scan?token={token}", json={"location": wrong})
    body_wrong = data(r) or {}
    wrong_rejected = (r.status_code >= 400) or (body_wrong.get("valid") is False) or (body_wrong.get("isValid") is False) or (body_wrong.get("matched") is False)
    check("scanning the WRONG location QR is rejected", wrong_rejected, f"HTTP {r.status_code} {str(body_wrong)[:200]}")

    if expected:
        r = client.post(f"/api/rounds/1/participant/scan?token={token}", json={"location": expected})
        b = data(r) or {}
        right_ok = r.status_code == 200 and (b.get("valid") is not False and b.get("isValid") is not False)
        check("scanning the CORRECT location QR is accepted", right_ok, f"HTTP {r.status_code} {str(b)[:200]}")
    else:
        note("could not read the assigned location from /participant/current - correct-scan check skipped")

# ------------------------------------------------------------ the ladder
section("The ladder: 32 -> 16 -> 12 -> 6")

for i, tid in enumerate(teams):
    per_leg = 300 + i * 11
    for leg in (1, 2, 3):
        start = BASE_TIME + timedelta(minutes=leg * 40)
        client.post(f"/api/rounds/1/teams/{tid}/timings", json={
            "mini_round_number": leg,
            "start_time": start.isoformat(),
            "completion_time": (start + timedelta(seconds=per_leg)).isoformat(),
            "hints_used": 0,
        }, headers=MARSHAL)

r1 = data(client.get("/api/rounds/1/teams", headers=ORG)) or []
check("every squad is ranked in Round 1", len([x for x in r1 if x.get("rank") is not None]) == 32,
      f"{len([x for x in r1 if x.get('rank') is not None])} of 32")

ok, detail = finalized(client.post("/api/rounds/1/finalize", headers=ORG))
check("Round 1 finalized", ok, detail)
if ok:
    adv = data(client.get("/api/rounds/2/teams", headers=ORG)) or []
    q = [t for t in adv if t.get("round1_qualified") or t.get("round1Qualified")]
    check("exactly 16 squads advance to Round 2", len(q) == 16, f"{len(q)} advanced")

r = client.post("/api/rounds/2/cabo/generate", headers=ORG)
check("Cabo tables generated", r.status_code == 200, f"HTTP {r.status_code} {r.text[:200]}")

print("\n" + "=" * 62)
print("FAILURES" if FAILURES else "All checks passed.")
for f in FAILURES:
    print("  - " + f)
sys.exit(1 if FAILURES else 0)
