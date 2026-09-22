import {
  Round4StageId,
  StageTimingRecord,
  RubricCategoryConfig,
  FinalScoreFormulaConfig,
  Round4Config,
  TeamRound4Record,
  Round4EngineResult,
  Round4SummaryStats,
  TeamPair,
  JudgeScoreRecord,
  AgentGuessingRecord,
  TeamFinalScoreBreakdown,
  Round4ChecklistItem,
} from '../types/round4';

export const DEFAULT_RUBRIC_CATEGORIES: RubricCategoryConfig[] = [
  {
    id: 'logical_structure',
    name: 'Logical structure',
    maxMarks: 20, // Suggested — pending organizer confirmation
    isConfirmed: false,
    description: 'Coherence of legal reasoning, clarity of core premise, structured argumentation',
  },
  {
    id: 'evidence_use',
    name: 'Use of evidence',
    maxMarks: 20, // Suggested — pending organizer confirmation
    isConfirmed: false,
    description: 'Application of case facts, documentary evidence, and discovery filings',
  },
  {
    id: 'rebuttal',
    name: 'Rebuttal',
    maxMarks: 20, // Suggested — pending organizer confirmation
    isConfirmed: false,
    description: 'Responsiveness to opposing counsel, counter-argument sharpness, cross-examination',
  },
  {
    id: 'resource_questioning',
    name: 'Questioning the resource person',
    maxMarks: 15, // Suggested — pending organizer confirmation
    isConfirmed: false,
    description: 'Relevance of queries, strategic discovery extraction, professional inquiry',
  },
  {
    id: 'presentation_teamwork',
    name: 'Presentation and teamwork',
    maxMarks: 15, // Suggested — pending organizer confirmation
    isConfirmed: false,
    description: 'Oratorical delivery, courtroom decorum, equal contribution across squad members',
  },
  {
    id: 'time_management',
    name: 'Time management',
    maxMarks: 10, // Suggested — pending organizer confirmation
    isConfirmed: false,
    description: 'Adherence to oral argument time limits, efficient division of speaking segments',
  },
];

export function createInitialPairStages(): Record<Round4StageId, StageTimingRecord> {
  return {
    prep_1: {
      stageId: 'prep_1',
      name: 'Preparation 1',
      suggestedDurationMinutes: 40,
      configuredDurationMinutes: 40,
      status: 'not_started',
      startedAt: null,
      endedAt: null,
      actualDurationSeconds: null,
      notes: '',
      incidentFlags: '',
    },
    hearing_1: {
      stageId: 'hearing_1',
      name: 'Hearing 1',
      suggestedDurationMinutes: 20,
      configuredDurationMinutes: 20,
      status: 'not_started',
      startedAt: null,
      endedAt: null,
      actualDurationSeconds: null,
      notes: '',
      incidentFlags: '',
    },
    file_exchange: {
      stageId: 'file_exchange',
      name: 'Opposing-File Exchange',
      suggestedDurationMinutes: null, // duration not specified in documentation
      configuredDurationMinutes: null,
      status: 'not_started',
      startedAt: null,
      endedAt: null,
      actualDurationSeconds: null,
      notes: '',
      incidentFlags: '',
    },
    prep_2: {
      stageId: 'prep_2',
      name: 'Preparation 2',
      suggestedDurationMinutes: 25, // 20-25 minutes suggested
      configuredDurationMinutes: 25,
      status: 'not_started',
      startedAt: null,
      endedAt: null,
      actualDurationSeconds: null,
      notes: '',
      incidentFlags: '',
    },
    hearing_2: {
      stageId: 'hearing_2',
      name: 'Hearing 2',
      suggestedDurationMinutes: 20,
      configuredDurationMinutes: 20,
      status: 'not_started',
      startedAt: null,
      endedAt: null,
      actualDurationSeconds: null,
      notes: '',
      incidentFlags: '',
    },
  };
}

