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

R1_QUALIFIERS: Final[int] = 16       # Top 16 squads advance from Round 1 to Round 2 (The ODDyssey Protocol)
R2_QUALIFIERS: Final[int] = 12       # Top 12 squads advance from Round 2 to Round 3 (The Black Market)
R3_QUALIFIERS: Final[int] = 6        # Top 6 squads advance from Round 3 to Round 4
R4_FINALISTS: Final[int] = 6         # 6 finalist squads participate in Round 4 (3 head-to-head matchups)
R4_PAIRS: Final[int] = 3             # Exactly 3 courtroom matchups in Round 4
R4_MAX_SCORE: Final[float] = 100.0   # Maximum Legal Battle judging score
R4_ADVANCING_COUNT: Final[int] = 1   # Final winner / champion
PODIUM_SIZE: Final[int] = 3          # Champion, 1st Runner Up, 2nd Runner Up

# ==============================================================================
# 2. ROUND 1 — THE ODDYSSEY PROTOCOL
# ==============================================================================
ROUND_1_NAME: Final[str] = "The ODDyssey Protocol"
ROUND_1_CODENAME: Final[str] = "ROUND_1_ODDYSSEY_PROTOCOL"

# Penalties in seconds added to raw gate time:
#   Hint: +5 minutes (+300s)
#   Unauthorised phone use: +10 minutes (+600s)
#   Team members separating: +5 minutes (+300s)
DEFAULT_R1_HINT_PENALTY_SECONDS: Final[int] = 300
DEFAULT_R1_PHONE_PENALTY_SECONDS: Final[int] = 600
DEFAULT_R1_SEPARATION_PENALTY_SECONDS: Final[int] = 300
DEFAULT_R1_CLUE_DAMAGE_DEDUCTION_POINTS: Final[float] = 20.0  # -20 points deduction or DQ

DEFAULT_R1_CHECKPOINTS: Final[List[str]] = [
    "GATE 42",
    "Map Point J",
    "Lock 48 / Stationary",
]

# Gate Names
GATE_1_NAME: Final[str] = "Gate 1 — The Signal Scramble"
GATE_2_NAME: Final[str] = "Gate 2 — The Route Riddle"
GATE_3_NAME: Final[str] = "Gate 3 — The Logic Lockdown"

# Round 1 Rank Points: 1st=16, 2nd=15 ... 16th=1, 17th+=0
R1_RANK_POINTS_MAP: Final[Dict[int, int]] = {i: 17 - i for i in range(1, 17)}

# Round 1 Code Fragments
R1_FRAGMENT_1_VALUE: Final[str] = "ODD"
R1_FRAGMENT_2_VALUE: Final[str] = "42"

# Round 1 8 Physical Locations (1-indexed internal LOCATION_1 .. LOCATION_8)
R1_LOCATIONS: Final[Dict[int, Dict[str, str]]] = {
    1: {
        "id": "LOCATION_1",
        "location_number": 1,
        "name": "Location 1 — Campus Border Gate",
        "riddle": "Walk toward the place where every campus day eventually ends — the border where students step out and the city begins. Vehicles often wait nearby for their next journey.",
        "target": "Find the metal plate where: S = The Silicon State of India, A = 100/2, L = The abbreviation for Extended Play, N = (17×100)+35",
    },
    2: {
        "id": "LOCATION_2",
        "location_number": 2,
        "name": "Location 2 — Roasted Bean Trail",
        "riddle": "Follow the familiar trail where tired students wander between classes, guided by the aroma of roasted beans and the promise of caffeine.",
        "target": "Find the metal plate where: S = The Silicon State, A = √4, L1 = The 11th letter of the alphabet, L2 = The 11th letter of the alphabet, N = 80² + 26",
    },
    3: {
        "id": "LOCATION_3",
        "location_number": 3,
        "name": "Location 3 — Newton's Domain",
        "riddle": "Where gravity, light, and electricity are not just observed but calculated. A place where falling apples inspire formulas, and waves travel through wires and lenses. Seek the domain where Newton’s curiosity would feel at home.",
        "target": "Domain of Physics and calculated formulas.",
    },
    4: {
        "id": "LOCATION_4",
        "location_number": 4,
        "name": "Location 4 — The Bakery of Logic",
        "riddle": "Here, heat transforms dough and patience turns sugar into delight. Yeast quietly performs its own chemistry, while aromas replace equations. Follow the scent of freshly baked logic.",
        "target": "Follow the scent of freshly baked logic.",
    },
    5: {
        "id": "LOCATION_5",
        "location_number": 5,
        "name": "Location 5 — The Morning Hut",
        "riddle": "Before lectures awaken minds, this humble refuge awakens people. Water boils, beans surrender their strength, and tired students rediscover energy. Seek the rustic hut that powers the campus mornings.",
        "target": "Seek the rustic hut that powers the campus mornings.",
    },
    6: {
        "id": "LOCATION_6",
        "location_number": 6,
        "name": "Location 6 — Words in Stone",
        "riddle": "Some knowledge is written in books, but here it is carved to last far longer. Seek the words that cannot be moved, resting in stone near the dreamers who design skylines.",
        "target": "Words carved in stone near the designers of skylines.",
    },
    7: {
        "id": "LOCATION_7",
        "location_number": 7,
        "name": "Location 7 — Block ARM & Dimension Room",
        "riddle": "Take the letters that appear immediately after A, R, and M in the alphabet. Think of the dimensions we inhabit, add a zero, and then repeat the same number of dimensions once more.",
        "target": "Block: Letters immediately after A, R, M. Room: Dimensions we inhabit + 0 + dimensions repeated.",
    },
    8: {
        "id": "LOCATION_8",
        "location_number": 8,
        "name": "Location 8 — Discovery Chamber",
        "riddle": "Seek the place where experiments either explode with excitement or quietly bloom with discovery. The exact number of bones in the adult human body will guide you.",
        "target": "Block: Discovery experiments. Room: Number of bones in the adult human body (206).",
    },
}

