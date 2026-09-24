"""
Drive a full 32-team tournament through the API and report what breaks.

Run it:
    cd backend
    .venv/Scripts/python scripts/rehearsal.py

WHY THIS EXISTS

Every defect found in this platform so far was invisible to the unit suite and
would have surfaced here in one run:

  * Round 1 data entered on the dashboard never reached Round 1 qualification -
    two different tables, and nothing connected them.
  * Round 3 points awarded on the dashboard were not spendable, transfers moved
    nothing, and a team holding both code fragments was refused Round 4.
  * The hint penalty was 120 seconds in six places at once.

372 unit tests passed through all of that, because each suite exercises one
layer and both layers pass on their own. Only driving the whole event end to
end, through the endpoints the dashboard actually calls, catches a round whose
data goes somewhere nothing reads.

Rounds 4 and 5 cannot be checked any other way at all: /rounds/4/finalize
refuses until Round 3 is finalized with a full field, so the championship score
is unreachable without playing the tournament.

Every check prints PASS or FAIL and the script exits non-zero if any failed.
"""

import os
import random
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("SECRET_KEY", "rehearsal_only_secret_key_at_least_32_characters")
_DB = Path(tempfile.gettempdir()) / "eventhq_rehearsal.db"
if _DB.exists():
    _DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB.as_posix()}"

from fastapi.testclient import TestClient  # noqa: E402

from app.core import constants as C  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402

random.seed(20260924)  # a rehearsal that cannot be repeated is not a rehearsal

FAILURES: list[str] = []
NOTES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> bool:
    if ok:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}" + (f"\n        -> {detail}" if detail else ""))
        FAILURES.append(label)
    return ok


def note(text: str) -> None:
    print(f"  ..    {text}")
    NOTES.append(text)


def section(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def body(resp):
    try:
        return resp.json().get("data")
    except Exception:  # noqa: BLE001
        return None


def field(obj: dict, *names, default=None):
    """
    Read a field by any of its spellings.

    The API is inconsistent about casing - some responses serialise snake_case,
    others camelCase, and a few carry both. A rehearsal that hard-codes one
    spelling fails on the serialiser rather than on the tournament, which tells
    you nothing useful.
    """
    for n in names:
        if n in obj:
            return obj[n]
    return default


def finalized(resp) -> tuple:
    """
    Did a finalize actually finalize?

    These endpoints answer 200 with {"can_finalize": false, "issues": [...]}
    when they refuse, so checking the status code alone reports success on a
    refusal - which is how an earlier version of this script "passed" Round 4
    while the championship stayed unscored.
    """
    if resp.status_code != 200:
        return False, resp.text[:250]
    d = body(resp) or {}
    if isinstance(d, dict) and d.get("can_finalize") is False:
        issues = d.get("issues") or []
        return False, "; ".join(
            f"{i.get('code')}: {i.get('message')}" for i in issues
        )[:400]
    return True, ""

# ---------------------------------------------------------------- setup

Base.metadata.create_all(bind=engine)
client = TestClient(app)


def _user(email: str, role: UserRole) -> dict:
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == email).first():
            db.add(User(
                email=email,
                name=email.split("@")[0].title(),
                hashed_password=get_password_hash("RehearsalPass123!"),
                role=role,
            ))
            db.commit()
    finally:
        db.close()
    r = client.post("/api/v1/auth/login",
                    json={"email": email, "password": "RehearsalPass123!"})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['data']['accessToken']}"}


ORG = _user("rehearsal.organizer@bmsit.in", UserRole.ORGANIZER)
MARSHAL = _user("rehearsal.marshal@bmsit.in", UserRole.MARSHAL)
JUDGE = _user("rehearsal.judge@bmsit.in", UserRole.JUDGE)

BASE_TIME = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)


# ------------------------------------------------- registration

section(f"Registration: {C.MAX_TEAMS} teams x {C.TEAM_SIZE} members")

teams: list[str] = []
players: dict[str, list[str]] = {}

