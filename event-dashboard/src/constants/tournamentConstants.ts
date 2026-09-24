/**
 * EVENT HQ — Authoritative Tournament Constants & Rules Specification
 * Source of Truth: Authoritative Event Documentation (Reconciled in Step 6B)
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
export const DEFAULT_R1_HINT_PENALTY_SECONDS = 120; // 2 minutes penalty per hint (configurable)
export const DEFAULT_R1_CHECKPOINTS = [
  'Checkpoint Alpha',
  'Checkpoint Bravo',
  'Checkpoint Charlie',
] as const;

// ORGANIZER DECISION #1: R1 Expedition Time-to-Wallet-Points conversion formula
// Unresolved in official documentation. Explicitly marked as pending organizer decision.
export const R1_WALLET_POINTS_FORMULA = 'PENDING_ORGANIZER_DECISION';

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

// ORGANIZER DECISION #2: Black Market suggested item prices
// Suggested guidelines; organizers may adjust live.
export const BLACK_MARKET_SUGGESTED_PRICES = {
  missing_code_fragment: 400,
  extra_prep_time: 200,
  extra_witness_question: 150,
  agent_intel: 250,
} as const;

export const BLACK_MARKET_FRAGMENT_PRICE_SUGGESTED = 400;
export const BLACK_MARKET_PREP_PRICE_SUGGESTED = 200;
export const BLACK_MARKET_WITNESS_PRICE_SUGGESTED = 150;
export const BLACK_MARKET_AGENT_INTEL_PRICE_SUGGESTED = 250;

// ==============================================================================
// 5. PASSIVE TRACK: CODE FRAGMENTS & FINAL CODE GATE
// ==============================================================================
// Exactly 2 physical/QR code fragments across tournament:
//   Fragment #1 recovered in Round 1 (Expedition)
//   Fragment #2 recovered in Round 2 (Cabo)
export const CODE_FRAGMENT_COUNT = 2;

// Both fragments required to assemble Final Code for Round 4 access
export const FINAL_CODE_REQUIRED_FOR_R4 = true;

// Deprecated 4-fragment hunt
export const DEPRECATED_R3_FRAGMENT_COUNT = 4;

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

// ORGANIZER DECISION #3: Black Market Carryover Weight into Finale
export const FINAL_SCORE_CARRYOVER_WEIGHT_SUGGESTED = 0.10;
export const DEFAULT_CARRYOVER_WEIGHT_PERCENT = 10;
export const DEPRECATED_CARRYOVER_WEIGHT = 0.0;
