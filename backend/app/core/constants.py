"""
EVENT HQ — Authoritative Tournament Constants & Rules Specification
Source of Truth: the ODDyssey Final Event Plan and the ODDyssey Rulebook.

This module defines the single canonical source of truth for tournament rules,
advancement cutoffs, scoring points, wallet economy, and agent parameters.

The three organizer decisions the older Event Documentation left open are all
resolved by the ODDyssey Final Event Plan and Rulebook:
1. R1 time-to-wallet-points conversion - Section 3 gives rank points, 1st = 24
   down to 24th = 1, so 25 - rank (R1_WALLET_POINTS_FORMULA).
2. Black Market item prices - Section 5's Market Catalogue prices every item
   (BLACK_MARKET_SUGGESTED_PRICES); organisers may still adjust them live.
3. Black Market carryover into the Finale - Section 1 and Rulebook Section 8
   carry the remaining balance in FULL, not at the previously suggested 10%
   (FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED = 1.0, still configurable).
"""

from typing import Dict, Final, List, Optional

# ==============================================================================
# 1. TOURNAMENT STRUCTURE & ADVANCEMENT
# ==============================================================================
MAX_TEAMS: Final[int] = 32
TEAM_SIZE: Final[int] = 5

R1_QUALIFIERS: Final[int] = 24       # Top 24 squads advance from Round 1 to Round 2
R2_QUALIFIERS: Final[int] = 12       # Top 12 squads advance from Round 2 to Round 3
R3_QUALIFIERS: Final[int] = 8        # Top 8 squads advance from Round 3 to Round 4
R4_FINALISTS: Final[int] = 8         # 8 finalist squads participate in Round 4
R4_PAIRS: Final[int] = 4             # Exactly 4 pairs in Round 4
R4_MAX_SCORE: Final[float] = 100.0   # Maximum Legal Battle judging score
R4_ADVANCING_COUNT: Final[int] = 8   # NO ELIMINATION: All 8 finalists advance to Grand Finale
PODIUM_SIZE: Final[int] = 3          # Champion, 1st Runner Up, 2nd Runner Up

# ==============================================================================
# 2. ROUND 1 — THE GREAT EXPEDITION
# ==============================================================================
# Section 4.3, rule 5: a hint "adds a fixed time penalty (e.g. +5 minutes)".
# Five minutes, in seconds. This was 120 (two minutes), which under-penalised
# every team that took a hint by three minutes - and Round 1 is ranked on
# adjusted total time, so it changed who reached Round 2.
DEFAULT_R1_HINT_PENALTY_SECONDS: Final[int] = 300
DEFAULT_R1_CHECKPOINTS: Final[List[str]] = [
    "Checkpoint Alpha",
    "Checkpoint Bravo",
    "Checkpoint Charlie",
]

# ODDyssey Section 4, Round 1 Scoring:
#   "Total time = time spent at gates + hint penalties + rule penalties"
# Only the hint penalty existed. The other three violations had nowhere to be
# recorded, so a squad that used a phone or split up finished on its raw time
# and could out-rank a squad that played by the rules.
R1_PENALTY_HINT_SECONDS: Final[int] = 300              # Using a hint, +5 minutes
R1_PENALTY_PHONE_USE_SECONDS: Final[int] = 600         # Unauthorised phone use, +10 minutes
R1_PENALTY_TEAM_SEPARATION_SECONDS: Final[int] = 300   # Separating from the team, +5 minutes

# "Moving or damaging a clue: -20 points or disqualification." This one is
# scored in points, not seconds, and the marshal may escalate to a DQ instead.
R1_CLUE_DAMAGE_POINT_PENALTY: Final[float] = -20.0

# Time-valued rule violations, keyed by the code stored on the timing row.
R1_RULE_PENALTY_SECONDS: Final[Dict[str, int]] = {
    "UNAUTHORISED_PHONE_USE": R1_PENALTY_PHONE_USE_SECONDS,
    "TEAM_SEPARATION": R1_PENALTY_TEAM_SEPARATION_SECONDS,
}

# Every violation the plan names, including the two that are not time-valued.
R1_RULE_VIOLATIONS: Final[List[str]] = [
    "UNAUTHORISED_PHONE_USE",
    "TEAM_SEPARATION",
    "CLUE_DAMAGE",
]

# ODDyssey Section 3 resolves what the older documentation left pending:
# "For Black Market points, qualifying teams receive rank points: 1st = 24,
# 2nd = 23, continue decreasing, 24th = 1." Implemented in
# wallet.calculate_r1_reward as 25 - rank, zero outside the qualifying 24.
R1_WALLET_POINTS_FORMULA: Final[str] = "RANK_POINTS_25_MINUS_RANK"
DEPRECATED_R1_WALLET_POINTS_FORMULA: Final[str] = "PENDING_ORGANIZER_DECISION"