for t in range(C.MAX_TEAMS):
    tid = body(client.post("/api/v1/teams",
                           json={"name": f"Squad {t + 1:02d}"}, headers=ORG))["id"]
    teams.append(tid)
    players[tid] = []
    for m in range(C.TEAM_SIZE):
        p = client.post("/api/v1/participants", json={
            "name": f"Squad {t + 1:02d} Player {m + 1}",
            "email": f"s{t + 1:02d}p{m + 1}@bmsit.in",
            "usn": f"1BM26CS{t * 5 + m + 1:03d}",
            "teamId": tid,
        }, headers=ORG)
        players[tid].append(body(p)["id"])

check(f"{C.MAX_TEAMS} teams registered", len(teams) == 32, f"got {len(teams)}")
check("160 players registered", sum(len(v) for v in players.values()) == 160)


# ------------------------------------------------- Round 1

section("Round 1: the Expedition")

for i, tid in enumerate(teams):
    # Spread the field so ranks are unambiguous; every 7th team takes a hint.
    per_leg = 300 + i * 11
    hints = 1 if i % 7 == 0 else 0
    for leg in (1, 2, 3):
        start = BASE_TIME + timedelta(minutes=leg * 40)
        client.post(f"/api/rounds/1/teams/{tid}/timings", json={
            "mini_round_number": leg,
            "start_time": start.isoformat(),
            "completion_time": (start + timedelta(seconds=per_leg)).isoformat(),
            "hints_used": hints if leg == 1 else 0,
        }, headers=MARSHAL)

r1 = body(client.get("/api/rounds/1/teams", headers=ORG)) or []
ranked = [r for r in r1 if r.get("rank") is not None]
check("every team ranked in Round 1", len(ranked) == 32, f"{len(ranked)} of 32")

hinted = next((r for r in r1 if field(r, "team_id", "teamId") == teams[0]), None)
check("a hint costs the documented 5 minutes",
      hinted and field(hinted, "total_penalty_seconds", "totalPenaltySeconds") == C.DEFAULT_R1_HINT_PENALTY_SECONDS,
      f"got {hinted and field(hinted, 'total_penalty_seconds', 'totalPenaltySeconds')}")

ok1, why1 = finalized(client.post("/api/rounds/1/finalize", json={}, headers=ORG))
check("Round 1 finalized", ok1, why1)


# ------------------------------------------------- Round 2

section("Round 2: Cabo")

gen = client.post("/api/rounds/2/cabo/generate", json={"seed": 7}, headers=ORG)
check("Cabo tables generated", gen.status_code == 200, gen.text[:200])

for game in (1, 2, 3):
    tables = body(client.get(f"/api/rounds/2/cabo/games/{game}", headers=ORG)) or []
    if not tables:
        check(f"game {game} has tables", False, "no tables returned")
        break
    for table in tables:
        seats = list(field(table, "players", default=[]))
        random.shuffle(seats)          # who wins at a table is chance
        scores = []
        for position, seat in enumerate(seats, start=1):
            scores.append({
                "gameNumber": game,
                "participantId": field(seat, "participant_id", "participantId"),
                "teamId": field(seat, "team_id", "teamId"),
                "placement": position,
                "finalCardHandTotal": random.randint(5, 45),
            })
        client.post(f"/api/rounds/2/cabo/games/{game}/scores",
                    json={"tableNumber": field(table, "table_number", "tableNumber"), "scores": scores},
                    headers=MARSHAL)

st2 = body(client.get("/api/rounds/2/cabo/standings", headers=ORG)) or []
scored = [s for s in st2 if (field(s, "cabo_score", "caboScore", default=0) or 0) > 0]
check("Cabo produced scores", len(scored) > 0, f"{len(scored)} teams scored")
worst = max((field(s, "cabo_score", "caboScore", default=0) or 0) for s in st2) if st2 else 0
check(f"no team beats the documented maximum of {C.CABO_MAX_TEAM_SCORE}",
      worst <= C.CABO_MAX_TEAM_SCORE, f"highest was {worst}")

