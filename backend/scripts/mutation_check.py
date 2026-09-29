"""
Prove the conformance tests actually bite.

Put each known-wrong value back, one at a time, and confirm the suite fails. A
test that does not fail on the bug it was written for is decoration - which is
exactly what happened with the hint penalty: test_official_constants.py
asserted 120 and called it correct, so the suite certified the bug instead of
catching it.

Run after changing anything in app/core/constants.py or any scoring rule:

    .venv/Scripts/python scripts/mutation_check.py
"""

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
PY = BACKEND / ".venv" / "Scripts" / "python.exe"

CONSTANTS = "app/core/constants.py"
SCORING_R1 = "app/scoring/round1_scoring.py"
BLACK_MARKET = "app/services/black_market_service.py"
CABO = "app/services/cabo_service.py"
ROUND_SERVICE = "app/services/round_service.py"
CHAMP_SCORING = "app/scoring/championship_scoring.py"
API_R3 = "app/api/rounds/round3.py"

CONFORMANCE = "tests/test_documentation_conformance.py"
ODDYSSEY = "tests/test_oddyssey_rules.py"

# (label, file, correct snippet, wrong snippet, tests that must catch it)
MUTATIONS = [
    # --- values in constants.py ---------------------------------------------
    ("hint penalty 300 -> 120 (the shipped bug)", CONSTANTS,
     "DEFAULT_R1_HINT_PENALTY_SECONDS: Final[int] = 300",
     "DEFAULT_R1_HINT_PENALTY_SECONDS: Final[int] = 120",
     CONFORMANCE),
    ("code fragments 4 -> 2 (the pre-ODDyssey spec)", CONSTANTS,
     "CODE_FRAGMENT_COUNT: Final[int] = 4",
     "CODE_FRAGMENT_COUNT: Final[int] = 2",
     CONFORMANCE),
    ("fragment price 350 -> 400", CONSTANTS,
     "BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED: Final[float] = 350.0",
     "BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED: Final[float] = 400.0",
     CONFORMANCE),
    ("starting balance 1000 -> 100", CONSTANTS,
     "STARTING_WALLET_BALANCE: Final[float] = 1000.0",
     "STARTING_WALLET_BALANCE: Final[float] = 100.0",
     CONFORMANCE),
    ("agent correct +30 -> +10", CONSTANTS,
     "AGENT_CORRECT_GUESS: Final[float] = 30.0",
     "AGENT_CORRECT_GUESS: Final[float] = 10.0",
     CONFORMANCE),
    ("agent wrong -20 -> -5", CONSTANTS,
     "AGENT_WRONG_GUESS: Final[float] = -20.0",
     "AGENT_WRONG_GUESS: Final[float] = -5.0",
     CONFORMANCE),
    ("carryover 1.0 -> 0.10 (the superseded weight)", CONSTANTS,
     "FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED: Final[float] = 1.0",
     "FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED: Final[float] = 0.10",
     CONFORMANCE),
    ("carryover percent 100 -> 10", CONSTANTS,
     "DEFAULT_CARRYOVER_WEIGHT_PERCENT: Final[float] = 100.0",
     "DEFAULT_CARRYOVER_WEIGHT_PERCENT: Final[float] = 10.0",
     CONFORMANCE),
    ("the final score stops summing the wallet in full", CHAMP_SCORING,
     "    bm_comp = bm_balance * weight",
     "    bm_comp = bm_balance * 0.10",
     ODDYSSEY),

    # --- ODDyssey Section 5: two organiser signatures -----------------------
    ("dual signature requirement switched off", CONSTANTS,
     "REQUIRE_BLACK_MARKET_DUAL_SIGNATURE: Final[bool] = True",
     "REQUIRE_BLACK_MARKET_DUAL_SIGNATURE: Final[bool] = False",
     ODDYSSEY),
    ("an organiser may countersign their own transaction", API_R3,
     "        if countersigner.lower() in {",
     "        if False and countersigner.lower() in {",
     ODDYSSEY),
    ("the countersignature is accepted but never stored", BLACK_MARKET,
     "        countersigned_by=countersigned_by,\n    )\n    db.add(bmp)",
     "        countersigned_by=None,\n    )\n    db.add(bmp)",
     ODDYSSEY),
    ("finale field 8 -> 3", CONSTANTS,
     "R4_ADVANCING_COUNT: Final[int] = 8",
     "R4_ADVANCING_COUNT: Final[int] = 3",
     CONFORMANCE),
    ("rubric questioning 15 -> 20", CONSTANTS,
     "R4_RUBRIC_RESOURCE_PERSON_MAX: Final[float] = 15.0",
     "R4_RUBRIC_RESOURCE_PERSON_MAX: Final[float] = 20.0",
     CONFORMANCE),

    # --- ODDyssey Section 4: Round 1 rule penalties --------------------------
    ("phone-use penalty 10 min -> 5 min", CONSTANTS,
     "R1_PENALTY_PHONE_USE_SECONDS: Final[int] = 600",
     "R1_PENALTY_PHONE_USE_SECONDS: Final[int] = 300",
     ODDYSSEY),
    ("separation penalty 5 min -> 0", CONSTANTS,
     "R1_PENALTY_TEAM_SEPARATION_SECONDS: Final[int] = 300",
     "R1_PENALTY_TEAM_SEPARATION_SECONDS: Final[int] = 0",
     ODDYSSEY),
    ("clue damage -20 -> -50 points", CONSTANTS,
     "R1_CLUE_DAMAGE_POINT_PENALTY: Final[float] = -20.0",
     "R1_CLUE_DAMAGE_POINT_PENALTY: Final[float] = -50.0",
     ODDYSSEY),
    ("rule penalties dropped from the adjusted gate time", SCORING_R1,
     'mr["adjusted_seconds"] = duration + total_penalty',
     'mr["adjusted_seconds"] = duration + hint_penalty',
     ODDYSSEY),
    ("rule penalties dropped from the team total", SCORING_R1,
     "total_penalty_seconds = total_hint_penalty_seconds + total_rule_penalty_seconds",
     "total_penalty_seconds = total_hint_penalty_seconds",
     ODDYSSEY),
    ("clue damage scored as time as well as points", SCORING_R1,
     "        + separation * R1_PENALTY_TEAM_SEPARATION_SECONDS\n    )",
     "        + separation * R1_PENALTY_TEAM_SEPARATION_SECONDS\n"
     "        + max(0, int(mini_round.get('clue_damage_count', 0) or 0)) * 60\n    )",
     ODDYSSEY),

    ("legacy bridge refunds the rule penalty on every edit", ROUND_SERVICE,
     "            timing.adjusted_seconds = int(duration + hints * penalty_per_hint + rule_penalty)",
     "            timing.adjusted_seconds = int(duration + hints * penalty_per_hint)",
     ODDYSSEY),
    ("legacy record total drops the rule penalty", ROUND_SERVICE,
     "    total_penalty += float(rule_penalty_seconds or 0)",
     "    total_penalty += 0.0",
     ODDYSSEY),

    # --- ODDyssey Section 5: market stock ------------------------------------
    ("prep time stock 4 -> unlimited", CONSTANTS,
     '"EXTRA_PREP_TIME": 4,',
     '"EXTRA_PREP_TIME": None,',
     ODDYSSEY),
    ("agent intel stock 5 -> 50", CONSTANTS,
     '"AGENT_INTEL": 5,',
     '"AGENT_INTEL": 50,',
     ODDYSSEY),
    ("stock never checked at the till", BLACK_MARKET,
     "    assert_in_stock(db, clean_asset, quantity)",
     "    pass  # assert_in_stock(db, clean_asset, quantity)",
     ODDYSSEY),
    ("code fragments rationed like everything else", BLACK_MARKET,
     "    limit = BLACK_MARKET_STOCK.get(clean)\n"
     "    if limit is None:\n        return None",
     "    limit = BLACK_MARKET_STOCK.get(clean)\n"
     "    if limit is None:\n        limit = 1",
     ODDYSSEY),

    # --- ODDyssey Section 4: Cabo tie-breakers 4 and 5 -----------------------
    ("tie-break result ignored by the standings sort", CABO,
     '            item["tie_break_rank"] if item["tie_break_rank"] is not None else 10**6,',
     "            0,",
     ODDYSSEY),
    ("a resolved tie still reported as unresolved", CABO,
     "            if _separated_from(other):",
     "            if False:",
     ODDYSSEY),
    ("one-sided resolution treated as a resolved tie", CABO,
     "            return mine is not None and theirs is not None and mine != theirs",
     "            return mine is not None or theirs is not None",
     ODDYSSEY),
]

