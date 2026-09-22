import { TeamRound1Record, MiniRoundTiming } from '../types/round1';

/**
 * Pure calculation logic for a single mini-round.
 * Validates start and completion timestamps.
 */
export function computeMiniRound(
  mr: MiniRoundTiming,
  penaltyPerHintSeconds: number
): MiniRoundTiming {
  const updated: MiniRoundTiming = { ...mr };
  const hints = Math.max(0, updated.hintsUsed || 0);
  updated.hintsUsed = hints;
  updated.hintPenaltySeconds = hints * penaltyPerHintSeconds;

  if (updated.startTime && updated.completionTime) {
    const start = new Date(updated.startTime).getTime();
    const end = new Date(updated.completionTime).getTime();

    if (!isNaN(start) && !isNaN(end) && end >= start) {
      const duration = Math.round((end - start) / 1000);
      updated.durationSeconds = duration;
      updated.adjustedSeconds = duration + updated.hintPenaltySeconds;
      updated.status = 'Completed';
    } else {
      updated.durationSeconds = null;
      updated.adjustedSeconds = null;
      updated.status = 'In Progress';
    }
  } else if (updated.startTime) {
    updated.durationSeconds = null;
    updated.adjustedSeconds = null;
    updated.status = 'In Progress';
  } else {
    updated.durationSeconds = null;
    updated.adjustedSeconds = null;
    updated.status = 'Not Started';
  }

  return updated;
}

/**
 * Computes raw total, penalties, adjusted total, and fastest mini-round for a squad.
 */
export function computeTeamTotals(
  record: TeamRound1Record,
  penaltyPerHintSeconds: number
): TeamRound1Record {
  const updatedMiniRounds = record.miniRounds.map((mr) =>
    computeMiniRound(mr, penaltyPerHintSeconds)
  ) as [MiniRoundTiming, MiniRoundTiming, MiniRoundTiming];

  const allThreeCompleted = updatedMiniRounds.every(
    (mr) =>
      mr.status === 'Completed' &&
      typeof mr.durationSeconds === 'number' &&
      mr.durationSeconds >= 0
  );

  let rawTotalSeconds: number | null = null;
  let totalPenaltySeconds = 0;
  let adjustedTotalSeconds: number | null = null;
  let fastestMiniRoundSeconds: number | null = null;

  totalPenaltySeconds = updatedMiniRounds.reduce(
    (acc, mr) => acc + (mr.hintPenaltySeconds || 0),
    0
  );

  if (allThreeCompleted) {
    rawTotalSeconds = updatedMiniRounds.reduce(
      (acc, mr) => acc + (mr.durationSeconds || 0),
      0
    );
    adjustedTotalSeconds = rawTotalSeconds + totalPenaltySeconds;

    fastestMiniRoundSeconds = Math.min(
      ...updatedMiniRounds.map((mr) => mr.durationSeconds as number)
    );
  }

  return {
    ...record,
    miniRounds: updatedMiniRounds,
    rawTotalSeconds,
    totalPenaltySeconds,
    adjustedTotalSeconds,
    fastestMiniRoundSeconds,
    isComplete: allThreeCompleted,
  };
}

export interface ScoringEngineResult {
  records: TeamRound1Record[];
  canFinalize: boolean;
  blockReason?: string;
  tiesCount: number;
  completedCount: number;
  incompleteCount: number;
  top24CutoffTime?: number | null;
}

/**
 * Main Scoring & Qualification Engine for Round 1.
 * - Only completed teams can be ranked.
 * - Sorts by adjustedTotalSeconds ASC.
 * - Resolves ties by fastestMiniRoundSeconds ASC.
 * - Flags unresolved ties for manual review.
 * - Prevents finalization if incomplete or if unresolved tie straddles 24th cutoff.
 */
