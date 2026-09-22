import {
  FinaleConfig,
  FinaleScoringCriterion,
  FinaleScorecard,
  FinaleSecretAgentVerdict,
  FinaleScoreBreakdown,
  TeamFinaleRecord,
  FinaleEngineResult,
  FinaleChecklistItem,
  FinaleSummaryStats,
} from '../types/finale';

export const DEFAULT_FINALE_CRITERIA: FinaleScoringCriterion[] = [
  {
    id: 'climax_defense',
    name: 'Grand Finale Oral Defense & Case Climax',
    maxMarks: 50,
    weight: 1.0,
    isConfirmed: false, // Pending official confirmation by organizers
    description: 'Final argument before faculty grand tribunal and assembly (Suggested — pending confirmation)',
  },
  {
    id: 'cross_examination',
    name: 'Grand Panel Cross-Examination & Q&A',
    maxMarks: 30,
    weight: 1.0,
    isConfirmed: false, // Pending official confirmation by organizers
    description: 'Responsiveness to master inquisitor and faculty queries (Suggested — pending confirmation)',
  },
  {
    id: 'synergy_decorum',
    name: 'Team Cohesion & Courtroom Decorum',
    maxMarks: 20,
    weight: 1.0,
    isConfirmed: false, // Pending official confirmation by organizers
    description: 'Equal participation and professionalism across all squad members (Suggested — pending confirmation)',
  },
];

export const DEFAULT_FINALE_CONFIG: FinaleConfig = {
  isScoringRulesConfirmed: false, // Must be explicitly confirmed by organizers
  confirmedAt: null,
  confirmedBy: null,
  criteria: DEFAULT_FINALE_CRITERIA,
  round4ScoreCarriedOver: true,
  round4ScoreWeight: 0.2, // Suggested: 20% carried forward from Round 4
  finaleActivityWeight: 1.0, // Suggested: 100% of finale activity score
  agentBonusPointsForCorrect: null, // Unconfirmed
  agentPenaltyPointsForIncorrect: null, // Unconfirmed
  scoringDirection: 'higher_wins',
  isFinalized: false,
  finalizedAt: null,
  finalizedBy: null,
};

/**
 * Calculates a scorecard's total score from category marks.
 * NEVER treats missing or unentered marks as zero.
 */
export function calculateScorecardTotal(
  scores: Record<string, number | null>,
  criteria: FinaleScoringCriterion[]
): { totalScore: number | null; isComplete: boolean } {
  let sum = 0;
  let isComplete = true;

  for (const crit of criteria) {
    const val = scores[crit.id];
    if (val === null || val === undefined || isNaN(val)) {
      isComplete = false;
    } else {
      sum += val;
    }
  }

  return {
    totalScore: isComplete ? Number(sum.toFixed(2)) : null,
    isComplete,
  };
}

/**
 * Calculates a squad's complete Grand Finale score breakdown.
 * Enforces that missing scores are never treated as zero, and final scores
 * are not computed while rules remain unconfirmed.
 */
export function calculateFinaleScoreBreakdown(
  teamId: string,
  round4Score: number | null,
  scorecard: FinaleScorecard,
  agentVerdict: FinaleSecretAgentVerdict | undefined,
  config: FinaleConfig
): FinaleScoreBreakdown {
  const missingComponents: string[] = [];

  if (!config.isScoringRulesConfirmed) {
    missingComponents.push('Grand Finale scoring rules pending official confirmation');
  }

  if (!scorecard.isComplete || scorecard.totalScore === null) {
    missingComponents.push('Grand Finale activity scorecard is incomplete or unsubmitted');
  }

  if (config.round4ScoreCarriedOver && round4Score === null) {
    missingComponents.push('Round 4 carried score is missing');
  }

  const round4Contribution =
    config.round4ScoreCarriedOver && round4Score !== null
      ? Number((round4Score * config.round4ScoreWeight).toFixed(2))
      : 0;

  const finaleActivityContribution =
    scorecard.totalScore !== null
      ? Number((scorecard.totalScore * config.finaleActivityWeight).toFixed(2))
      : null;

  let agentAdjustment = 0;
  if (agentVerdict && agentVerdict.isVerified) {
    if (agentVerdict.isCorrect === true && agentVerdict.bonusPoints !== null) {
      agentAdjustment += agentVerdict.bonusPoints;
    } else if (agentVerdict.isCorrect === false && agentVerdict.penaltyPoints !== null) {
      agentAdjustment -= agentVerdict.penaltyPoints;
    }
  }

  const isComplete = missingComponents.length === 0 && finaleActivityContribution !== null;

  let totalFinaleScore: number | null = null;
  if (isComplete) {
    totalFinaleScore = Number((round4Contribution + finaleActivityContribution + agentAdjustment).toFixed(2));
  }

  return {
    teamId,
    round4CarriedScore: round4Score,
    round4Weight: config.round4ScoreWeight,
    round4Contribution,
    finaleActivityScore: scorecard.totalScore,
    finaleActivityWeight: config.finaleActivityWeight,
    finaleActivityContribution,
    agentAdjustment,
    totalFinaleScore,
    isComplete,
    missingComponents,
  };
}

