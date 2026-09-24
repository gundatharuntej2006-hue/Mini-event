"""
EVENT HQ — Authoritative Tournament Constants & Rules Specification
Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B)

This module defines the single canonical source of truth for tournament rules,
advancement cutoffs, scoring points, wallet economy, and agent parameters.

Three specific organizer decisions remain unconfirmed in the authoritative event
documentation and are explicitly marked as configurable or pending:
1. R1 time-to-wallet-points conversion formula (R1_WALLET_POINTS_FORMULA = "PENDING_ORGANIZER_DECISION")
2. Black Market item prices (BLACK_MARKET_SUGGESTED_PRICES: suggested defaults, configurable)
3. Black Market carryover weight into Finale (FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED = 0.10, configurable)
"""

from typing import Dict, Final, List

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

# ORGANIZER DECISION #1: R1 Expedition Time-to-Wallet-Points conversion formula
# Unresolved in official documentation. Explicitly marked as pending organizer decision.
R1_WALLET_POINTS_FORMULA: Final[str] = "PENDING_ORGANIZER_DECISION"

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

# ORGANIZER DECISION #2: Black Market suggested item prices
# These prices are documented as suggested guidelines; organizers may adjust live.
BLACK_MARKET_SUGGESTED_PRICES: Final[Dict[str, float]] = {
    "missing_code_fragment": 400.0,
    "extra_prep_time": 200.0,
    "extra_witness_question": 150.0,
    "agent_intel": 250.0,
}

BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED: Final[float] = 400.0
BLACK_MARKET_PREP_PRICE_SUGGESTED: Final[float] = 200.0
BLACK_MARKET_WITNESS_PRICE_SUGGESTED: Final[float] = 150.0
BLACK_MARKET_AGENT_INTEL_PRICE_SUGGESTED: Final[float] = 250.0

# ==============================================================================
# 5. PASSIVE TRACK: CODE FRAGMENTS & FINAL CODE GATE
# ==============================================================================
# Exactly 2 physical/QR code fragments across the tournament:
#   Fragment #1 recovered in Round 1 (Expedition)
#   Fragment #2 recovered in Round 2 (Cabo)
CODE_FRAGMENT_COUNT: Final[int] = 2

# Both fragments are strictly required to assemble the Final Code to enter Round 4.
# If a team is missing a fragment, they must purchase it at the Black Market.
FINAL_CODE_REQUIRED_FOR_R4: Final[bool] = True

# Deprecated legacy 4-fragment hunt
DEPRECATED_R3_FRAGMENT_COUNT: Final[int] = 4

# ==============================================================================
# 6. PASSIVE TRACK: UNDERCOVER SECRET AGENTS
# ==============================================================================
AGENT_TASK_REWARD: Final[float] = 50.0   # +50 pts awarded per verified secret sabotage/task
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

# ORGANIZER DECISION #3: Black Market Carryover Weight into Finale
# Documented as suggested 10%; organizers may adjust.
FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED: Final[float] = 0.10
DEFAULT_CARRYOVER_WEIGHT_PERCENT: Final[float] = 10.0
DEPRECATED_CARRYOVER_WEIGHT: Final[float] = 0.0
