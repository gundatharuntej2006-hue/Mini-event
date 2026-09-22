import {
  BlackMarketConfig,
  BlackMarketTransaction,
  TeamLedger,
  TeamCodeRecord,
  TeamRound3Record,
  Round3SummaryStats,
  Round3EngineResult,
  BlackMarketRankingMetric,
} from '../types/round3';

export const DEFAULT_ROUND3_CONFIG: BlackMarketConfig = {
  // DEMO DEFAULTS: Unconfirmed rules pending official organizer confirmation
  startingBalance: 100, // Demo Default · Unconfirmed Rule
  allowNegativeBalance: false,
  rankingMetric: 'current_balance', // Demo Default · Unconfirmed Rule
  scoringDirection: 'higher_is_better', // Demo Default · Unconfirmed Rule
  isScoringConfigured: false, // Must be explicitly confirmed by organizers before official finalization
  hiddenCodeConfig: {
    isRequiredForQualification: false,
    requiredFragmentCount: null, // "Requirements not configured"
    isConfigured: false,
    instructionsNote: 'Official fragment requirements pending organizer confirmation.',
  },
  isFinalized: false,
  finalizedAt: null,
};

/**
 * Computes a team's financial ledger from their transaction history.
 * Preserves all transactions (including reversals and reversed entries).
 * Active transactions (!isReversed) calculate the balance.
 */
export function computeTeamLedger(
  teamId: string,
  transactions: BlackMarketTransaction[],
  startingBalance: number
): TeamLedger {
  const teamTx = transactions.filter((t) => t.teamId === teamId);

  let totalEarned = 0;
  let totalSpent = 0;
  let netAdjustments = 0;
  let activeTransactionCount = 0;
  let reversalCount = 0;

  teamTx.forEach((tx) => {
    if (tx.type === 'reversal') {
      reversalCount++;
      return;
    }

    if (tx.isReversed) {
      return; // Reversed transactions do not impact active ledger balances
    }

    activeTransactionCount++;

    if (tx.type === 'earn') {
      totalEarned += tx.amount;
    } else if (tx.type === 'spend') {
      totalSpent += tx.amount;
    } else if (tx.type === 'adjustment') {
      netAdjustments += tx.amount; // Can be positive (credit) or negative (debit)
    }
  });

  const currentBalance = startingBalance + totalEarned - totalSpent + netAdjustments;

  return {
    teamId,
    openingBalance: startingBalance,
    totalEarned,
    totalSpent,
    netAdjustments,
    currentBalance,
    activeTransactionCount,
    reversalCount,
    transactions: teamTx.sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    ),
  };
}

/**
 * Computes the metric value used for ranking.
 */
export function computeRankingMetricValue(
  ledger: TeamLedger,
  metric: BlackMarketRankingMetric
): number {
  switch (metric) {
    case 'current_balance':
      return ledger.currentBalance;
    case 'total_earned':
      return ledger.totalEarned;
    case 'net_profit':
      return ledger.totalEarned - ledger.totalSpent;
    default:
      return ledger.currentBalance;
  }
}

/**
 * Evaluates hidden code completion status for a team.
 * Never silently combines code with score.
 */
export function evaluateTeamCodeStatus(
  codeRecord: TeamCodeRecord | undefined,
  teamId: string,
  config: BlackMarketConfig
): TeamCodeRecord {
  if (!codeRecord) {
    return {
      teamId,
      fragments: [],
      isComplete: false,
      verifiedAt: null,
      verifiedBy: null,
    };
  }

  const { isConfigured, requiredFragmentCount } = config.hiddenCodeConfig;

  let isComplete = false;
  if (isConfigured && requiredFragmentCount !== null && requiredFragmentCount > 0) {
    // Complete if team has recovered at least required count of unique fragments
    const uniqueFragments = new Set(codeRecord.fragments.map((f) => f.fragmentIndex));
    isComplete = uniqueFragments.size >= requiredFragmentCount;
  }

  return {
    ...codeRecord,
    isComplete,
  };
}

/**
 * Standings and qualification engine for Round 3: The Black Market.
 *
 * Rules:
 * - 12 participating teams qualified from Round 2.
 * - Top 8 squads qualify for Round 4: The Legal Battle.
 * - Bottom 4 squads are eliminated. Records preserved, never deleted.
 * - No invented tie-breakers: Ties spanning the 8th-place cutoff boundary strictly block finalization.
 * - Standings remain provisional until organizers officially confirm rules.
 * - Does not silently combine points and code status unless explicitly configured.
 */
