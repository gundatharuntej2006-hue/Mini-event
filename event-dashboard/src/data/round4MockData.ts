import { Team } from '../types/team';
import {
  TeamPair,
  ResourcePersonRecord,
  JudgeScoreRecord,
  AgentGuessingRecord,
} from '../types/round4';
import {
  createInitialPairStages,
} from '../utils/round4Scoring';

/**
 * Generates initial pairings for the 4 Round 4 finalist teams.
 * Pairs teams into 2 semifinal matchups:
 * Matchup 1: Semifinal 1 (Seed 1 vs Seed 4)
 * Matchup 2: Semifinal 2 (Seed 2 vs Seed 3)
 */
export function generateInitialRound4Pairs(teams: Team[]): TeamPair[] {
  const top4 = teams.slice(0, 4);
  const baseTime = new Date('2026-09-19T16:00:00Z').getTime();

  const caseTemplates = [
    {
      id: 'CASE-401',
      name: 'Semifinal 1: State vs. CyberCorp Protocol Breach (Data Theft Liability)',
      details: 'Discovery docket Ref: CC-2026-BMSIT. Focus on negligence and encrypted payload attribution.',
    },
    {
      id: 'CASE-402',
      name: 'Semifinal 2: Autonomous Systems Labs vs. Department of Transportation',
      details: 'Algorithmic vehicle collision during closed-course telemetry trials.',
    },
  ];

  const pairs: TeamPair[] = [];

  // Matchup 1: Seed 1 vs Seed 4
  // Matchup 2: Seed 2 vs Seed 3
  const seedPairings = [
    { teamA: top4[0], teamB: top4[3], cTemplate: caseTemplates[0] },
    { teamA: top4[1], teamB: top4[2], cTemplate: caseTemplates[1] },
  ];

  for (let i = 0; i < 2; i++) {
    const { teamA, teamB, cTemplate } = seedPairings[i];
    const stages = createInitialPairStages();

    // Stages progression for demo
    stages.prep_1.status = 'completed';
    stages.prep_1.startedAt = new Date(baseTime).toISOString();
    stages.prep_1.endedAt = new Date(baseTime + 40 * 60000).toISOString();
    stages.prep_1.actualDurationSeconds = 2400;

    stages.hearing_1.status = 'completed';
    stages.hearing_1.startedAt = new Date(baseTime + 42 * 60000).toISOString();
    stages.hearing_1.endedAt = new Date(baseTime + 62 * 60000).toISOString();
    stages.hearing_1.actualDurationSeconds = 1200;

    stages.file_exchange.status = 'completed';
    stages.file_exchange.startedAt = new Date(baseTime + 63 * 60000).toISOString();
    stages.file_exchange.endedAt = new Date(baseTime + 68 * 60000).toISOString();
    stages.file_exchange.actualDurationSeconds = 300;

    stages.prep_2.status = 'completed';
    stages.prep_2.startedAt = new Date(baseTime + 70 * 60000).toISOString();
    stages.prep_2.endedAt = new Date(baseTime + 95 * 60000).toISOString();
    stages.prep_2.actualDurationSeconds = 1500;

    stages.hearing_2.status = 'completed';
    stages.hearing_2.startedAt = new Date(baseTime + 97 * 60000).toISOString();
    stages.hearing_2.endedAt = new Date(baseTime + 117 * 60000).toISOString();
    stages.hearing_2.actualDurationSeconds = 1200;

    pairs.push({
      pairId: `pair-${i + 1}`,
      pairNumber: i + 1,
      teamAId: teamA ? teamA.id : null,
      teamBId: teamB ? teamB.id : null,
      isConfirmed: true,
      confirmedAt: new Date(baseTime - 600000).toISOString(),
      confirmedBy: 'Tech Head / Chief Marshal',
      caseId: cTemplate.id,
      caseName: cTemplate.name,
      caseDetails: cTemplate.details,
      teamAAssignment: {
        teamId: teamA ? teamA.id : '',
        side: 'Prosecution / Plaintiff',
        hasReceivedCaseFile: true,
        caseFileReceivedAt: new Date(baseTime - 300000).toISOString(),
        hasReceivedOpposingFile: true,
        opposingFileReceivedAt: new Date(baseTime + 68 * 60000).toISOString(),
      },
      teamBAssignment: {
        teamId: teamB ? teamB.id : '',
        side: 'Defense / Respondent',
        hasReceivedCaseFile: true,
        caseFileReceivedAt: new Date(baseTime - 300000).toISOString(),
        hasReceivedOpposingFile: true,
        opposingFileReceivedAt: new Date(baseTime + 68 * 60000).toISOString(),
      },
      stages,
      resourcePersonId: `rp-${i + 1}`,
    });
  }

  return pairs;
}