# ==============================================================================
# 3. ROUND 2 — CABO TOURNAMENT
# ==============================================================================
# Cabo Table Scoring: 5 players per table, 1 player per team per table.
# Points awarded per table placement:
#   1st = 5 pts
#   2nd = 3 pts
#   3rd = 2 pts
#   4th = 1 pt
#   5th = 0 pts
CABO_PLACEMENT_POINTS: Final[Dict[int, int]] = {
    1: 5,
    2: 3,
    3: 2,
    4: 1,
    5: 0,
}

CABO_GAMES: Final[int] = 3           # Exactly 3 Cabo games
CABO_TABLE_SIZE: Final[int] = 5      # 5 players per table
CABO_MAX_TEAM_SCORE: Final[int] = 75 # 5 players * 5 max pts * 3 games = 75 max points

# Deprecated legacy scales (retained for backward compatibility with legacy tests)
DEPRECATED_CABO_24_POINT_SCALE: Final[Dict[str, int]] = {str(i): 25 - i for i in range(1, 25)}
DEPRECATED_CABO_100_POINT_SCALE: Final[List[int]] = [100, 80, 65, 55, 45, 35, 25, 20, 15, 10, 5, 0]

# ==============================================================================
# 4. ROUND 3 — THE BLACK MARKET & WALLET ECONOMY
# ==============================================================================
# Unified tournament wallet starting balance: 1000 points
STARTING_WALLET_BALANCE: Final[float] = 1000.0

# Deprecated demo starting balance
DEPRECATED_R3_STARTING_BALANCE: Final[float] = 100.0

# ODDyssey Section 5, Market Catalogue. Six items, not four - the case-theme
# hint was missing entirely, and the fragment was priced at 400 rather than 350.
BLACK_MARKET_SUGGESTED_PRICES: Final[Dict[str, float]] = {
    "missing_code_fragment": 350.0,
    "extra_prep_time": 200.0,
    "extra_witness_question": 150.0,
    "agent_intel": 250.0,
    "case_theme_hint": 200.0,
}

# ODDyssey Section 2: "Each missing fragment costs 350 points in the Black
# Market" and "Teams may purchase more than one missing fragment."
BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED: Final[float] = 350.0
BLACK_MARKET_PREP_PRICE_SUGGESTED: Final[float] = 200.0
BLACK_MARKET_WITNESS_PRICE_SUGGESTED: Final[float] = 150.0
BLACK_MARKET_AGENT_INTEL_PRICE_SUGGESTED: Final[float] = 250.0
# ODDyssey Section 5 adds a sixth item: "Case-theme hint, 200 points,
# 4 available, Reveals one important issue in the legal case."
BLACK_MARKET_CASE_HINT_PRICE_SUGGESTED: Final[float] = 200.0

# ODDyssey Section 5 limits stock. The market catalogue is not unlimited, so a
# rich team cannot simply buy every advantage on the board.
BLACK_MARKET_STOCK: Final[Dict[str, Optional[int]]] = {
    "MISSING_CODE_FRAGMENT": None,   # "As required"
    "EXTRA_PREP_TIME": 4,
    "EXTRA_WITNESS_QUESTION": 8,
    "AGENT_INTEL": 5,
    "CASE_THEME_HINT": 4,
}

# "Points cannot be transferred." (ODDyssey Section 5, Black Market Rules)
# Also: purchases cannot be cancelled, advantages cannot be exchanged, and
# teams cannot buy more points.
ALLOW_POINT_TRANSFERS: Final[bool] = False

# "Every transaction requires two organiser signatures." (Section 5, Black
# Market Rules; Rulebook Section 5: "Every purchase needs two organisers to
# sign off on it.") Only the acting organiser was recorded, so a single person
# could move a squad's points with nothing in the ledger showing who else
# authorised it. Enforced at the API, where a real organiser acts; internal
# service calls and seeding are unaffected.
REQUIRE_BLACK_MARKET_DUAL_SIGNATURE: Final[bool] = True

# ==============================================================================
# 5. PASSIVE TRACK: CODE FRAGMENTS & FINAL CODE GATE
# ==============================================================================
# ODDyssey Section 2: the complete secret code is ODD - 42 - ECHO - PRIME, so
# FOUR fragments, two from each of the first two rounds:
#
#   ODD    Round 1, The Signal Scramble  (odd-seat message)
#   42     Round 1, The Route Riddle     (coordinate (7,4), map point 42)
#   ECHO   Round 2, marked Cabo cards    (E, C, HO across the three games)
#   PRIME  Round 2, Prime Number Challenge
#
# NOTE FOR ANYONE READING THE HISTORY: this was 4, was changed to 2 against an
# earlier event document, and is 4 again under the ODDyssey plan. The ODDyssey
# plan is the current specification.
CODE_FRAGMENT_COUNT: Final[int] = 4

