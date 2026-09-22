import {
  CaboConfig,
  CaboGameRecord,
  TeamRound2Record,
  Round2SummaryStats,
  Round2EngineResult,
} from '../types/round2';

/**
 * Creates the demo default placement-point table (1st: 24 pts, ..., 24th: 1 pt).
 * Clearly marked as an unconfirmed demo default.
 */
export function createDefaultPointTable(): Record<number, number> {
  const table: Record<number, number> = {};
  for (let i = 1; i <= 24; i++) {
    table[i] = 25 - i; // 1st -> 24 pts, 24th -> 1 pt
  }
  return table;
}

export const DEFAULT_CABO_CONFIG: CaboConfig = {
  // DEMO DEFAULT: 'higher_is_better'
  // NOTE: Official scoring direction is unconfirmed by organizers and can be configured.
  scoringDirection: 'higher_is_better',
  tiePolicy: 'strict_unique',
  pointTable: createDefaultPointTable(),
  isFinalized: false,
  finalizedAt: null,
};

/**
 * Validates point table configuration.
 * All 24 placements must have a defined non-negative number.
 */
export function isPointTableValid(pointTable: Record<number, number>): boolean {
  if (!pointTable || typeof pointTable !== 'object') return false;
  for (let i = 1; i <= 24; i++) {
    const val = pointTable[i];
    if (typeof val !== 'number' || isNaN(val) || val < 0) {
      return false;
    }
  }
  return true;
}

/**
 * Computes individual team game points and total points.
 * Rule: Only teams with valid results in ALL three games receive a complete total.
 * NEVER treat missing results as zero points.
 */
export function computeTeamRound2Points(
  teamId: string,
  teamNumber: number,
  teamName: string,
  round1Qualified: boolean,
  games: [CaboGameRecord, CaboGameRecord, CaboGameRecord],
  pointTable: Record<number, number>
): TeamRound2Record {
  const g1 = games[0].placements[teamId];
  const g2 = games[1].placements[teamId];
  const g3 = games[2].placements[teamId];

  const g1Placement = g1?.placement ?? null;
  const g2Placement = g2?.placement ?? null;
  const g3Placement = g3?.placement ?? null;

  const g1Points = g1Placement !== null && pointTable[g1Placement] !== undefined ? pointTable[g1Placement] : null;
  const g2Points = g2Placement !== null && pointTable[g2Placement] !== undefined ? pointTable[g2Placement] : null;
  const g3Points = g3Placement !== null && pointTable[g3Placement] !== undefined ? pointTable[g3Placement] : null;

  let gamesCompletedCount = 0;
  if (g1Placement !== null) gamesCompletedCount++;
  if (g2Placement !== null) gamesCompletedCount++;
  if (g3Placement !== null) gamesCompletedCount++;

  const isComplete = gamesCompletedCount === 3;
  const totalPoints = isComplete && g1Points !== null && g2Points !== null && g3Points !== null
    ? g1Points + g2Points + g3Points
    : null;

  return {
    teamId,
    teamNumber,
    teamName,
    round1Qualified,
    game1Placement: g1Placement,
    game1Points: g1Points,
    game2Placement: g2Placement,
    game2Points: g2Points,
    game3Placement: g3Placement,
    game3Points: g3Points,
    totalPoints,
    gamesCompletedCount,
    isComplete,
    rank: null,
    tieRequiresReview: false,
    qualificationStatus: isComplete ? 'Provisional Cutoff' : 'Incomplete',
  };
}

/**
 * Computes Round 2 standings, ranks, and cutoff tie reviews.
 * Does NOT invent arbitrary tie-breakers. Flags ties affecting the 12th-place cutoff.
 */
