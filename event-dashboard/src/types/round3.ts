export type BlackMarketTransactionType = 'earn' | 'spend' | 'adjustment' | 'reversal';

export type BlackMarketRankingMetric = 'current_balance' | 'total_earned' | 'net_profit';

export type BlackMarketScoringDirection = 'higher_is_better' | 'lower_is_better';

export interface BlackMarketTransaction {
  id: string;
  teamId: string;
  amount: number; // positive number; type determines credit vs debit
  type: BlackMarketTransactionType;
  reason: string;
  organizerRef?: string; // Operator / marshal name or ID
  timestamp: string;
  isReversed?: boolean;
  reversalTransactionId?: string; // ID of the compensating reversal transaction
  reversedTransactionId?: string; // If this IS a reversal, points to target transaction
  notes?: string;
}

export interface TeamLedger {
  teamId: string;
  openingBalance: number;
  totalEarned: number;
  totalSpent: number;
  netAdjustments: number;
  currentBalance: number;
  activeTransactionCount: number;
  reversalCount: number;
  transactions: BlackMarketTransaction[];
}

export interface HiddenCodeFragmentRecord {
  fragmentIndex: number; // e.g. 1, 2, 3...
  recoveredAt: string;
  recoveredBy?: string; // Marshal or organizer reference
  notes?: string;
}

export interface TeamCodeRecord {
  teamId: string;
  fragments: HiddenCodeFragmentRecord[];
  isComplete: boolean;
  verifiedAt?: string | null;
  verifiedBy?: string | null;
}

export interface HiddenCodeConfig {
  isRequiredForQualification: boolean; // Configurable: Is code completion required to advance?
  requiredFragmentCount: number | null; // null = "Requirements not configured"
  isConfigured: boolean;                // Flag: True once organizers officially confirm requirements
  instructionsNote?: string;
}

export interface BlackMarketConfig {
  startingBalance: number;                       // Demo default (e.g. 100), configurable
  allowNegativeBalance: boolean;                  // Configurable: disallow spend exceeding balance
  rankingMetric: BlackMarketRankingMetric;       // Configurable: current_balance | total_earned | net_profit
  scoringDirection: BlackMarketScoringDirection; // Configurable: higher_is_better (default) | lower_is_better
  isScoringConfigured: boolean;                  // Flag: True once organizers confirm scoring rules
  hiddenCodeConfig: HiddenCodeConfig;
  isFinalized: boolean;                          // Has qualification to Round 4 been finalized?
  finalizedAt?: string | null;
}

export type Round3QualificationStatus =
  | 'Round 2 Pending'         // Round 2 is not yet officially finalized
  | 'Standings Provisional'   // Scoring rules or field results unconfirmed
  | 'Provisional Top 8'       // Currently in top 8 (qualifying zone)
  | 'Provisional Cutoff'      // Outside top 8 (Ranks 9-12 elimination zone)
  | 'Code Incomplete'         // Top 8 by balance, but missing mandatory code completion
  | 'Tie Review Needed'       // Unresolved tie spanning across the 8th-place cutoff boundary
  | 'Finalized Qualified'     // Officially advancing to Round 4: The Legal Battle
  | 'Finalized Eliminated';    // Officially eliminated from advancing to Round 4

export interface TeamRound3Record {
  teamId: string;
  teamNumber: number;
  teamName: string;
  round2Qualified: boolean;
  ledger: TeamLedger;
  codeRecord: TeamCodeRecord;
  rank?: number | null;        // 1 to 12
  tieRequiresReview?: boolean; // True if tie spans across 8th-place cutoff
  tieReason?: string;
  qualificationStatus: Round3QualificationStatus;
}

export interface Round3SummaryStats {
  round2Finalized: boolean;
  round2EligibleTeamsCount: number; // 12 expected
  participatingCount: number;       // 12 squads
  totalTransactionsCount: number;
  totalVolumeTransacted: number;
  codeCompletedCount: number;
  codeConfigured: boolean;
  provisionalTop8Count: number;
  provisionalEliminatedCount: number;
  tiesAffectingCutoffCount: number;
  isScoringConfigured: boolean;
  isFinalized: boolean;
}

export interface Round3EngineResult {
  records: TeamRound3Record[];
  canFinalize: boolean;
  blockReason?: string | null;
  tiesAffectingCutoff: boolean;
  top8TeamIds: string[];
  eliminatedTeamIds: string[];
}

export interface Round3Data {
  config: BlackMarketConfig;
  transactions: BlackMarketTransaction[];
  codeRecords: Record<string, TeamCodeRecord>;
  records: TeamRound3Record[];
  stats: Round3SummaryStats;
  engine: Round3EngineResult;
  round2Finalized: boolean;
  round2QualifiedTeamsCount: number;
}