export function processRound1Standings(
  records: TeamRound1Record[],
  penaltyPerHintSeconds: number,
  isFinalized: boolean
): ScoringEngineResult {
  // 1. Calculate individual team totals
  const processed = records.map((rec) => computeTeamTotals(rec, penaltyPerHintSeconds));

  const completed = processed.filter((r) => r.isComplete);
  const incomplete = processed.filter((r) => !r.isComplete);

  // 2. Sort completed teams
  completed.sort((a, b) => {
    const timeA = a.adjustedTotalSeconds!;
    const timeB = b.adjustedTotalSeconds!;

    if (timeA !== timeB) {
      return timeA - timeB;
    }

    // Tie-breaker 1: Fastest single mini-round duration
    const fastestA = a.fastestMiniRoundSeconds!;
    const fastestB = b.fastestMiniRoundSeconds!;
    if (fastestA !== fastestB) {
      return fastestA - fastestB;
    }

    // Unresolved tie
    return a.teamNumber - b.teamNumber;
  });

  // 3. Assign ranks and evaluate ties
  let tiesCount = 0;
  let cutoffBoundaryTie = false;

  for (let i = 0; i < completed.length; i++) {
    const current = completed[i];
    let rank = i + 1;

    // Check if tied with predecessor
    if (i > 0) {
      const prev = completed[i - 1];
      if (
        prev.adjustedTotalSeconds === current.adjustedTotalSeconds &&
        prev.fastestMiniRoundSeconds === current.fastestMiniRoundSeconds
      ) {
        // Tied with prev
        rank = prev.rank!;
        current.tieRequiresReview = true;
        prev.tieRequiresReview = true;
        current.tieReason = `Tied with ${prev.teamName} (Adj: ${current.adjustedTotalSeconds}s, Fastest Mini: ${current.fastestMiniRoundSeconds}s)`;
        prev.tieReason = `Tied with ${current.teamName} (Adj: ${prev.adjustedTotalSeconds}s, Fastest Mini: ${prev.fastestMiniRoundSeconds}s)`;
        tiesCount++;

        // Check if tie crosses or lands on cutoff boundary (rank 24 and rank 25)
        if (i === 23 || i === 24) {
          cutoffBoundaryTie = true;
        }
      } else {
        current.tieRequiresReview = false;
        current.tieReason = undefined;
      }
    } else {
      current.tieRequiresReview = false;
      current.tieReason = undefined;
    }

    current.rank = rank;

    // Determine qualification status
    if (isFinalized) {
      current.qualificationStatus =
        rank <= 24 ? 'Finalized Qualified' : 'Finalized Eliminated';
    } else {
      if (current.tieRequiresReview && (rank === 24 || rank === 25)) {
        current.qualificationStatus = 'Tie Review Needed';
      } else {
        current.qualificationStatus =
          rank <= 24 ? 'Provisional Qualified' : 'Provisional Eliminated';
      }
    }
  }

  // Handle incomplete teams
  for (const inc of incomplete) {
    inc.rank = null;
    inc.tieRequiresReview = false;
    inc.tieReason = undefined;
    inc.qualificationStatus = 'Incomplete';
  }

  const allRecords = [...completed, ...incomplete];

  // Finalization readiness evaluation
  let canFinalize = true;
  let blockReason: string | undefined;

  if (allRecords.length < 32) {
    canFinalize = false;
    blockReason = `Tournament has only ${allRecords.length} registered squads (expected 32).`;
  } else if (incomplete.length > 0) {
    canFinalize = false;
    blockReason = `Results are incomplete: ${incomplete.length} squad(s) have not completed all three mini-rounds.`;
  } else if (cutoffBoundaryTie) {
    canFinalize = false;
    blockReason =
      'Unresolved tie exists at the 24th qualification cutoff boundary. Manual review required by event marshals.';
  }

  const top24CutoffTime =
    completed.length >= 24 ? completed[23].adjustedTotalSeconds : null;

  return {
    records: allRecords,
    canFinalize,
    blockReason,
    tiesCount,
    completedCount: completed.length,
    incompleteCount: incomplete.length,
    top24CutoffTime,
  };
}