export const DEFAULT_FINAL_SCORE_FORMULA: FinalScoreFormulaConfig = {
  // Suggested formula: Final Score = Legal Battle panel score + Agent guessing points + 10% of remaining Black Market points
  // Organizers may adjust weighting. Labeled "Suggested — pending organizer confirmation".
  panelScoreWeight: 1.0,
  agentGuessingWeight: 1.0,
  blackMarketWeightPercent: 10, // 10%
  isFormulaConfirmed: false,
  confirmedAt: null,
  confirmedBy: null,
};

export const DEFAULT_ROUND4_CONFIG: Round4Config = {
  rubricCategories: DEFAULT_RUBRIC_CATEGORIES,
  isRubricConfirmed: false, // Suggested — pending organizer confirmation
  judgeAggregation: 'average',
  judgesList: [
    { id: 'judge-1', name: 'Faculty Judge 1 [TBD]' },
    { id: 'judge-2', name: 'Faculty Judge 2 [TBD]' },
  ],
  isGuessingRulesConfigured: false,
  guessingPointsForCorrect: null, // Unconfigured
  guessingPointsForIncorrect: null,
  finalScoreFormula: DEFAULT_FINAL_SCORE_FORMULA,
  advancingTeamsCount: null, // Configurable: null = unconfirmed (e.g. Top 3 for Grand Finale podium)
  isFinalized: false,
  finalizedAt: null,
};

/**
 * Calculates a squad's aggregated panel score from submitted judge scorecards.
 * Never treats missing scores as zero.
 */
export function calculatePanelScore(
  judgeScores: JudgeScoreRecord[],
  aggregation: 'average' | 'sum' | 'single_judge'
): { panelScore: number | null; isComplete: boolean } {
  const submittedScores = judgeScores.filter((js) => js.isSubmitted);
  if (submittedScores.length === 0) {
    return { panelScore: null, isComplete: false };
  }

  if (aggregation === 'single_judge') {
    return { panelScore: submittedScores[0].totalScore, isComplete: true };
  }

  if (aggregation === 'sum') {
    const sum = submittedScores.reduce((acc, s) => acc + s.totalScore, 0);
    return { panelScore: sum, isComplete: true };
  }

  // Default: average
  const sum = submittedScores.reduce((acc, s) => acc + s.totalScore, 0);
  const avg = Number((sum / submittedScores.length).toFixed(2));
  return { panelScore: avg, isComplete: true };
}

/**
 * Calculates a squad's final score using the configurable formula.
 *
 * Suggested formula:
 * Final Score = (Panel Score * weight) + (Agent Guessing Points * weight) + (Black Market Remaining Points * percentage)
 *
 * Enforces:
 * - Does NOT silently treat missing scores as zero.
 * - Does NOT calculate final score if formula is unconfirmed by organizers.
 */
export function calculateFinalScoreBreakdown(
  teamId: string,
  panelScore: number | null,
  agentRecord: AgentGuessingRecord | undefined,
  blackMarketBalance: number,
  formula: FinalScoreFormulaConfig,
  isGuessingConfigured: boolean
): TeamFinalScoreBreakdown {
  const missingComponents: string[] = [];

  if (!formula.isFormulaConfirmed) {
    missingComponents.push('Final score formula unconfirmed by organizers');
  }

  if (panelScore === null) {
    missingComponents.push('Faculty judging panel score missing');
  }

  let agentGuessingPoints: number | null = null;
  if (isGuessingConfigured) {
    if (!agentRecord || !agentRecord.isVerified || agentRecord.pointsAwarded === null) {
      missingComponents.push('Secret agent guessing score unverified');
    } else {
      agentGuessingPoints = agentRecord.pointsAwarded;
    }
  } else {
    // If guessing rules not configured, record as null
    agentGuessingPoints = agentRecord?.pointsAwarded ?? null;
  }

  const rawPanel = panelScore;
  const weightedPanel = panelScore !== null ? Number((panelScore * formula.panelScoreWeight).toFixed(2)) : null;
  const bmContribution = Number(
    ((Math.max(0, blackMarketBalance) * formula.blackMarketWeightPercent) / 100).toFixed(2)
  );

  let finalScore: number | null = null;
  const isComplete = missingComponents.length === 0 && panelScore !== null;

  if (isComplete) {
    let sum = (weightedPanel ?? 0) + bmContribution;
    if (agentGuessingPoints !== null) {
      sum += agentGuessingPoints * formula.agentGuessingWeight;
    }
    finalScore = Number(sum.toFixed(2));
  }

  return {
    teamId,
    rawPanelScore: rawPanel,
    weightedPanelScore: weightedPanel,
    agentGuessingPoints,
    blackMarketBalance,
    blackMarketContribution: bmContribution,
    finalScore,
    isComplete,
    missingComponents,
  };
}

