"""
Prove the conformance tests actually bite.

Put each known-wrong value back, one at a time, and confirm the suite fails. A
test that does not fail on the bug it was written for is decoration - which is
exactly what happened with the hint penalty: test_official_constants.py
asserted 120 and called it correct, so the suite certified the bug instead of
catching it.

Run after changing anything in app/core/constants.py:

    .venv/Scripts/python scripts/mutation_check.py
"""

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
CONSTANTS = BACKEND / "app" / "core" / "constants.py"
PY = BACKEND / ".venv" / "Scripts" / "python.exe"
TESTS = "tests/test_documentation_conformance.py"

MUTATIONS = [
    ("hint penalty 300 -> 120 (the shipped bug)",
     "DEFAULT_R1_HINT_PENALTY_SECONDS: Final[int] = 300",
     "DEFAULT_R1_HINT_PENALTY_SECONDS: Final[int] = 120"),
    ("code fragments 2 -> 4",
     "CODE_FRAGMENT_COUNT: Final[int] = 2",
     "CODE_FRAGMENT_COUNT: Final[int] = 4"),
    ("starting balance 1000 -> 100",
     "STARTING_WALLET_BALANCE: Final[float] = 1000.0",
     "STARTING_WALLET_BALANCE: Final[float] = 100.0"),
    ("agent correct +30 -> +10",
     "AGENT_CORRECT_GUESS: Final[float] = 30.0",
     "AGENT_CORRECT_GUESS: Final[float] = 10.0"),
    ("agent wrong -20 -> -5",
     "AGENT_WRONG_GUESS: Final[float] = -20.0",
     "AGENT_WRONG_GUESS: Final[float] = -5.0"),
    ("carryover weight 0.10 -> 0.0",
     "FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED: Final[float] = 0.10",
     "FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED: Final[float] = 0.0"),
    ("finale field 8 -> 3",
     "R4_ADVANCING_COUNT: Final[int] = 8",
     "R4_ADVANCING_COUNT: Final[int] = 3"),
    ("rubric questioning 15 -> 20",
     "R4_RUBRIC_RESOURCE_PERSON_MAX: Final[float] = 15.0",
     "R4_RUBRIC_RESOURCE_PERSON_MAX: Final[float] = 20.0"),
]

original = CONSTANTS.read_text(encoding="utf-8")
survivors = []

try:
    for label, old, new in MUTATIONS:
        if old not in original:
            print(f"SKIP        {label}  (anchor not found - update this script)")
            survivors.append(label)
            continue
        CONSTANTS.write_text(original.replace(old, new), encoding="utf-8")
        r = subprocess.run(
            [str(PY), "-m", "pytest", TESTS, "-q", "--no-header", "-x", "--tb=no"],
            cwd=str(BACKEND), capture_output=True, text=True,
        )
        tail = [l for l in r.stdout.splitlines() if "passed" in l or "failed" in l]
        if r.returncode == 0:
            print(f"NOT CAUGHT  {label}")
            survivors.append(label)
        else:
            print(f"caught      {label}   ({tail[-1].strip() if tail else ''})")
finally:
    CONSTANTS.write_text(original, encoding="utf-8")

print()
if survivors:
    print(f"{len(survivors)} mutation(s) SURVIVED - those rules are not actually protected.")
    sys.exit(1)
print(f"All {len(MUTATIONS)} mutations caught. constants.py restored.")
