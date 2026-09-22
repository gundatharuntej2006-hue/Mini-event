export type CaboScoringDirection = 'higher_is_better' | 'lower_is_better';

export type CaboTiePolicy = 'strict_unique' | 'allow_shared';

export interface CaboPlacementPointRule {
  placement: number; // 1 to 24
  points: number;    // Configurable points awarded
}

export interface CaboConfig {
  scoringDirection: CaboScoringDirection; // Configurable: 'higher_is_better' (default) or 'lower_is_better'
  tiePolicy: CaboTiePolicy;               // 'strict_unique' (no duplicates) or 'allow_shared'
  pointTable: Record<number, number>;     // placement (1 to 24) -> points
  isFinalized: boolean;                   // Has qualification to Round 3 been finalized?
  finalizedAt?: string | null;
}

export interface CaboGamePlacement {
  teamId: string;
  placement: number;          // 1 to 24
  points: number;             // Calculated from pointTable
  recordedAt?: string | null;
  notes?: string;
}

export interface CaboGameRecord {
  gameNumber: 1 | 2 | 3;
  name: string;               // e.g. "Cabo Game 1"
  isCompleted: boolean;
  placements: Record<string, CaboGamePlacement>; // teamId -> CaboGamePlacement
}

export type Round2QualificationStatus =
  | 'Round 1 Pending'         // Round 1 is not yet finalized
  | 'Incomplete'              // Missing 1 or more game results
  | 'Provisional Top 12'      // Currently in top 12 provisionally
  | 'Provisional Cutoff'      // Outside top 12 (Rank 13-24)
  | 'Tie Review Needed'       // Unresolved tie affecting the 12th place cutoff
  | 'Finalized Qualified'     // Officially advancing to Round 3: The Black Market
  | 'Finalized Eliminated';    // Officially eliminated from advancing to Round 3

export interface TeamRound2Record {
  teamId: string;
  teamNumber: number;
  teamName: string;
  round1Qualified: boolean;
  game1Placement?: number | null;
  game1Points?: number | null;
  game2Placement?: number | null;
  game2Points?: number | null;
  game3Placement?: number | null;
  game3Points?: number | null;
  totalPoints?: number | null;     // Sum of 3 games ONLY if all 3 are completed
  gamesCompletedCount: number;     // 0, 1, 2, or 3
  isComplete: boolean;             // true if all 3 games have valid placements
  rank?: number | null;            // 1 to 24 (null if incomplete)
  tieRequiresReview?: boolean;     // true if tied on 12th cutoff
  tieReason?: string;
  qualificationStatus: Round2QualificationStatus;
}

export interface Round2SummaryStats {
  round1Finalized: boolean;
  round1EligibleTeamsCount: number; // 24 expected
  participatingCount: number;       // 24 squads
  game1CompletionCount: number;     // Count of teams with Game 1 placement
  game2CompletionCount: number;     // Count of teams with Game 2 placement
  game3CompletionCount: number;     // Count of teams with Game 3 placement
  completeTeamsCount: number;       // Teams with all 3 games completed
  provisionalTop12Count: number;
  provisionalEliminatedCount: number;
  tiesAffectingCutoffCount: number;
  isConfigComplete: boolean;
  isFinalized: boolean;
}

export interface Round2EngineResult {
  records: TeamRound2Record[];
  canFinalize: boolean;
  blockReason?: string | null;
  tiesAffectingCutoff: boolean;
  top12TeamIds: string[];
  eliminatedTeamIds: string[];
}

export interface Round2Data {
  config: CaboConfig;
  games: [CaboGameRecord, CaboGameRecord, CaboGameRecord];
  records: TeamRound2Record[];
  stats: Round2SummaryStats;
  engine: Round2EngineResult;
  round1Finalized: boolean;
  round1QualifiedTeamsCount: number;
}