/**
 * Standings and Qualification Engine for Round 4: The Legal Battle.
 *
 * Evaluates:
 * - Verification that exactly 8 teams qualified from Round 3.
 * - Confirmation of team pairings and case assignments.
 * - Stage progression across Preparation 1, Hearing 1, File Exchange, Prep 2, Hearing 2.
 * - Faculty judging panel score completion.
 * - Final score formula confirmation and calculation.
 * - Tie detection across onward qualification cutoff.
 */
export function processRound4Standings(
  records: TeamRound4Record[],
  pairs: TeamPair[],
  config: Round4Config,
  round3Finalized: boolean
): Round4EngineResult {
  const checklist: Round4ChecklistItem[] = [];

  // 1. Check Round 3 finalization
  const r3Check = round3Finalized;
  checklist.push({
    id: 'round-3-finalized',
    label: 'Round 3: The Black Market Finalized',
    passed: r3Check,
    details: r3Check
      ? 'Official Round 3 results sealed. 8 finalist squads advanced.'
      : 'Round 3 results must be finalized before Round 4 can proceed.',
    severity: 'blocker',
  });

  // 2. Check exactly 8 participating squads
  const teamCountCheck = records.length === 8;
  checklist.push({
    id: 'squad-count',
    label: 'Exactly 8 Finalist Squads Participating',
    passed: teamCountCheck,
    details: `Detected ${records.length} participating squads (Expected: 8).`,
    severity: 'blocker',
  });

  // 3. Check pairings confirmation
  const pairsFormed = pairs.length === 4 && pairs.every((p) => p.teamAId && p.teamBId);
  const pairingsConfirmed = pairsFormed && pairs.every((p) => p.isConfirmed);
  checklist.push({
    id: 'pairings-confirmed',
    label: '4 Team Matchup Pairings Confirmed',
    passed: pairingsConfirmed,
    details: pairingsConfirmed
      ? 'All 4 head-to-head pairings officially confirmed by organizers.'
      : 'Pairings must be formed and explicitly confirmed by organizers.',
    severity: 'blocker',
  });

  // 4. Check case assignments and sides
  const casesAssigned =
    pairs.length === 4 &&
    pairs.every(
      (p) =>
        p.caseName &&
        p.caseName.trim().length > 0 &&
        p.teamAAssignment.side !== 'Unassigned' &&
        p.teamBAssignment.side !== 'Unassigned'
    );
  checklist.push({
    id: 'cases-assigned',
    label: 'Fictional Legal Cases & Sides Assigned',
    passed: casesAssigned,
    details: casesAssigned
      ? 'All 4 pairs have designated legal cases and counsel sides.'
      : 'Assign official case titles and team sides for all 4 pairs.',
    severity: 'blocker',
  });

  // 5. Check stage progression (hearings and file exchange)
  const hearingsDone = pairs.every(
    (p) =>
      p.stages.hearing_1.status === 'completed' &&
      p.stages.file_exchange.status === 'completed' &&
      p.stages.hearing_2.status === 'completed'
  );
  checklist.push({
    id: 'hearings-completed',
    label: 'Hearing Stages & File Exchange Completed',
    passed: hearingsDone,
    details: hearingsDone
      ? 'Hearing 1, Opposing-File Exchange, and Hearing 2 logged complete.'
      : 'Oral argument sessions and file exchanges must be marked completed.',
    severity: 'blocker',
  });

  // 6. Check faculty judging completeness
  const judgesComplete = records.every((r) => r.isJudgePanelComplete && r.panelScore !== null);
  checklist.push({
    id: 'judging-scores',
    label: 'Faculty Panel Scorecards Submitted',
    passed: judgesComplete,
    details: judgesComplete
      ? 'All 8 finalist squads have complete submitted judging scores.'
      : 'Faculty judging scorecards are missing or incomplete for one or more squads.',
    severity: 'blocker',
  });

  // 7. Check final score formula confirmation
  const formulaConfirmed = config.finalScoreFormula.isFormulaConfirmed;
  checklist.push({
    id: 'formula-confirmed',
    label: 'Final-Score Formula Officially Confirmed',
    passed: formulaConfirmed,
    details: formulaConfirmed
      ? 'Scoring formula and weighting confirmed by organizing committee.'
      : 'Suggested scoring formula is unconfirmed. Organizers must review and confirm.',
    severity: 'blocker',
  });

  // Sort records:
  // If final scores are available, sort by finalScore descending.
  // Otherwise sort by panelScore descending or teamNumber.
  const sortedRecords = [...records].sort((a, b) => {
    const scoreA = a.finalScoreBreakdown.finalScore;
    const scoreB = b.finalScoreBreakdown.finalScore;

    if (scoreA !== null && scoreB !== null) {
      if (scoreB !== scoreA) return scoreB - scoreA;
    } else if (scoreA !== null) {
      return -1;
    } else if (scoreB !== null) {
      return 1;
    } else {
      // Fallback to panel score
      const pA = a.panelScore ?? -1;
      const pB = b.panelScore ?? -1;
      if (pB !== pA) return pB - pA;
    }

    return a.teamNumber - b.teamNumber;
  });

  // Assign ranks if final scores are computed
  let currentRank = 1;
  sortedRecords.forEach((rec) => {
    if (rec.finalScoreBreakdown.finalScore !== null) {
      rec.rank = currentRank++;
    } else {
      rec.rank = null;
    }
  });

  // Detect ties across advancing cutoff if onward qualification count is configured
  let tiesAffectingCutoff = false;
  if (config.advancingTeamsCount && config.advancingTeamsCount > 0 && config.advancingTeamsCount < 8) {
    const cutoffRank = config.advancingTeamsCount;
    const scoreGroups = new Map<number, TeamRound4Record[]>();

    sortedRecords.forEach((rec) => {
      const fs = rec.finalScoreBreakdown.finalScore;
      if (fs !== null) {
        if (!scoreGroups.has(fs)) scoreGroups.set(fs, []);
        scoreGroups.get(fs)!.push(rec);
      }
    });

    scoreGroups.forEach((group, scoreVal) => {
      if (group.length > 1) {
        const ranks = group.map((r) => r.rank!).filter((r) => r !== null && r !== undefined);
        const minRank = Math.min(...ranks);
        const maxRank = Math.max(...ranks);

        if (minRank <= cutoffRank && maxRank > cutoffRank) {
          tiesAffectingCutoff = true;
          group.forEach((rec) => {
            rec.tieRequiresReview = true;
            rec.tieReason = `Tied on ${scoreVal} pts spanning advancing cutoff #${cutoffRank} (Ranks #${minRank}–#${maxRank}). Official tournament rules require manual marshal review.`;
          });
        }
      }
    });
  }

  checklist.push({
    id: 'tie-safeguard',
    label: 'Advancement Cutoff Free of Unresolved Ties',
    passed: !tiesAffectingCutoff,
    details: tiesAffectingCutoff
      ? 'An unresolved tie spans across the onward qualification cutoff boundary.'
      : 'No cutoff-affecting ties detected.',
    severity: 'blocker',
  });

  // Assign review status
  sortedRecords.forEach((rec) => {
    if (!round3Finalized) {
      rec.reviewStatus = 'Round 3 Pending';
    } else if (config.isFinalized) {
      if (config.advancingTeamsCount && rec.rank !== null && rec.rank !== undefined && rec.rank <= config.advancingTeamsCount) {
        rec.reviewStatus = 'Finalized Qualified';
      } else {
        rec.reviewStatus = 'Finalized Eliminated';
      }
    } else if (rec.tieRequiresReview) {
      rec.reviewStatus = 'Tie Review Needed';
    } else if (!pairingsConfirmed) {
      rec.reviewStatus = 'Pairing Unconfirmed';
    } else if (rec.side === 'Unassigned' || !rec.caseName) {
      rec.reviewStatus = 'Case Unassigned';
    } else if (rec.stagesCompletedCount < 3) {
      rec.reviewStatus = 'Hearing Stage';
    } else if (!rec.isJudgePanelComplete) {
      rec.reviewStatus = 'Awaiting Scores';
    } else if (!formulaConfirmed) {
      rec.reviewStatus = 'Formula Unconfirmed';
    } else {
      rec.reviewStatus = 'Ready for Review';
    }
  });

  // Evaluate canFinalize
  const blockerIssues = checklist.filter((c) => !c.passed && c.severity === 'blocker');
  const canFinalize = blockerIssues.length === 0;
  const blockReason = blockerIssues.length > 0 ? blockerIssues[0].label + ': ' + blockerIssues[0].details : null;

  const advancingCount = config.advancingTeamsCount ?? 0;
  const advancingTeamIds = sortedRecords
    .filter((r) => r.rank !== null && r.rank !== undefined && advancingCount > 0 && r.rank <= advancingCount)
    .map((r) => r.teamId);

  const eliminatedTeamIds = sortedRecords
    .filter((r) => r.rank !== null && r.rank !== undefined && advancingCount > 0 && r.rank > advancingCount)
    .map((r) => r.teamId);

  return {
    records: sortedRecords,
    canFinalize,
    blockReason,
    checklist,
    tiesAffectingCutoff,
    advancingTeamIds,
    eliminatedTeamIds,
  };
}