CODE_FRAGMENTS: Final[Dict[str, str]] = {
    "ODD": "Round 1, The Signal Scramble",
    "42": "Round 1, The Route Riddle",
    "ECHO": "Round 2, marked Cabo cards",
    "PRIME": "Round 2, Prime Number Challenge",
}
COMPLETE_SECRET_CODE: Final[str] = "ODD-42-ECHO-PRIME"

# "A team must hold all four fragments after the Black Market to qualify for
# Round 4" and "A team without the complete code after the market is
# eliminated."
FINAL_CODE_REQUIRED_FOR_R4: Final[bool] = True

# Superseded two-fragment scheme, kept only as a marker of the old value.
DEPRECATED_R3_FRAGMENT_COUNT: Final[int] = 2

# ==============================================================================
# 6. PASSIVE TRACK: UNDERCOVER SECRET AGENTS
# ==============================================================================
AGENT_TASK_REWARD: Final[float] = 50.0   # +50 pts awarded per verified secret sabotage/task

# ODDyssey Section 7: "Give every agent two tasks during the event. Each
# successfully verified task earns 50 points." Two tasks is the agent track's
# entire contribution to the economy - 100 points at most - and nothing capped
# it, so tasks could be handed out indefinitely and mint points the Black
# Market is explicitly forbidden to sell ("Teams cannot buy more points").
# Organisers can still exceed the cap deliberately; they cannot do it by
# accident.
AGENT_TASKS_PER_AGENT: Final[int] = 2
AGENT_MAX_TASK_POINTS: Final[float] = AGENT_TASKS_PER_AGENT * AGENT_TASK_REWARD

PENALTY_MIN: Final[float] = -50.0        # Rule infraction / misconduct minimum penalty
PENALTY_MAX: Final[float] = -200.0       # Rule infraction / misconduct maximum penalty

# ==============================================================================
# 7. ROUND 4 — THE LEGAL BATTLE (100-POINT JUDGING RUBRIC)
# ==============================================================================
R4_RUBRIC_LOGICAL_STRUCTURE_MAX: Final[float] = 20.0
R4_RUBRIC_EVIDENCE_MAX: Final[float] = 20.0
R4_RUBRIC_REBUTTAL_MAX: Final[float] = 20.0
R4_RUBRIC_RESOURCE_PERSON_MAX: Final[float] = 15.0
R4_RUBRIC_PRESENTATION_TEAMWORK_MAX: Final[float] = 15.0
R4_RUBRIC_TIME_MAX: Final[float] = 10.0
R4_RUBRIC_TOTAL_MAX: Final[float] = 100.0

R4_RUBRIC_LIMITS: Final[Dict[str, float]] = {
    "logical_structure": 20.0,
    "evidence": 20.0,
    "rebuttal": 20.0,
    "resource_person_questioning": 15.0,
    "presentation_teamwork": 15.0,
    "time": 10.0,
}

# ==============================================================================
# 8. ROUND 4 & FINALE — AGENT UNMASKING & CARRYOVER
# ==============================================================================
AGENT_GUESS_MIN: Final[int] = 1          # Min guesses allowed per team
AGENT_GUESS_MAX: Final[int] = 5          # Max guesses allowed per team
AGENT_CORRECT_GUESS: Final[float] = 30.0 # +30 pts per correct agent identification
AGENT_WRONG_GUESS: Final[float] = -20.0  # -20 pts penalty per false agent accusation

# Deprecated legacy single-verdict scores
DEPRECATED_AGENT_CORRECT_BONUS: Final[float] = 10.0
DEPRECATED_AGENT_WRONG_PENALTY: Final[float] = -5.0

# ODDyssey Final Event Plan, Section 1, and Rulebook Section 8:
#   "Final Score = Legal Battle score + Agent-guessing score
#    + Points remaining after the Black Market"
#
# The remaining balance carries in FULL. The 10% weight came from the older
# Event Documentation, where it was explicitly an unresolved organiser
# decision; neither ODDyssey document mentions a percentage. At 10% a squad
# finishing on 900 points contributed 90, so the entire Black Market economy -
# every earn, every purchase, every sealed bid - was worth less than one
# Legal Battle rubric category.
FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED: Final[float] = 1.0
DEFAULT_CARRYOVER_WEIGHT_PERCENT: Final[float] = 100.0

# Superseded weights, kept only as markers of the old values.
DEPRECATED_CARRYOVER_WEIGHT: Final[float] = 0.10
DEPRECATED_ZERO_CARRYOVER_WEIGHT: Final[float] = 0.0