export function processRound3Standings(
  records: TeamRound3Record[],
  config: BlackMarketConfig,
  round2Finalized: boolean
): Round3EngineResult {
  const isHigherBetter = config.scoringDirection === 'higher_is_better';

  // Sort teams strictly by the configured ranking metric
  const sortedRecords = [...records].sort((a, b) => {
    const valA = computeRankingMetricValue(a.ledger, config.rankingMetric);
    const valB = computeRankingMetricValue(b.ledger, config.rankingMetric);

    if (isHigherBetter) {
      if (valB !== valA) return valB - valA;
    } else {
      if (valA !== valB) return valA - valB;
    }
    // Stable secondary display sort by team number (NOT an official tournament tie-breaker)
    return a.teamNumber - b.teamNumber;
  });

  // Group teams by ranking metric value to detect ties
  const metricGroups = new Map<number, TeamRound3Record[]>();
  sortedRecords.forEach((rec) => {
    const val = computeRankingMetricValue(rec.ledger, config.rankingMetric);
    if (!metricGroups.has(val)) {
      metricGroups.set(val, []);
    }
    metricGroups.get(val)!.push(rec);
  });

  let currentRank = 1;
  let tiesAffectingCutoff = false;

  sortedRecords.forEach((rec) => {
    rec.rank = currentRank++;
    rec.tieRequiresReview = false;
    rec.tieReason = undefined;
  });

  // Check for ties spanning the 8th-place cutoff boundary
  // Cutoff is between Rank #8 (advancing) and Rank #9 (eliminated)
  metricGroups.forEach((group, metricVal) => {
    if (group.length > 1) {
      const ranks = group.map((r) => r.rank!);
      const minRank = Math.min(...ranks);
      const maxRank = Math.max(...ranks);

      // A tie affects the cutoff if the group contains rank <= 8 AND rank > 8
      const spansCutoff = minRank <= 8 && maxRank >= 9;

      group.forEach((rec) => {
        if (spansCutoff) {
          rec.tieRequiresReview = true;
          rec.tieReason = `Tied on ${metricVal} points spanning the 8th-place cutoff (Ranks #${minRank}–#${maxRank}). Official tournament rules require manual marshal review.`;
          tiesAffectingCutoff = true;
        } else if (maxRank <= 8) {
          rec.tieReason = `Tied on ${metricVal} points with ${group.length - 1} other squad(s) inside the Top 8.`;
        } else {
          rec.tieReason = `Tied on ${metricVal} points with ${group.length - 1} other squad(s) in the elimination zone.`;
        }
      });
    }
  });

  // Assign qualification statuses
  sortedRecords.forEach((rec) => {
    if (!round2Finalized) {
      rec.qualificationStatus = 'Round 2 Pending';
    } else if (config.isFinalized) {
      rec.qualificationStatus = rec.rank! <= 8 ? 'Finalized Qualified' : 'Finalized Eliminated';
    } else if (rec.tieRequiresReview) {
      rec.qualificationStatus = 'Tie Review Needed';
    } else if (config.hiddenCodeConfig.isRequiredForQualification && !rec.codeRecord.isComplete) {
      rec.qualificationStatus = 'Code Incomplete';
    } else if (!config.isScoringConfigured) {
      rec.qualificationStatus = 'Standings Provisional';
    } else if (rec.rank! <= 8) {
      rec.qualificationStatus = 'Provisional Top 8';
    } else {
      rec.qualificationStatus = 'Provisional Cutoff';
    }
  });

  // Determine whether qualification to Round 4 can be finalized
  let canFinalize = true;
  let blockReason: string | null = null;

  if (!round2Finalized) {
    canFinalize = false;
    blockReason = 'Round 2 (Cabo) results are not yet officially finalized. Finalize Round 2 first.';
  } else if (records.length !== 12) {
    canFinalize = false;
    blockReason = `Expected exactly 12 qualified squads from Round 2, but found ${records.length}. Organizer review required.`;
  } else if (!config.isScoringConfigured) {
    canFinalize = false;
    blockReason = 'Scoring and ranking rules have not been officially confirmed by organizers. Review and confirm in Rules & Settings.';
  } else if (tiesAffectingCutoff) {
    canFinalize = false;
    blockReason = 'An unresolved tie affects the 8th-place qualification cutoff boundary. Manual marshal review is required before finalization.';
  } else if (config.hiddenCodeConfig.isRequiredForQualification) {
    if (!config.hiddenCodeConfig.isConfigured || config.hiddenCodeConfig.requiredFragmentCount === null) {
      canFinalize = false;
      blockReason = 'Hidden code completion is set as mandatory for qualification, but official fragment requirements have not been configured.';
    } else {
      const incompleteTop8 = sortedRecords.filter((r) => r.rank! <= 8 && !r.codeRecord.isComplete);
      if (incompleteTop8.length > 0) {
        canFinalize = false;
        blockReason = `${incompleteTop8.length} squad(s) currently in the Top 8 have not satisfied the mandatory hidden code requirement.`;
      }
    }
  }

  const top8TeamIds = sortedRecords
    .filter((r) => r.rank !== null && r.rank !== undefined && r.rank <= 8)
    .map((r) => r.teamId);

  const eliminatedTeamIds = sortedRecords
    .filter((r) => r.rank !== null && r.rank !== undefined && r.rank > 8)
    .map((r) => r.teamId);

  return {
    records: sortedRecords,
    canFinalize,
    blockReason,
    tiesAffectingCutoff,
    top8TeamIds,
    eliminatedTeamIds,
  };
}

/**
 * Computes overview KPI statistics for Round 3.
 */
export function computeRound3SummaryStats(
  records: TeamRound3Record[],
  transactions: BlackMarketTransaction[],
  config: BlackMarketConfig,
  round2Finalized: boolean,
  round2QualifiedCount: number
): Round3SummaryStats {
  const codeCompletedCount = records.filter((r) => r.codeRecord.isComplete).length;
  const tiesAffectingCutoffCount = records.filter((r) => r.tieRequiresReview).length;
  const provisionalTop8Count = records.filter(
    (r) => r.rank !== null && r.rank !== undefined && r.rank <= 8
  ).length;
  const provisionalEliminatedCount = records.filter(
    (r) => r.rank !== null && r.rank !== undefined && r.rank > 8
  ).length;

  let totalVolume = 0;
  transactions.forEach((tx) => {
    if (!tx.isReversed && tx.type !== 'reversal') {
      totalVolume += tx.amount;
    }
  });

  return {
    round2Finalized,
    round2EligibleTeamsCount: round2QualifiedCount,
    participatingCount: records.length,
    totalTransactionsCount: transactions.length,
    totalVolumeTransacted: totalVolume,
    codeCompletedCount,
    codeConfigured: config.hiddenCodeConfig.isConfigured,
    provisionalTop8Count,
    provisionalEliminatedCount,
    tiesAffectingCutoffCount,
    isScoringConfigured: config.isScoringConfigured,
    isFinalized: config.isFinalized,
  };
}