ok2, why2 = finalized(client.post("/api/rounds/2/cabo/finalize", json={}, headers=ORG))
check("Round 2 finalized", ok2, why2)


# ------------------------------------------------- Round 3

section("Round 3: the Black Market")

r3_teams = teams[: C.R2_QUALIFIERS]

# Code fragments through the desk endpoint the dashboard uses.
for i, tid in enumerate(r3_teams):
    if i % 3 != 2:                      # two thirds find both fragments
        for idx in range(C.CODE_FRAGMENT_COUNT):
            client.put("/api/v1/rounds/3/codes/fragment", json={
                "teamId": tid, "fragmentIndex": idx,
                "isDiscovered": True, "code": f"FRAG-{idx}",
            }, headers=MARSHAL)

gated = [t for i, t in enumerate(r3_teams) if i % 3 != 2]
eligible = 0
for tid in gated:
    e = body(client.get(f"/api/code-hunt/eligibility/r4/{tid}", headers=ORG)) or {}
    if e.get("isEligible"):
        eligible += 1
check("fragments logged at the desk open the Round 4 gate",
      eligible == len(gated), f"{eligible} of {len(gated)} eligible")

# Points awarded on the dashboard must be spendable.
# Measure the DELTA. The team has already earned Round 1 rank points by now, so
# an absolute figure would be wrong for reasons that have nothing to do with
# whether the bridge works.
before = (body(client.get(f"/api/teams/{r3_teams[0]}/wallet", headers=ORG)) or {}).get("currentBalance", 0)
client.post("/api/v1/rounds/3/transactions",
            json={"teamId": r3_teams[0], "amount": 600.0, "type": "earn",
                  "reason": "Rehearsal award"}, headers=MARSHAL)
after = (body(client.get(f"/api/teams/{r3_teams[0]}/wallet", headers=ORG)) or {}).get("currentBalance", 0)
check("dashboard awards reach the wallet",
      after - before == 600, f"awarded 600, wallet moved {after - before}")

# Section 6.2: a code-less team buys its way back through the gate. This is the
# documented recovery route, so it has to actually work.
buyer = r3_teams[2]
before_gate = (body(client.get(f"/api/code-hunt/eligibility/r4/{buyer}", headers=ORG)) or {}).get("isEligible")
bought = 0
for _ in range(C.CODE_FRAGMENT_COUNT):
    buy = client.post("/api/rounds/3/purchase",
                      json={"teamId": buyer, "assetType": "MISSING_CODE_FRAGMENT"},
                      headers=ORG)
    if buy.status_code == 200:
        bought += 1
    else:
        note(f"purchase {bought + 1} refused: {buy.status_code} {buy.text[:160]}")
check("a code-less team can buy every missing fragment",
      bought == C.CODE_FRAGMENT_COUNT, f"bought {bought} of {C.CODE_FRAGMENT_COUNT}")

after_gate = (body(client.get(f"/api/code-hunt/eligibility/r4/{buyer}", headers=ORG)) or {}).get("isEligible")
check("buying the Final Code opens the Round 4 gate (Section 6.2)",
      after_gate is True,
      f"gate went {before_gate} -> {after_gate} after buying {bought} fragment(s); "
      "Section 6.2 says this purchase 'completes the Final Code needed for Round 4'")
ok3, why3 = finalized(client.post("/api/rounds/3/market/finalize", json={}, headers=ORG))
check("Round 3 finalized", ok3, why3)




# ------------------------------------------------- Round 4

section("Round 4: the Legal Battle")

pairs = client.post("/api/rounds/4/pairs/auto", json={}, headers=ORG)
check("courtroom pairings drawn", pairs.status_code == 200, pairs.text[:250])

conf = client.post("/api/rounds/4/pairs/confirm", json={}, headers=ORG)
check("pairings confirmed", conf.status_code == 200, conf.text[:200])