/**
 * Pure standings and qualification engine for the Grand Finale.
 * Enforces:
 * - Exactly 3 teams qualify from Round 4.
 * - Round 4 must be finalized.
 * - Rules must be confirmed by organizers.
 * - No invented tie-breakers: placement-affecting ties strictly require manual review.
 */
export function processFinaleStandings(
  rawRecords: TeamFinaleRecord[],
  config: FinaleConfig,
  round4Finalized: boolean
): FinaleEngineResult {
  const checklist: FinaleChecklistItem[] = [];

  // 1. Check Round 4 finalization
  checklist.push({
    id: 'round-4-finalized',
    label: 'Round 4: The Legal Battle Finalized',
    passed: round4Finalized,
    details: round4Finalized
      ? 'Official Round 4 results sealed. Top 3 finalist squads advanced.'
      : 'Round 4 results must be finalized before Grand Finale results can be declared.',
    severity: 'blocker',
  });

  // 2. Check finalist count (Expected: 3)
  const countPassed = rawRecords.length === 3;
  checklist.push({
    id: 'finalist-count',
    label: 'Exactly 3 Finalist Squads Participating',
    passed: countPassed,
    details: countPassed
      ? 'All 3 finalist podium squads verified from Round 4.'
      : `Detected ${rawRecords.length} finalist squads (Expected: exactly 3). Organizer review required.`,
    severity: 'blocker',
  });

  // 3. Check official rules confirmation
  const rulesPassed = config.isScoringRulesConfirmed;
  checklist.push({
    id: 'rules-confirmed',
    label: 'Grand Finale Scoring Rules Confirmed',
    passed: rulesPassed,
    details: rulesPassed
      ? 'Scoring criteria, multipliers, and carried-over weights officially confirmed by organizing committee.'
      : 'Rules are currently pending official confirmation. Organizers must review and confirm.',
    severity: 'blocker',
  });

  // 4. Check scorecards completeness
  const scorecardsPassed =
    rawRecords.length > 0 &&
    rawRecords.every((r) => r.scorecard.isComplete && r.scoreBreakdown.totalFinaleScore !== null);
  checklist.push({
    id: 'scorecards-complete',
    label: 'All Finalist Scorecards Submitted & Complete',
    passed: scorecardsPassed,
    details: scorecardsPassed
      ? 'All finalist scorecards submitted with zero missing criteria.'
      : 'One or more finalist scorecards are missing or incomplete. Missing scores are never treated as zero.',
    severity: 'blocker',
  });

  // Sort records:
  // If total finale scores are present, sort by totalFinaleScore descending.
  // Otherwise sort by round4Score descending or teamNumber.
  const sorted = [...rawRecords].sort((a, b) => {
    const scoreA = a.scoreBreakdown.totalFinaleScore;
    const scoreB = b.scoreBreakdown.totalFinaleScore;

    if (scoreA !== null && scoreB !== null) {
      if (scoreB !== scoreA) {
        return config.scoringDirection === 'higher_wins' ? scoreB - scoreA : scoreA - scoreB;
      }
    } else if (scoreA !== null) {
      return -1;
    } else if (scoreB !== null) {
      return 1;
    } else {
      const r4A = a.round4Score ?? -1;
      const r4B = b.round4Score ?? -1;
      if (r4B !== r4A) return r4B - r4A;
    }

    return a.teamNumber - b.teamNumber;
  });

  // Detect ties affecting 1st, 2nd, or 3rd place
  let tiesAffectingPlacement = false;
  if (scorecardsPassed && rulesPassed) {
    const scoreMap = new Map<number, TeamFinaleRecord[]>();
    sorted.forEach((r) => {
      const sc = r.scoreBreakdown.totalFinaleScore;
      if (sc !== null) {
        if (!scoreMap.has(sc)) scoreMap.set(sc, []);
        scoreMap.get(sc)!.push(r);
      }
    });

    scoreMap.forEach((group, scoreVal) => {
      if (group.length > 1) {
        tiesAffectingPlacement = true;
        group.forEach((rec) => {
          rec.tieRequiresReview = true;
          rec.tieReason = `Tied with ${scoreVal} pts for podium placement. Tournament rules require explicit manual marshal determination.`;
        });
      }
    });
  }

  checklist.push({
    id: 'ties-safeguard',
    label: 'Podium Free of Unresolved Placement Ties',
    passed: !tiesAffectingPlacement,
    details: tiesAffectingPlacement
      ? 'Two or more squads share identical total points affecting podium honors. Manual review required.'
      : 'No placement-affecting ties detected.',
    severity: 'blocker',
  });

  // Assign placement titles if all scores are complete, rules are confirmed, and no ties exist
  const canAwardPlacements = rulesPassed && scorecardsPassed && !tiesAffectingPlacement;

  sorted.forEach((rec, idx) => {
    if (canAwardPlacements) {
      const p = (idx + 1) as 1 | 2 | 3;
      rec.placement = p;
      if (p === 1) rec.placementTitle = 'Grand Champion';
      else if (p === 2) rec.placementTitle = '1st Runner Up';
      else if (p === 3) rec.placementTitle = '2nd Runner Up';
    } else {
      rec.placement = null;
      rec.placementTitle = null;
    }

    // Assign Review Status
    if (!round4Finalized) {
      rec.reviewStatus = 'Round 4 Pending';
    } else if (rawRecords.length !== 3) {
      rec.reviewStatus = 'Finalist Discrepancy';
    } else if (!rulesPassed) {
      rec.reviewStatus = 'Rules Unconfirmed';
    } else if (!rec.scorecard.isComplete) {
      rec.reviewStatus = 'Scores Incomplete';
    } else if (rec.tieRequiresReview) {
      rec.reviewStatus = 'Tie Review Needed';
    } else if (config.isFinalized) {
      if (rec.placement === 1) rec.reviewStatus = 'Finalized Champion';
      else if (rec.placement === 2) rec.reviewStatus = 'Finalized 1st Runner Up';
      else if (rec.placement === 3) rec.reviewStatus = 'Finalized 2nd Runner Up';
      else rec.reviewStatus = 'Finalized';
    } else {
      rec.reviewStatus = 'Ready for Finalization';
    }
  });

  // Check blockers
  const blockers = checklist.filter((c) => !c.passed && c.severity === 'blocker');
  const canFinalize = blockers.length === 0;
  const blockReason = blockers.length > 0 ? `${blockers[0].label}: ${blockers[0].details}` : null;

  const championTeamId = canAwardPlacements && sorted.length > 0 ? sorted[0].teamId : null;
  const runnerUp1TeamId = canAwardPlacements && sorted.length > 1 ? sorted[1].teamId : null;
  const runnerUp2TeamId = canAwardPlacements && sorted.length > 2 ? sorted[2].teamId : null;

  return {
    records: sorted,
    canFinalize,
    blockReason,
    checklist,
    tiesAffectingPlacement,
    championTeamId,
    runnerUp1TeamId,
    runnerUp2TeamId,
  };
}

/**
 * Computes summary KPI stats for Grand Finale.
 */
export function computeFinaleSummaryStats(
  records: TeamFinaleRecord[],
  config: FinaleConfig,
  round4Finalized: boolean,
  eligibleCount: number,
  engine: FinaleEngineResult
): FinaleSummaryStats {
  const scorecardsCompletedCount = records.filter((r) => r.scorecard.isComplete).length;
  const agentVerdictsVerifiedCount = records.filter(
    (r) => r.agentVerdict && r.agentVerdict.isVerified
  ).length;

  const champion = records.find((r) => r.teamId === engine.championTeamId);
  const r1 = records.find((r) => r.teamId === engine.runnerUp1TeamId);
  const r2 = records.find((r) => r.teamId === engine.runnerUp2TeamId);

  return {
    round4Finalized,
    eligibleTeamsCount: eligibleCount,
    rulesConfirmed: config.isScoringRulesConfirmed,
    scorecardsCompletedCount,
    agentVerdictsVerifiedCount,
    canFinalize: engine.canFinalize,
    isFinalized: config.isFinalized,
    championTeamName: champion?.teamName || null,
    runnerUp1TeamName: r1?.teamName || null,
    runnerUp2TeamName: r2?.teamName || null,
  };
}
