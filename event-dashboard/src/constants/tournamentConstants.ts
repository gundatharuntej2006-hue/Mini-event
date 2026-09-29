/**
 * EVENT HQ — Authoritative Tournament Constants & Rules Specification
 * Source of Truth: the ODDyssey Event Plan.
 *
 * This module establishes the single canonical source of truth in the frontend for
 * tournament rules, qualification counts, scoring metrics, and economy parameters.
 */

// ==============================================================================
// 1. TOURNAMENT STRUCTURE & ADVANCEMENT
// ==============================================================================
export const MAX_TEAMS = 32;
export const TEAM_SIZE = 5;

export const R1_QUALIFIERS = 24;       // Top 24 squads advance from Round 1 to Round 2
export const R2_QUALIFIERS = 12;       // Top 12 squads advance from Round 2 to Round 3
export const R3_QUALIFIERS = 8;        // Top 8 squads advance from Round 3 to Round 4
export const R4_FINALISTS = 8;         // All 8 finalist squads proceed to Grand Finale assembly
export const PODIUM_SIZE = 3;          // Champion, 1st Runner Up, 2nd Runner Up

// ==============================================================================
// 2. ROUND 1 — THE GREAT EXPEDITION
// ==============================================================================
// Section 4.3, rule 5: a hint "adds a fixed time penalty (e.g. +5 minutes)".
// Five minutes, in seconds. This was 120 (two minutes) here and in the backend,
// which under-penalised every team that took a hint by three minutes - and
// Round 1 is ranked on adjusted total time, so it changed who reached Round 2.
export const DEFAULT_R1_HINT_PENALTY_SECONDS = 300;
export const DEFAULT_R1_CHECKPOINTS = [
  'Checkpoint Alpha',
  'Checkpoint Bravo',
  'Checkpoint Charlie',
] as const;

// ODDyssey Section 4, Round 1 Scoring:
//   "Total time = time spent at gates + hint penalties + rule penalties"
// Only the hint penalty existed. A squad caught using a phone or splitting up
// kept its raw time, and Round 1 decides who reaches Round 2.
export const R1_PENALTY_HINT_SECONDS = 300;             // Using a hint, +5 minutes
export const R1_PENALTY_PHONE_USE_SECONDS = 600;        // Unauthorised phone use, +10 minutes
export const R1_PENALTY_TEAM_SEPARATION_SECONDS = 300;  // Separating from the team, +5 minutes

// "Moving or damaging a clue: -20 points or disqualification." Scored in
// points rather than seconds, and the marshal may escalate to a DQ instead.
export const R1_CLUE_DAMAGE_POINT_PENALTY = -20;

export const R1_RULE_VIOLATIONS = [
  'UNAUTHORISED_PHONE_USE',
  'TEAM_SEPARATION',
  'CLUE_DAMAGE',
] as const;

export const R1_RULE_VIOLATION_LABELS: Record<string, string> = {
  UNAUTHORISED_PHONE_USE: 'Unauthorised phone use (+10 min)',
  TEAM_SEPARATION: 'Team members separating (+5 min)',
  CLUE_DAMAGE: 'Moving or damaging a clue (-20 pts or DQ)',
};

// ODDyssey Section 3 resolves what was organiser decision #1: qualifying teams
// receive rank points, 1st = 24, 2nd = 23, continuing down to 24th = 1.
export const R1_WALLET_POINTS_FORMULA = 'RANK_POINTS_25_MINUS_RANK';
export const r1RankPoints = (rank: number): number => (rank > R1_QUALIFIERS ? 0 : 25 - rank);

// ==============================================================================
// 3. ROUND 2 — CABO TOURNAMENT
// ==============================================================================
// Cabo Table Scoring: 5 players per table, 1 player per team per table.
// Placements per table: 1st = 5 pts, 2nd = 3 pts, 3rd = 2 pts, 4th = 1 pt, 5th = 0 pts.
export const CABO_PLACEMENT_POINTS: Record<number, number> = {
  1: 5,
  2: 3,
  3: 2,
  4: 1,
  5: 0,
};

// ODDyssey Section 4, Cabo Tie-Breakers, in order. The platform computed the
// first three and flagged anything still level "unresolved" with no way to
// resolve it - while an unresolved tie blocks Round 2 finalisation.
export const CABO_TIE_BREAKERS = [
  'Higher team placement score',
  'Lower combined final card total',
  'More first-place finishes',
  'One sudden-death Cabo game with one representative from each tied team',
  'Organiser draw if still tied',
] as const;

// Tie-breakers 4 and 5 are entered by an organiser; the platform never breaks
// a tie at random.
export const CABO_TIE_BREAK_METHODS = ['SUDDEN_DEATH', 'ORGANISER_DRAW'] as const;
export const CABO_TIE_BREAK_METHOD_LABELS: Record<string, string> = {
  SUDDEN_DEATH: 'Sudden-death Cabo game',
  ORGANISER_DRAW: 'Organiser draw',
};

export const CABO_GAMES = 3;           // Exactly 3 Cabo games
export const CABO_TABLE_SIZE = 5;      // 5 players per table
export const CABO_MAX_TEAM_SCORE = 75; // 5 players * 5 max pts * 3 games = 75 max points

