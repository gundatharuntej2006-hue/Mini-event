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
export interface ScoringEngineResult {
  records: TeamRound1Record[];
  canFinalize: boolean;
  blockReason?: string;
  tiesCount: number;
  completedCount: number;
  incompleteCount: number;
  top16CutoffTime?: number | null;
  top24CutoffTime?: number | null; // Backwards-compatible alias
}

/**
 * Computes raw total, penalties, adjusted total, and fastest mini-round for a squad.
 */
export function computeTeamTotals(
  record: TeamRound1Record,
  penaltyPerHintSeconds: number = 300
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

  // Sum hints and additional penalties across gates
  const hintsCount = updatedMiniRounds.reduce((acc, mr) => acc + (mr.hintsUsed || 0), 0);
  const hintPenaltiesSeconds = hintsCount * penaltyPerHintSeconds;
  const phonePenaltiesCount = record.phonePenaltiesCount || updatedMiniRounds.reduce((acc, mr) => acc + (mr.phonePenaltiesCount || 0), 0);
  const phonePenaltySeconds = phonePenaltiesCount * 600;
  const separationPenaltiesCount = record.separationPenaltiesCount || updatedMiniRounds.reduce((acc, mr) => acc + (mr.separationPenaltiesCount || 0), 0);
  const separationPenaltySeconds = separationPenaltiesCount * 300;
  const clueTamperingDeduction = record.clueTamperingDeduction || 0;
  const isDisqualified = !!record.isDisqualified;

  totalPenaltySeconds = hintPenaltiesSeconds + phonePenaltySeconds + separationPenaltySeconds;

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
    hintsCount,
    hintPenaltiesSeconds,
    phonePenaltiesCount,
    phonePenaltySeconds,
    separationPenaltiesCount,
    separationPenaltySeconds,
    clueTamperingDeduction,
    isDisqualified,
    totalPenaltySeconds,
    adjustedTotalSeconds,
    fastestMiniRoundSeconds,
    isComplete: allThreeCompleted,
  };
}

/**
 * Main Scoring & Qualification Engine for Round 1: The ODDyssey Protocol.
 * - Top 16 qualifiers advance to Round 2 (Cabo).
 * - Sorts completed teams by adjustedTotalSeconds ASC.
 * - Resolves ties by fastestMiniRoundSeconds ASC.
 * - Awards rank points: 1st=16, 2nd=15 ... 16th=1, 17th+=0.
 * - Flags unresolved ties for manual review.
 * - Prevents finalization if incomplete or if unresolved tie straddles 16th/17th cutoff.
 */
export function processRound1Standings(
  records: TeamRound1Record[],
  penaltyPerHintSeconds: number = 300,
  isFinalized: boolean = false
): ScoringEngineResult {
  // 1. Calculate individual team totals
  const processed = records.map((rec) => computeTeamTotals(rec, penaltyPerHintSeconds));

  const disqualified = processed.filter((r) => r.isDisqualified);
  const nonDq = processed.filter((r) => !r.isDisqualified);

  const completed = nonDq.filter((r) => r.isComplete);
  const incomplete = nonDq.filter((r) => !r.isComplete);

  // 2. Sort completed teams
  completed.sort((a, b) => {
    const timeA = a.adjustedTotalSeconds!;
    const timeB = b.adjustedTotalSeconds!;

    if (timeA !== timeB) {
      return timeA - timeB;
    }

    // Tie-breaker 1: Fastest single gate duration
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
        current.tieReason = `Tied with ${prev.teamName} (Adj: ${current.adjustedTotalSeconds}s, Fastest Gate: ${current.fastestMiniRoundSeconds}s)`;
        prev.tieReason = `Tied with ${current.teamName} (Adj: ${prev.adjustedTotalSeconds}s, Fastest Gate: ${prev.fastestMiniRoundSeconds}s)`;
        tiesCount++;

        // Check if tie crosses or lands on 16th cutoff boundary (rank 16 and rank 17)
        if (i === 15 || i === 16) {
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
    // Rank points: 1st=16, 2nd=15 ... 16th=1, 17th+=0
    current.rankPoints = rank <= 16 ? 17 - rank : 0;

    // Determine qualification status (Top 16)
    if (isFinalized) {
      current.qualificationStatus =
        rank <= 16 ? 'Finalized Qualified' : 'Finalized Eliminated';
    } else {
      if (current.tieRequiresReview && (rank === 16 || rank === 17)) {
        current.qualificationStatus = 'Tie Review Needed';
      } else {
        current.qualificationStatus =
          rank <= 16 ? 'Provisional Qualified' : 'Provisional Eliminated';
      }
    }
  }

  // Handle incomplete teams
  for (const inc of incomplete) {
    inc.rank = null;
    inc.rankPoints = 0;
    inc.tieRequiresReview = false;
    inc.tieReason = undefined;
    inc.qualificationStatus = 'Incomplete';
  }

  // Handle disqualified teams
  for (const dq of disqualified) {
    dq.rank = null;
    dq.rankPoints = 0;
    dq.tieRequiresReview = false;
    dq.tieReason = dq.disqualificationReason || 'Disqualified';
    dq.qualificationStatus = 'Disqualified';
  }

  const allRecords = [...completed, ...incomplete, ...disqualified];

  // Finalization readiness evaluation
  let canFinalize = true;
  let blockReason: string | undefined;

  if (allRecords.length < 32) {
    canFinalize = false;
    blockReason = `Tournament has only ${allRecords.length} registered squads (expected 32).`;
  } else if (incomplete.length > 0) {
    canFinalize = false;
    blockReason = `Results are incomplete: ${incomplete.length} squad(s) have not completed all three gates.`;
  } else if (cutoffBoundaryTie) {
    canFinalize = false;
    blockReason =
      'Unresolved tie exists at the 16th qualification cutoff boundary. Manual review required by event marshals.';
  }

  const top16CutoffTime =
    completed.length >= 16 ? completed[15].adjustedTotalSeconds : null;

  return {
    records: allRecords,
    canFinalize,
    blockReason,
    tiesCount,
    completedCount: completed.length,
    incompleteCount: incomplete.length,
    top16CutoffTime,
    top24CutoffTime: top16CutoffTime,
  };
}
