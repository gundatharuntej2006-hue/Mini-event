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
 * Generates initial demo pairings for the 8 Round 4 finalist teams.
 * Pairs teams 2-by-2 into 4 matchups with official fictional case placeholders.
 */
export function generateInitialRound4Pairs(teams: Team[]): TeamPair[] {
  const top8 = teams.slice(0, 8);
  const baseTime = new Date('2026-09-19T16:00:00Z').getTime();

  const caseTemplates = [
    {
      id: 'CASE-401',
      name: 'State vs. CyberCorp Protocol Breach (Data Theft Liability)',
      details: 'Discovery docket Ref: CC-2026-BMSIT. Focus on negligence and encrypted payload attribution.',
    },
    {
      id: 'CASE-402',
      name: 'Autonomous Systems Labs vs. Department of Transportation',
      details: 'Algorithmic vehicle collision during closed-course telemetry trials.',
    },
    {
      id: 'CASE-403',
      name: 'In Re Digital Asset Arbitrage & Market Manipulation',
      details: 'Offshore token liquidity pool draining via flash-loan exploit contracts.',
    },
    {
      id: 'CASE-404',
      name: 'Campus Research IP Dispute: Quantum Cipher Key Rights',
      details: 'Trade secret misappropriation claim by former principal student investigators.',
    },
  ];

  const pairs: TeamPair[] = [];

  for (let i = 0; i < 4; i++) {
    const teamA = top8[i * 2];
    const teamB = top8[i * 2 + 1];
    const cTemplate = caseTemplates[i];

    const stages = createInitialPairStages();

    // Set realistic stage progression:
    // Pair 1 & Pair 2: All 5 stages complete
    // Pair 3: prep_1, hearing_1, file_exchange done, prep_2 in progress
    // Pair 4: prep_1, hearing_1 done, file_exchange in progress
    if (i < 2) {
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
    } else if (i === 2) {
      stages.prep_1.status = 'completed';
      stages.prep_1.startedAt = new Date(baseTime).toISOString();
      stages.prep_1.endedAt = new Date(baseTime + 40 * 60000).toISOString();
      stages.prep_1.actualDurationSeconds = 2400;

      stages.hearing_1.status = 'completed';
      stages.hearing_1.startedAt = new Date(baseTime + 42 * 60000).toISOString();
      stages.hearing_1.endedAt = new Date(baseTime + 63 * 60000).toISOString();
      stages.hearing_1.actualDurationSeconds = 1260;

      stages.file_exchange.status = 'completed';
      stages.file_exchange.startedAt = new Date(baseTime + 64 * 60000).toISOString();
      stages.file_exchange.endedAt = new Date(baseTime + 69 * 60000).toISOString();
      stages.file_exchange.actualDurationSeconds = 300;

      stages.prep_2.status = 'in_progress';
      stages.prep_2.startedAt = new Date(baseTime + 70 * 60000).toISOString();
    } else {
      stages.prep_1.status = 'completed';
      stages.prep_1.startedAt = new Date(baseTime).toISOString();
      stages.prep_1.endedAt = new Date(baseTime + 40 * 60000).toISOString();
      stages.prep_1.actualDurationSeconds = 2400;

      stages.hearing_1.status = 'completed';
      stages.hearing_1.startedAt = new Date(baseTime + 42 * 60000).toISOString();
      stages.hearing_1.endedAt = new Date(baseTime + 62 * 60000).toISOString();
      stages.hearing_1.actualDurationSeconds = 1200;

      stages.file_exchange.status = 'in_progress';
      stages.file_exchange.startedAt = new Date(baseTime + 65 * 60000).toISOString();
    }

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
        hasReceivedOpposingFile: i < 3,
        opposingFileReceivedAt: i < 3 ? new Date(baseTime + 68 * 60000).toISOString() : null,
      },
      teamBAssignment: {
        teamId: teamB ? teamB.id : '',
        side: 'Defense / Respondent',
        hasReceivedCaseFile: true,
        caseFileReceivedAt: new Date(baseTime - 300000).toISOString(),
        hasReceivedOpposingFile: i < 3,
        opposingFileReceivedAt: i < 3 ? new Date(baseTime + 68 * 60000).toISOString() : null,
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
    'Prof. K. N. Rao (Cryptographic Financial Systems)',
    'Adv. Meera Sen (Intellectual Property Specialist)',
  ];

  pairs.forEach((p, idx) => {
    const rpId = `rp-${idx + 1}`;
    records[rpId] = {
      id: rpId,
      pairId: p.pairId,
      nameOrIdentifier: rpNames[idx] || `Resource Person ${idx + 1} [TBD]`,
      assignedCaseName: p.caseName,
      questions: [
        {
          id: `q-${idx + 1}-1`,
          teamId: p.teamAId || '',
          questionText: 'Clarification regarding server logs and server clock drift during file transfer.',
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
      isQuestioningComplete: idx < 2,
    };
  });

  return records;
}

/**
 * Generates initial demo Judge scorecards for the 8 teams.
 */
export function generateInitialRound4JudgeScores(
  teams: Team[]
): Record<string, JudgeScoreRecord[]> {
  const scores: Record<string, JudgeScoreRecord[]> = {};
  const top8 = teams.slice(0, 8);

  // 2 sample faculty judges
  const judges = [
    { id: 'judge-1', name: 'Prof. K. Venkatesh (Faculty Bench Chair)' },
    { id: 'judge-2', name: 'Adv. Sunita Rao (External Senior Advocate)' },
  ];

  // Base rubric point spreads (suggested 100-pt rubric)
  // [logical(20), evidence(20), rebuttal(20), resource(15), presentation(15), time(10)]
  const sampleRubrics = [
    { l: 19, e: 18, r: 19, q: 14, p: 14, t: 9 }, // Total 93
    { l: 18, e: 18, r: 18, q: 14, p: 14, t: 9 }, // Total 91
    { l: 18, e: 17, r: 18, q: 13, p: 14, t: 9 }, // Total 89
    { l: 17, e: 17, r: 17, q: 13, p: 14, t: 8 }, // Total 86
    { l: 17, e: 16, r: 17, q: 13, p: 13, t: 8 }, // Total 84
    { l: 16, e: 16, r: 16, q: 12, p: 13, t: 8 }, // Total 81
    { l: 15, e: 15, r: 15, q: 12, p: 12, t: 7 }, // Total 76
    { l: 14, e: 15, r: 14, q: 11, p: 12, t: 7 }, // Total 73
  ];

  top8.forEach((team, idx) => {
    // Teams 0-5 have complete submitted scores; Teams 6-7 have partial/pending
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
      isSubmitted: idx < 6,
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
      isSubmitted: idx < 5,
    });

    scores[team.id] = teamScores;
  });

  return scores;
}

/**
 * Generates initial demo Secret Agent guessing entries for the 8 teams.
 * NOTE: Confidential identities and codes are strictly protected and never exposed.
 */
export function generateInitialRound4AgentGuesses(
  teams: Team[]
): Record<string, AgentGuessingRecord> {
  const records: Record<string, AgentGuessingRecord> = {};
  const top8 = teams.slice(0, 8);

  top8.forEach((team, idx) => {
    const isCorrect = idx < 5;
    records[team.id] = {
      teamId: team.id,
      outcome: isCorrect ? 'correct' : idx === 5 ? 'incorrect' : 'pending',
      pointsAwarded: isCorrect ? 25 : idx === 5 ? 0 : null,
      isVerified: idx < 6,
      verifiedBy: idx < 6 ? 'Chief-Marshal' : null,
      verifiedAt: idx < 6 ? new Date('2026-09-19T17:00:00Z').toISOString() : null,
      notes: idx < 6 ? 'Physical suspect accusation envelope opened and audited.' : 'Pending submission verification.',
    };
  });

  return records;
}