/**
 * Computes summary KPI statistics for Round 4.
 */
export function computeRound4SummaryStats(
  records: TeamRound4Record[],
  pairs: TeamPair[],
  config: Round4Config,
  round3Finalized: boolean,
  round3QualifiedCount: number,
  engine: Round4EngineResult
): Round4SummaryStats {
  const pairingsConfirmed = pairs.length === 4 && pairs.every((p) => p.isConfirmed);
  const casesAssignedCount = pairs.filter((p) => p.caseName && p.caseName.trim().length > 0).length;

  let prep1 = 0;
  let hearing1 = 0;
  let exchange = 0;
  let prep2 = 0;
  let hearing2 = 0;

  pairs.forEach((p) => {
    if (p.stages.prep_1.status === 'completed') prep1++;
    if (p.stages.hearing_1.status === 'completed') hearing1++;
    if (p.stages.file_exchange.status === 'completed') exchange++;
    if (p.stages.prep_2.status === 'completed') prep2++;
    if (p.stages.hearing_2.status === 'completed') hearing2++;
  });

  const judgingCompletedCount = records.filter((r) => r.isJudgePanelComplete).length;
  const agentGuessesVerifiedCount = records.filter(
    (r) => r.agentGuessingRecord && r.agentGuessingRecord.isVerified
  ).length;

  return {
    round3Finalized,
    eligibleTeamsCount: round3QualifiedCount,
    pairsConfiguredCount: pairs.length,
    pairingsConfirmed,
    casesAssignedCount,
    prep1CompletedCount: prep1,
    hearing1CompletedCount: hearing1,
    fileExchangeCompletedCount: exchange,
    prep2CompletedCount: prep2,
    hearing2CompletedCount: hearing2,
    judgingCompletedCount,
    agentGuessesVerifiedCount,
    scoringFormulaConfirmed: config.finalScoreFormula.isFormulaConfirmed,
    isRubricConfirmed: config.isRubricConfirmed,
    canFinalize: engine.canFinalize,
    isFinalized: config.isFinalized,
  };
}