R1_DEFAULT_TEAM_IDS: Final[List[str]] = [str(1000 + i) for i in range(1, 33)]
R1_QUESTION_SETS: Final[List[str]] = ["A", "B", "C", "D"]
R1_MAX_ATTEMPTS_PER_CHECKPOINT: Final[int] = 3

# ==============================================================================
# 3. ROUND 2 — CABO: THE MEMORY HEIST
# ==============================================================================
ROUND_2_NAME: Final[str] = "Cabo - The Memory Heist"
ROUND_2_CODENAME: Final[str] = "ROUND_2_CABO_THE_MEMORY_HEIST"

# Cabo Table Scoring: 5 players per table, 1 player per team per table.
# 16 teams enter -> 16 tables per game.
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
CABO_TABLES: Final[int] = 16         # 16 tables (16 squads * 5 players = 80 participants)
CABO_TABLE_SIZE: Final[int] = 5      # 5 players per table
CABO_MAX_TEAM_SCORE: Final[int] = 75 # 5 players * 5 max pts * 3 games = 75 max points

# Round 2 Code Fragments & Challenge Constants
R2_FRAGMENT_1_VALUE: Final[str] = "ECHO"
R2_FRAGMENT_2_VALUE: Final[str] = "PRIME"
PRIME_SEQUENCE: Final[List[int]] = [2, 3, 5, 7, 11]
PRIME_LETTER_MAP: Final[Dict[int, str]] = {2: "P", 3: "R", 5: "I", 7: "M", 11: "E"}

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
# The 4 official items available in the Black Market:
# 1. Secret Code Item 1
# 2. Secret Code Item 2 (Item 1 + Item 2 form the required key for qualification)
# 3. Powerup 1 for Round 4
# 4. Powerup 2 for Round 4 (carried forward into Round 4)
BLACK_MARKET_SUGGESTED_PRICES: Final[Dict[str, float]] = {
    "secret_code_item_1": 350.0,
    "secret_code_item_2": 350.0,
    "powerup_1_r4": 200.0,
    "powerup_2_r4": 200.0,
    "missing_code_fragment": 400.0,  # Legacy alias
    "extra_prep_time": 200.0,        # Legacy alias
    "extra_witness_question": 150.0, # Legacy alias
    "agent_intel": 250.0,            # Legacy alias
}

BLACK_MARKET_SECRET_CODE_1_PRICE_SUGGESTED: Final[float] = 350.0
BLACK_MARKET_SECRET_CODE_2_PRICE_SUGGESTED: Final[float] = 350.0
BLACK_MARKET_POWERUP_1_PRICE_SUGGESTED: Final[float] = 200.0
BLACK_MARKET_POWERUP_2_PRICE_SUGGESTED: Final[float] = 200.0

BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED: Final[float] = 400.0
BLACK_MARKET_PREP_PRICE_SUGGESTED: Final[float] = 200.0
BLACK_MARKET_WITNESS_PRICE_SUGGESTED: Final[float] = 150.0
BLACK_MARKET_AGENT_INTEL_PRICE_SUGGESTED: Final[float] = 250.0

# ==============================================================================
# 5. PASSIVE TRACK: CODE FRAGMENTS & FINAL CODE GATE
# ==============================================================================
# The 4-fragment code across Round 1 & Round 2 (ODD, 42, ECHO, PRIME):
#   Fragment #1 ('ODD'): recovered in Round 1, Gate 1
#   Fragment #2 ('42'):  recovered in Round 1, Gate 2
#   Fragment #3 ('ECHO'): recovered in Round 2, Cabo (marked cards)
#   Fragment #4 ('PRIME'): recovered in Round 2, Cabo (prime challenge)
CODE_FRAGMENT_COUNT: Final[int] = 4
CODE_FRAGMENTS: Final[List[str]] = ["ODD", "42", "ECHO", "PRIME"]
FINAL_CODE_REQUIRED_FOR_R4: Final[bool] = True
MISSING_FRAGMENT_PENALTY: Final[float] = -350.0  # -350 points per missing fragment penalty

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
AGENT_NO_GUESS: Final[float] = 0.0       # 0 pts if no guess

# Deprecated legacy single-verdict scores
DEPRECATED_AGENT_CORRECT_BONUS: Final[float] = 10.0
DEPRECATED_AGENT_WRONG_PENALTY: Final[float] = -5.0

# ORGANIZER DECISION #3: Black Market Carryover Weight into Finale
# Documented as suggested 10%; organizers may adjust.
FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED: Final[float] = 0.10
DEFAULT_CARRYOVER_WEIGHT_PERCENT: Final[float] = 10.0
DEPRECATED_CARRYOVER_WEIGHT: Final[float] = 0.0