export function processRound2Standings(
  records: TeamRound2Record[],
  config: CaboConfig,
  round1Finalized: boolean
): Round2EngineResult {
  const isHigherBetter = config.scoringDirection === 'higher_is_better';

  // Separate complete vs incomplete records
  const completeRecords = records.filter((r) => r.isComplete && r.totalPoints !== null);
  const incompleteRecords = records.filter((r) => !r.isComplete || r.totalPoints === null);

  // Sort complete records strictly by total points based on scoring direction
  completeRecords.sort((a, b) => {
    const ptsA = a.totalPoints!;
    const ptsB = b.totalPoints!;
    if (isHigherBetter) {
      if (ptsB !== ptsA) return ptsB - ptsA;
    } else {
      if (ptsA !== ptsB) return ptsA - ptsB;
    }
    // Stable secondary sort by team number without treating as an official competitive tie-breaker
    return a.teamNumber - b.teamNumber;
  });

  // Assign ranks and detect ties
  // Groups of identical total points
  const pointGroups = new Map<number, TeamRound2Record[]>();
  completeRecords.forEach((rec) => {
    const pts = rec.totalPoints!;
    if (!pointGroups.has(pts)) {
      pointGroups.set(pts, []);
    }
    pointGroups.get(pts)!.push(rec);
  });

  let currentRank = 1;
  let tiesAffectingCutoff = false;

  completeRecords.forEach((rec) => {
    rec.rank = currentRank++;
  });

  // Check for ties and specifically check if any tie spans across the 12th-place qualification cutoff!
  // The cutoff is between Rank 12 (qualifies for Round 3) and Rank 13 (eliminated).
  pointGroups.forEach((group, pts) => {
    if (group.length > 1) {
      const ranks = group.map((r) => r.rank!);
      const minRank = Math.min(...ranks);
      const maxRank = Math.max(...ranks);

      // A tie affects the cutoff if the group contains rank <= 12 AND rank > 12!
      const spansCutoff = minRank <= 12 && maxRank >= 13;

      group.forEach((rec) => {
        if (spansCutoff) {
          rec.tieRequiresReview = true;
          rec.tieReason = `Tied on ${pts} total points spanning the 12th-place cutoff (Ranks #${minRank}–#${maxRank}). Official tournament rules require manual marshal review.`;
          tiesAffectingCutoff = true;
        } else if (maxRank <= 12) {
          rec.tieReason = `Tied on ${pts} total points with ${group.length - 1} other team(s) inside the Top 12.`;
        } else {
          rec.tieReason = `Tied on ${pts} total points with ${group.length - 1} other team(s) in the elimination zone.`;
        }
      });
    }
  });

  // Assign qualification status
  completeRecords.forEach((rec) => {
    if (!round1Finalized) {
      rec.qualificationStatus = 'Round 1 Pending';
    } else if (config.isFinalized) {
      rec.qualificationStatus = rec.rank! <= 12 ? 'Finalized Qualified' : 'Finalized Eliminated';
    } else if (rec.tieRequiresReview) {
      rec.qualificationStatus = 'Tie Review Needed';
    } else if (rec.rank! <= 12) {
      rec.qualificationStatus = 'Provisional Top 12';
    } else {
      rec.qualificationStatus = 'Provisional Cutoff';
    }
  });

  incompleteRecords.forEach((rec) => {
    rec.rank = null;
    rec.tieRequiresReview = false;
    rec.qualificationStatus = !round1Finalized ? 'Round 1 Pending' : 'Incomplete';
  });

  const finalRecords = [...completeRecords, ...incompleteRecords];

  // Determine whether finalization is allowed
  let canFinalize = true;
  let blockReason: string | null = null;

  if (!round1Finalized) {
    canFinalize = false;
    blockReason = 'Round 1 results are not yet officially finalized. Finalize Round 1 first.';
  } else if (records.length !== 24) {
    canFinalize = false;
    blockReason = `Expected exactly 24 qualified teams from Round 1, but found ${records.length}.`;
  } else if (incompleteRecords.length > 0) {
    canFinalize = false;
    blockReason = `${incompleteRecords.length} squad(s) have incomplete Cabo game results. All 3 games must be recorded for all 24 squads.`;
  } else if (!isPointTableValid(config.pointTable)) {
    canFinalize = false;
    blockReason = 'Placement points table is incomplete or invalid. All 24 placements must have valid non-negative points.';
  } else if (tiesAffectingCutoff) {
    canFinalize = false;
    blockReason = 'An unresolved tie affects the 12th-place qualification cutoff boundary. Manual marshal review is required before finalization.';
  }

  const top12TeamIds = completeRecords
    .filter((r) => r.rank !== null && r.rank !== undefined && r.rank <= 12)
    .map((r) => r.teamId);

  const eliminatedTeamIds = completeRecords
    .filter((r) => r.rank !== null && r.rank !== undefined && r.rank > 12)
    .map((r) => r.teamId);

  return {
    records: finalRecords,
    canFinalize,
    blockReason,
    tiesAffectingCutoff,
    top12TeamIds,
    eliminatedTeamIds,
  };
}

/**
 * Computes summary KPI statistics for Round 2 overview.
 */
export function computeRound2SummaryStats(
  records: TeamRound2Record[],
  games: [CaboGameRecord, CaboGameRecord, CaboGameRecord],
  config: CaboConfig,
  round1Finalized: boolean,
  round1QualifiedCount: number
): Round2SummaryStats {
  const g1Count = Object.keys(games[0].placements).length;
  const g2Count = Object.keys(games[1].placements).length;
  const g3Count = Object.keys(games[2].placements).length;

  const completeTeams = records.filter((r) => r.isComplete && r.totalPoints !== null);
  const tiesAffectingCutoffCount = records.filter((r) => r.tieRequiresReview).length;
  const provisionalTop12 = completeRecordsTop12Count(records);
  const provisionalEliminated = records.filter(
    (r) => r.isComplete && r.rank !== null && r.rank !== undefined && r.rank > 12
  ).length;

  return {
    round1Finalized,
    round1EligibleTeamsCount: round1QualifiedCount,
    participatingCount: records.length,
    game1CompletionCount: g1Count,
    game2CompletionCount: g2Count,
    game3CompletionCount: g3Count,
    completeTeamsCount: completeTeams.length,
    provisionalTop12Count: provisionalTop12,
    provisionalEliminatedCount: provisionalEliminated,
    tiesAffectingCutoffCount,
    isConfigComplete: isPointTableValid(config.pointTable),
    isFinalized: config.isFinalized,
  };
}

function completeRecordsTop12Count(records: TeamRound2Record[]): number {
  return records.filter((r) => r.rank !== null && r.rank !== undefined && r.rank <= 12).length;
}