// Deprecated legacy 24-point scale (retained for backward compatibility)
export const DEPRECATED_CABO_24_POINT_SCALE: Record<number, number> = Object.fromEntries(
  Array.from({ length: 24 }, (_, i) => [i + 1, 25 - (i + 1)])
);

// ==============================================================================
// 4. ROUND 3 — THE BLACK MARKET & WALLET ECONOMY
// ==============================================================================
// Unified tournament wallet starting balance: 1000 points
export const STARTING_WALLET_BALANCE = 1000;
export const DEPRECATED_R3_STARTING_BALANCE = 100;

// ODDyssey Section 5, Market Catalogue. The case-theme hint was missing
// entirely, and the fragment was priced at 400 rather than 350 - so the market
// screen quoted a price the backend would not charge.
export const BLACK_MARKET_SUGGESTED_PRICES = {
  missing_code_fragment: 350,
  extra_prep_time: 200,
  extra_witness_question: 150,
  agent_intel: 250,
  case_theme_hint: 200,
} as const;

export const BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED = 350;
export const BLACK_MARKET_PREP_PRICE_SUGGESTED = 200;
export const BLACK_MARKET_WITNESS_PRICE_SUGGESTED = 150;
export const BLACK_MARKET_AGENT_INTEL_PRICE_SUGGESTED = 250;
export const BLACK_MARKET_CASE_HINT_PRICE_SUGGESTED = 200;

// ODDyssey Section 5's Quantity column. These are market-wide totals, not
// per-squad allowances; null means "as required", i.e. unlimited. The scarcity
// is what makes the spend-versus-save decision mean anything.
export const BLACK_MARKET_STOCK: Record<string, number | null> = {
  MISSING_CODE_FRAGMENT: null,
  EXTRA_PREP_TIME: 4,
  EXTRA_WITNESS_QUESTION: 8,
  AGENT_INTEL: 5,
  CASE_THEME_HINT: 4,
};

// "Points cannot be transferred." (Section 5, Black Market Rules)
export const ALLOW_POINT_TRANSFERS = false;

// ==============================================================================
// 5. PASSIVE TRACK: CODE FRAGMENTS & FINAL CODE GATE
// ==============================================================================
// ODDyssey Section 2: the complete secret code is ODD - 42 - ECHO - PRIME, so
// FOUR fragments, two from each of the first two rounds. This file said 2,
// which meant the dashboard showed a squad's code complete while the backend
// still held it two fragments short of the Round 4 gate.
export const CODE_FRAGMENT_COUNT = 4;

export const CODE_FRAGMENTS: Record<string, string> = {
  ODD: 'Round 1, The Signal Scramble',
  '42': 'Round 1, The Route Riddle',
  ECHO: 'Round 2, marked Cabo cards',
  PRIME: 'Round 2, Prime Number Challenge',
};
export const COMPLETE_SECRET_CODE = 'ODD-42-ECHO-PRIME';

// "A team must hold all four fragments after the Black Market to qualify for
// Round 4"; a team without the complete code after the market is eliminated.
export const FINAL_CODE_REQUIRED_FOR_R4 = true;

// Superseded two-fragment scheme, kept only as a marker of the old value.
export const DEPRECATED_R3_FRAGMENT_COUNT = 2;

// ==============================================================================
// 6. PASSIVE TRACK: UNDERCOVER SECRET AGENTS
// ==============================================================================
export const AGENT_TASK_REWARD = 50;   // +50 pts awarded per verified secret sabotage/task
export const PENALTY_MIN = -50;        // Rule infraction / misconduct minimum penalty
export const PENALTY_MAX = -200;       // Rule infraction / misconduct maximum penalty

// ==============================================================================
// 7. ROUND 4 & FINALE — AGENT UNMASKING & CARRYOVER
// ==============================================================================
export const AGENT_GUESS_MIN = 1;      // Min guesses allowed per team
export const AGENT_GUESS_MAX = 5;      // Max guesses allowed per team
export const AGENT_CORRECT_GUESS = 30; // +30 pts per correct agent identification
export const AGENT_WRONG_GUESS = -20;  // -20 pts penalty per false agent accusation

// Deprecated legacy single-verdict scores
export const DEPRECATED_AGENT_CORRECT_BONUS = 10;
export const DEPRECATED_AGENT_WRONG_PENALTY = -5;

// ODDyssey Final Event Plan section 1, and Rulebook section 8:
//   "Final Score = Legal Battle score + Agent-guessing score
//    + Points remaining after the Black Market"
// The remaining balance carries in FULL. The 10% weight came from the older
// Event Documentation, where it was an explicitly unresolved organiser
// decision; at 10% a squad finishing on 900 points contributed 90, and the
// whole Black Market economy was nearly decorative next to a 100-point Legal
// Battle score.
export const FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED = 1.0;
export const DEFAULT_CARRYOVER_WEIGHT_PERCENT = 100;

// Superseded weights, kept only as markers of the old values.
export const DEPRECATED_CARRYOVER_WEIGHT = 0.10;
export const DEPRECATED_ZERO_CARRYOVER_WEIGHT = 0.0;