/**
 * Generates initial demo Resource Person records for each pair.
 */
export function generateInitialRound4ResourcePersons(
  pairs: TeamPair[]
): Record<string, ResourcePersonRecord> {
  const records: Record<string, ResourcePersonRecord> = {};

  const rpNames = [
    'Adv. Rajesh Menon (Cyber Law Counsel)',
    'Dr. Aruna Swamy (Autonomous Robotics Expert)',
  ];

  pairs.forEach((p, idx) => {
    const rpId = `rp-${idx + 1}`;
    records[rpId] = {
      id: rpId,
      pairId: p.pairId,
      nameOrIdentifier: rpNames[idx] || `Resource Person ${idx + 1}`,
      assignedCaseName: p.caseName,
      questions: [
        {
          id: `q-${idx + 1}-1`,
          teamId: p.teamAId || '',
          questionText: 'Clarification regarding server logs and clock drift during file transfer.',
          stage: 'prep_1',
          askedAt: new Date('2026-09-19T16:15:00Z').toISOString(),
          notes: 'Witness answered confirming 14-second NTP variance.',
        },
        {
          id: `q-${idx + 1}-2`,
          teamId: p.teamBId || '',
          questionText: 'Verification of user permission credentials on subnet gateway.',
          stage: 'prep_1',
          askedAt: new Date('2026-09-19T16:22:00Z').toISOString(),
          notes: 'Clarified admin role inheritance structure.',
        },
      ],
      notes: 'Resource person available for preparation cross-examination.',
      isQuestioningComplete: true,
    };
  });

  return records;
}

/**
 * Generates initial demo Judge scorecards for the 4 teams.
 */