originals = {}
for _, path, _, _, _ in MUTATIONS:
    if path not in originals:
        originals[path] = (BACKEND / path).read_text(encoding="utf-8")

survivors = []

try:
    for label, path, old, new, tests in MUTATIONS:
        source = originals[path]
        if source.count(old) != 1:
            print(
                f"SKIP        {label}  "
                f"(anchor appears {source.count(old)}x in {path} - update this script)"
            )
            survivors.append(label)
            continue

        (BACKEND / path).write_text(source.replace(old, new), encoding="utf-8")
        try:
            r = subprocess.run(
                [str(PY), "-m", "pytest", tests, "-q", "--no-header", "-x", "--tb=no"],
                cwd=str(BACKEND), capture_output=True, text=True,
            )
        finally:
            (BACKEND / path).write_text(source, encoding="utf-8")

        tail = [l for l in r.stdout.splitlines() if "passed" in l or "failed" in l]
        if r.returncode == 0:
            print(f"NOT CAUGHT  {label}")
            survivors.append(label)
        else:
            print(f"caught      {label}   ({tail[-1].strip() if tail else ''})")
finally:
    # Belt and braces: every touched file goes back exactly as it was, even if
    # the loop above died between a write and its own restore.
    for path, source in originals.items():
        (BACKEND / path).write_text(source, encoding="utf-8")

print()
if survivors:
    print(f"{len(survivors)} mutation(s) SURVIVED - those rules are not actually protected.")
    sys.exit(1)
print(f"All {len(MUTATIONS)} mutations caught. Sources restored.")