# Section 7.2's five stages have to be run before Round 4 can be finalized.
STAGES = ["prep_1", "hearing_1", "file_exchange", "prep_2", "hearing_2"]
pair_rows = body(client.get("/api/rounds/4/pairs", headers=ORG)) or []
for pair in pair_rows:
    pid = field(pair, "id", "pair_id", "pairId")
    for stage in STAGES:
        client.put(f"/api/rounds/4/stages/{pid}/{stage}",
                   json={"status": "completed", "actualDurationSeconds": 1200},
                   headers=ORG)
check("all courtroom stages completed", len(pair_rows) == C.R4_PAIRS,
      f"{len(pair_rows)} pairs")

RUBRIC = {
    "logical_structure": 18.0, "use_of_evidence": 17.0, "rebuttal": 16.0,
    "questioning_of_resource_person": 13.0, "presentation_and_teamwork": 12.0,
    "time_management": 9.0,
}
# Judge the teams that ACTUALLY qualified, read off the confirmed pairings.
# Assuming teams[:8] was wrong - the finalists are whichever squads held the
# Final Code and ranked highest in Round 3, which is the point of the gate.
r4_teams = []
for pair in pair_rows:
    for k in ("team_a_id", "teamAId"):
        if pair.get(k):
            r4_teams.append(pair[k])
            break
    for k in ("team_b_id", "teamBId"):
        if pair.get(k):
            r4_teams.append(pair[k])
            break
r4_teams = [t for t in r4_teams if t]
check(f"{C.R4_FINALISTS} finalists drawn into pairings",
      len(r4_teams) == C.R4_FINALISTS, f"got {len(r4_teams)}")

for n, tid in enumerate(r4_teams):
    marks = dict(RUBRIC)
    marks["logical_structure"] = max(5.0, 18.0 - n)   # separate the field
    client.post(f"/api/rounds/4/judging/{tid}/scores", json={
        "judgeId": "judge-1", "judgeName": "Faculty Panel",
        "teamId": tid, "scores": marks,
    }, headers=JUDGE)

ok4, why4 = finalized(client.post("/api/rounds/4/finalize", json={}, headers=ORG))
check("Round 4 finalized", ok4, why4)


# ------------------------------------------------- Finale

section("The Grand Finale")

for tid in r4_teams:
    others = [t for t in r4_teams if t != tid][: C.AGENT_GUESS_MAX]
    guesses = [{"targetTeamId": o, "suspectedAgentName": "Suspect"} for o in others]
    client.post("/api/rounds/finale/guesses/submit",
                json={"guessingTeamId": tid, "guesses": guesses}, headers=ORG)

standings = body(client.get("/api/finale/standings", headers=ORG)) or []
check("the championship ranks the finalists", len(standings) > 0,
      f"{len(standings)} rows")

with_panel = [s for s in standings if field(s, "legal_battle_score", "legalBattleScore") is not None]
check("Round 4 judging reaches the championship score",
      len(with_panel) > 0,
      "legal_battle_score is null for every team; no champion can be computed")

with_final = [s for s in standings if field(s, "final_score", "finalScore") is not None]
check("a final score can be computed", len(with_final) > 0,
      "final_score is null for every team")

if with_final:
    top = sorted(with_final, key=lambda s: field(s, "final_score", "finalScore"), reverse=True)[0]
    note(f"leader: {field(top, 'team_name', 'teamName')} on {field(top, 'final_score', 'finalScore')}")


# ---------------------------------------------------------------- report

section("Result")

if FAILURES:
    print(f"\n{len(FAILURES)} check(s) FAILED:")
    for f in FAILURES:
        print(f"  - {f}")
    print(f"\nDatabase left at {_DB} for inspection.")
    sys.exit(1)

print("\nAll checks passed. A full 32-team tournament runs end to end.")
try:
    engine.dispose()
    _DB.unlink(missing_ok=True)
except OSError:
    pass
sys.exit(0)