export function generateInitialRound4JudgeScores(
  teams: Team[]
): Record<string, JudgeScoreRecord[]> {
  const scores: Record<string, JudgeScoreRecord[]> = {};
  const top4 = teams.slice(0, 4);

  // 2 faculty judges
  const judges = [
    { id: 'judge-1', name: 'Prof. K. Venkatesh (Faculty Bench Chair)' },
    { id: 'judge-2', name: 'Adv. Sunita Rao (External Senior Advocate)' },
  ];

  // Official 100-pt rubric spreads:
  // logical(20), evidence(20), rebuttal(20), resource(15), presentation(15), time(10)
  const sampleRubrics = [
    { l: 19, e: 18, r: 19, q: 14, p: 14, t: 9 }, // Total 93
    { l: 18, e: 18, r: 18, q: 14, p: 14, t: 9 }, // Total 91
    { l: 18, e: 17, r: 18, q: 13, p: 14, t: 9 }, // Total 89
    { l: 17, e: 17, r: 17, q: 13, p: 14, t: 8 }, // Total 86
  ];

  top4.forEach((team, idx) => {
    const s1 = sampleRubrics[idx] || sampleRubrics[0];
    const s2 = {
      l: Math.max(0, s1.l - (idx % 2)),
      e: Math.max(0, s1.e + (idx % 2 === 0 ? 1 : -1)),
      r: s1.r,
      q: s1.q,
      p: s1.p,
      t: s1.t,
    };

    const teamScores: JudgeScoreRecord[] = [];

    // Judge 1 scorecard
    const total1 = s1.l + s1.e + s1.r + s1.q + s1.p + s1.t;
    teamScores.push({
      id: `score-${team.id}-j1`,
      judgeId: judges[0].id,
      judgeName: judges[0].name,
      teamId: team.id,
      scores: {
        logical_structure: s1.l,
        evidence_use: s1.e,
        rebuttal: s1.r,
        resource_questioning: s1.q,
        presentation_teamwork: s1.p,
        time_management: s1.t,
      },
      totalScore: total1,
      comments: 'Strong legal precedents cited; articulate rebuttal presentation.',
      submittedAt: new Date('2026-09-19T17:15:00Z').toISOString(),
      isSubmitted: true,
      isLocked: true,
      lockedAt: new Date('2026-09-19T17:16:00Z').toISOString(),
      lockedBy: judges[0].name,
    });

    // Judge 2 scorecard
    const total2 = s2.l + s2.e + s2.r + s2.q + s2.p + s2.t;
    teamScores.push({
      id: `score-${team.id}-j2`,
      judgeId: judges[1].id,
      judgeName: judges[1].name,
      teamId: team.id,
      scores: {
        logical_structure: s2.l,
        evidence_use: s2.e,
        rebuttal: s2.r,
        resource_questioning: s2.q,
        presentation_teamwork: s2.p,
        time_management: s2.t,
      },
      totalScore: total2,
      comments: 'Sound evidentiary handling. Sharp cross-examination of resource person.',
      submittedAt: new Date('2026-09-19T17:20:00Z').toISOString(),
      isSubmitted: true,
      isLocked: true,
      lockedAt: new Date('2026-09-19T17:21:00Z').toISOString(),
      lockedBy: judges[1].name,
    });

    scores[team.id] = teamScores;
  });

  return scores;
}

/**
 * Generates initial demo Secret Agent guessing entries for the 4 teams.
 * Rules: 1-5 guesses per team. Correct = +30, Incorrect = -20, No guess = 0.
 * NOTE: Confidential identities are strictly shielded.
 */
export function generateInitialRound4AgentGuesses(
  teams: Team[]
): Record<string, AgentGuessingRecord> {
  const records: Record<string, AgentGuessingRecord> = {};
  const top4 = teams.slice(0, 4);

  top4.forEach((team, idx) => {
    // Team 0: 2 guesses (2 correct) -> +60
    // Team 1: 1 guess (1 correct) -> +30
    // Team 2: 2 guesses (1 correct, 1 wrong) -> +10
    // Team 3: 1 guess (1 wrong) -> -20
    const guessConfigs = [
      { total: 2, correct: 2, wrong: 0, pts: 60 },
      { total: 1, correct: 1, wrong: 0, pts: 30 },
      { total: 2, correct: 1, wrong: 1, pts: 10 },
      { total: 1, correct: 0, wrong: 1, pts: -20 },
    ];
    const cfg = guessConfigs[idx] || guessConfigs[0];

    records[team.id] = {
      teamId: team.id,
      outcome: cfg.wrong === 0 ? 'correct' : cfg.correct > 0 ? 'correct' : 'incorrect',
      pointsAwarded: cfg.pts,
      isVerified: true,
      verifiedBy: 'Chief-Marshal',
      verifiedAt: new Date('2026-09-19T17:00:00Z').toISOString(),
      notes: `Audited ${cfg.total} suspect accusation(s): ${cfg.correct} confirmed correct, ${cfg.wrong} confirmed incorrect.`,
      totalGuesses: cfg.total,
      correctGuesses: cfg.correct,
      wrongGuesses: cfg.wrong,
      guesses: Array.from({ length: cfg.total }, (_, gIdx) => ({
        suspectId: `suspect-${idx}-${gIdx + 1}`,
        suspectName: `Suspect Agent ${gIdx + 1}`,
        isCorrect: gIdx < cfg.correct,
      })),
    };
  });

  return records;
}
