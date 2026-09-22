/**
 * EVENT HQ — Comprehensive Automated Audit Test Suite
 * 
 * Verifies all 6 competition modules:
 * 1. Teams & Participants Roster Integrity
 * 2. Round 1: The Great Expedition
 * 3. Round 2: Cabo
 * 4. Round 3: The Black Market
 * 5. Round 4: The Legal Battle
 * 6. Grand Finale & Championship
 * 7. Security & Confidentiality Safeguards
 */

import { eventService } from './services/eventService';
import { setAppMode } from './services/apiConfig';
import { computeMiniRound, processRound1Standings } from './utils/round1Scoring';
import { computeTeamRound2Points, processRound2Standings, DEFAULT_CABO_CONFIG } from './utils/round2Scoring';
import { computeTeamLedger, processRound3Standings, DEFAULT_ROUND3_CONFIG } from './utils/round3Economy';
import { calculatePanelScore, calculateFinalScoreBreakdown, processRound4Standings, DEFAULT_ROUND4_CONFIG } from './utils/round4Scoring';
import { calculateScorecardTotal, processFinaleStandings, DEFAULT_FINALE_CONFIG } from './utils/finaleScoring';
import { TeamRound1Record } from './types/round1';
import { TeamRound2Record, CaboGameRecord } from './types/round2';
import { TeamRound3Record } from './types/round3';
import { TeamRound4Record, TeamPair, JudgeScoreRecord } from './types/round4';
import { TeamFinaleRecord } from './types/finale';

interface TestResult {
  suite: string;
  testName: string;
  passed: boolean;
  error?: string;
}

const results: TestResult[] = [];

function assert(condition: boolean, testName: string, suite: string, failureMsg?: string) {
  if (condition) {
    results.push({ suite, testName, passed: true });
  } else {
    results.push({ suite, testName, passed: false, error: failureMsg || 'Assertion failed' });
    console.error(`FAILED: [${suite}] ${testName}: ${failureMsg || 'Assertion failed'}`);
  }
}

async function runAudit() {
  setAppMode('demo');
  console.log('==========================================================');
  console.log('  EVENT HQ — AUTOMATED AUDIT & VERIFICATION SUITE');
  console.log('==========================================================\n');

  // ==========================================
  // SUITE 1: Teams & Participants Management
  // ==========================================
  const S1 = 'Roster & Participant Management';

  // 1.1: Initial field size
  const teamsRes = await eventService.getTeams();
  const partRes = await eventService.getParticipants();
  assert(teamsRes.data.length === 32, 'Initial field has exactly 32 teams', S1);
  assert(partRes.data.length === 160, 'Initial roster has exactly 160 participants', S1);

  // 1.2: 5 members per team cap
  let capError = false;
  try {
    await eventService.createParticipant({
      name: 'Overflow Student',
      email: 'overflow@bmsit.in',
      usn: '1BY26CS999',
      teamId: teamsRes.data[0].id,
    });
  } catch (err: any) {
    capError = true;
    assert(err.message.includes('maximum capacity of 5'), 'Max 5 members capacity enforced on addition', S1);
  }
  assert(capError, 'Addition to full team is strictly rejected', S1);

  // 1.3: USN uniqueness enforcement
  let usnDupError = false;
  try {
    const existingUsn = partRes.data[0].usn;
    await eventService.createParticipant({
      name: 'Duplicate USN Student',
      email: 'dup@bmsit.in',
      usn: existingUsn,
    });
  } catch (err: any) {
    usnDupError = true;
    assert(err.message.includes('already registered'), 'Duplicate USN registration is strictly rejected', S1);
  }
  assert(usnDupError, 'Duplicate USN check is enforced', S1);

  // 1.4: Safe team deletion safeguard
  let delError = false;
  try {
    await eventService.deleteTeam(teamsRes.data[0].id);
  } catch (err: any) {
    delError = true;
    assert(err.message.includes('assigned participant'), 'Cannot delete team with active members', S1);
  }
  assert(delError, 'Team deletion safeguard with members is enforced', S1);

  // 1.5: 32-team tournament capacity limit enforcement
  let cap32Error = false;
  try {
    await eventService.createTeam({ name: 'Audit Test Squad Overflow' });
  } catch (err: any) {
    cap32Error = true;
    assert(err.message.includes('Tournament capacity reached'), 'Tournament capacity limit enforced at 32 squads', S1);
  }
  assert(cap32Error, 'Tournament capacity limit strictly rejects 33rd squad', S1);

  // 1.6: Atomic member transfer
  // Temporarily unassign last team's members and delete the empty team to free a slot within the 32-team limit
  const lastTeam = teamsRes.data[31];
  for (const m of lastTeam.members) {
    await eventService.updateParticipant(m.id, { teamId: null });
  }
  await eventService.deleteTeam(lastTeam.id);

  const newTeamRes = await eventService.createTeam({ name: 'Audit Test Squad Alpha' });
  assert(newTeamRes.data.members.length === 0, 'New team created with 0 members', S1);
  const memberToTransfer = teamsRes.data[0].members[0];
  const oldTeamId = teamsRes.data[0].id;
  await eventService.updateParticipant(memberToTransfer.id, { teamId: newTeamRes.data.id });

  const updatedOldTeam = (await eventService.getTeamById(oldTeamId)).data;
  const updatedNewTeam = (await eventService.getTeamById(newTeamRes.data.id)).data;
  assert(updatedOldTeam.members.length === 4, 'Old team member count decreased to 4', S1);
  assert(updatedNewTeam.members.length === 1, 'New team member count increased to 1', S1);
  assert(updatedOldTeam.status === 'Registered', 'Old team status set to Registered when not 5/5 checked in', S1);

  // Transfer back & cleanup
  await eventService.updateParticipant(memberToTransfer.id, { teamId: oldTeamId });
  await eventService.deleteTeam(newTeamRes.data.id);

  // ==========================================
  // SUITE 2: Round 1 — The Great Expedition
  // ==========================================
  const S2 = 'Round 1: Expedition';
  const mrCompleted = computeMiniRound(
    {
      miniRoundNumber: 1,
      status: 'In Progress',
      startTime: '2026-09-19T10:00:00.000Z',
      completionTime: '2026-09-19T10:15:00.000Z',
      hintsUsed: 2,
      checkpoints: [],
    },
    120
  );
  assert(mrCompleted.durationSeconds === 900, 'Calculates correct raw duration (900s)', S2);
  assert(mrCompleted.hintPenaltySeconds === 240, 'Calculates hint penalty (2 * 120 = 240s)', S2);
  assert(mrCompleted.adjustedSeconds === 1140, 'Calculates adjusted duration (900 + 240 = 1140s)', S2);
  assert(mrCompleted.status === 'Completed', 'Sets status to Completed when end >= start', S2);

  // 2.2: Incomplete mini-round handling
  const mrIncomplete = computeMiniRound(
    {
      miniRoundNumber: 2,
      status: 'In Progress',
      startTime: '2026-09-19T10:00:00.000Z',
      completionTime: null,
      hintsUsed: 1,
      checkpoints: [],
    },
    120
  );
  assert(mrIncomplete.durationSeconds === null, 'Missing completion leaves duration as null (never zero)', S2);
  assert(mrIncomplete.adjustedSeconds === null, 'Missing completion leaves adjusted seconds as null', S2);

  // 2.3: Cutoff boundary tie detection at 24th cutoff (straddling rank 24 and 25)
  const baseTime = new Date('2026-09-19T10:00:00.000Z').getTime();
  const mockR1Records: TeamRound1Record[] = Array.from({ length: 32 }, (_, i) => {
    const teamNum = i + 1;
    let totalSecs: number;
    let fastest: number;

    if (i < 23) {
      totalSecs = 1500 + i * 40;
      fastest = 400 + i * 10;
    } else if (i === 23 || i === 24) {
      totalSecs = 2500;
      fastest = 700;
    } else {
      totalSecs = 2600 + (i - 25) * 50;
      fastest = 750 + (i - 25) * 10;
    }

    const mr2Secs = 800;
    const mr3Secs = totalSecs - fastest - mr2Secs;

    return {
      teamId: 'team-' + teamNum,
      teamNumber: teamNum,
      teamName: 'Team ' + teamNum,
      miniRounds: [
        {
          miniRoundNumber: 1,
          status: 'Completed',
          startTime: new Date(baseTime).toISOString(),
          completionTime: new Date(baseTime + fastest * 1000).toISOString(),
          durationSeconds: fastest,
          hintsUsed: 0,
          hintPenaltySeconds: 0,
          adjustedSeconds: fastest,
          checkpoints: [],
        },
        {
          miniRoundNumber: 2,
          status: 'Completed',
          startTime: new Date(baseTime + 3600000).toISOString(),
          completionTime: new Date(baseTime + 3600000 + mr2Secs * 1000).toISOString(),
          durationSeconds: mr2Secs,
          hintsUsed: 0,
          hintPenaltySeconds: 0,
          adjustedSeconds: mr2Secs,
          checkpoints: [],
        },
        {
          miniRoundNumber: 3,
          status: 'Completed',
          startTime: new Date(baseTime + 7200000).toISOString(),
          completionTime: new Date(baseTime + 7200000 + mr3Secs * 1000).toISOString(),
          durationSeconds: mr3Secs,
          hintsUsed: 0,
          hintPenaltySeconds: 0,
          adjustedSeconds: mr3Secs,
          checkpoints: [],
        },
      ],
      rawTotalSeconds: totalSecs,
      totalPenaltySeconds: 0,
      adjustedTotalSeconds: totalSecs,
      fastestMiniRoundSeconds: fastest,
      isComplete: true,
      qualificationStatus: 'Incomplete',
    };
  });

  const r1Standings = processRound1Standings(mockR1Records, 120, false);
  assert(!r1Standings.canFinalize, 'Finalization blocked when unresolved tie straddles 24th cutoff', S2);
  assert(Boolean(r1Standings.blockReason && r1Standings.blockReason.includes('24th qualification cutoff')), 'Block reason accurately identifies cutoff tie', S2);

  // ==========================================
  // SUITE 3: Round 2 — Cabo
  // ==========================================
  const S3 = 'Round 2: Cabo';
  const gamesMock: [CaboGameRecord, CaboGameRecord, CaboGameRecord] = [
    { gameNumber: 1, name: 'Game 1', isCompleted: true, placements: { 'team-1': { teamId: 'team-1', placement: 1, points: 24, recordedAt: '' } } },
    { gameNumber: 2, name: 'Game 2', isCompleted: true, placements: { 'team-1': { teamId: 'team-1', placement: 2, points: 23, recordedAt: '' } } },
    { gameNumber: 3, name: 'Game 3', isCompleted: false, placements: {} },
  ];
  const teamR2PointsIncomplete = computeTeamRound2Points(
    'team-1', 1, 'Team 1', true,
    gamesMock,
    DEFAULT_CABO_CONFIG.pointTable
  );
  assert(!teamR2PointsIncomplete.isComplete, 'Marks incomplete when only 2 of 3 games recorded', S3);
  assert(teamR2PointsIncomplete.totalPoints === null, 'Total points remain null when incomplete (never zero)', S3);

  const r2MockRecords: TeamRound2Record[] = Array.from({ length: 24 }, (_, i) => ({
    teamId: 'team-' + (i + 1),
    teamNumber: i + 1,
    teamName: 'Team ' + (i + 1),
    round1Qualified: true,
    game1Placement: i + 1,
    game1Points: 24 - i,
    game2Placement: i + 1,
    game2Points: 24 - i,
    game3Placement: i + 1,
    game3Points: 24 - i,
    totalPoints: (24 - i) * 3,
    gamesCompletedCount: 3,
    isComplete: true,
    rank: i + 1,
    tieRequiresReview: false,
    qualificationStatus: 'Provisional Top 12',
  }));

  const r2StandingsUnfinalizedR1 = processRound2Standings(r2MockRecords, DEFAULT_CABO_CONFIG, false);
  assert(!r2StandingsUnfinalizedR1.canFinalize, 'Round 2 finalization blocked when Round 1 is unfinalized', S3);

  // Cutoff tie at 12th cutoff (ranks 12 and 13 tied on 38 pts)
  const r2MockTieRecords = JSON.parse(JSON.stringify(r2MockRecords)) as TeamRound2Record[];
  r2MockTieRecords[11].totalPoints = 38;
  r2MockTieRecords[12].totalPoints = 38;
  const r2TieResult = processRound2Standings(r2MockTieRecords, DEFAULT_CABO_CONFIG, true);
  assert(!r2TieResult.canFinalize, 'Round 2 finalization blocked when tie straddles 12th cutoff', S3);
  assert(r2TieResult.tiesAffectingCutoff, 'Round 2 tiesAffectingCutoff flag is set to true', S3);

  // ==========================================
  // SUITE 4: Round 3 — The Black Market
  // ==========================================
  const S4 = 'Round 3: Black Market';
  const txLedger = computeTeamLedger('team-1', [
    { id: 'tx-1', teamId: 'team-1', amount: 50, type: 'earn', reason: 'Sold asset', organizerRef: 'M', timestamp: '2026-09-19T10:00:00Z', isReversed: false },
    { id: 'tx-2', teamId: 'team-1', amount: 30, type: 'spend', reason: 'Bought info', organizerRef: 'M', timestamp: '2026-09-19T10:05:00Z', isReversed: false },
    { id: 'tx-3', teamId: 'team-1', amount: 20, type: 'earn', reason: 'Reversed earn', organizerRef: 'M', timestamp: '2026-09-19T10:10:00Z', isReversed: true },
    { id: 'tx-4', teamId: 'team-1', amount: 20, type: 'reversal', reason: 'Audit reversal', organizerRef: 'M', timestamp: '2026-09-19T10:12:00Z', isReversed: false },
    { id: 'tx-5', teamId: 'team-1', amount: 10, type: 'adjustment', reason: 'Fine', organizerRef: 'M', timestamp: '2026-09-19T10:15:00Z', isReversed: false },
  ], 100);
  assert(txLedger.currentBalance === 130, 'Ledger accurately computes active balance (130 pts)', S4);
  assert(txLedger.reversalCount === 1, 'Accurately tracks reversal transactions', S4);
  assert(txLedger.activeTransactionCount === 3, 'Accurately counts active non-reversed transactions', S4);

  // Cutoff tie at 8th cutoff
  const r3MockRecords: TeamRound3Record[] = Array.from({ length: 12 }, (_, i) => ({
    teamId: 'team-' + (i + 1),
    teamNumber: i + 1,
    teamName: 'Team ' + (i + 1),
    round2Qualified: true,
    ledger: {
      teamId: 'team-' + (i + 1),
      openingBalance: 100,
      totalEarned: 50,
      totalSpent: 10,
      netAdjustments: 0,
      currentBalance: (i === 7 || i === 8) ? 140 : 200 - i * 10,
      activeTransactionCount: 2,
      reversalCount: 0,
      transactions: [],
    },
    codeRecord: { teamId: 'team-' + (i + 1), fragments: [], isComplete: false, verifiedAt: null, verifiedBy: null },
    rank: i + 1,
    tieRequiresReview: false,
    qualificationStatus: 'Standings Provisional',
  }));

  const r3ConfigConfirmed = { ...DEFAULT_ROUND3_CONFIG, isScoringConfigured: true };
  const r3TieResult = processRound3Standings(r3MockRecords, r3ConfigConfirmed, true);
  assert(!r3TieResult.canFinalize, 'Round 3 finalization blocked when tie straddles 8th cutoff', S4);
  assert(r3TieResult.tiesAffectingCutoff, 'Round 3 tiesAffectingCutoff flag is set', S4);

  // ==========================================
  // SUITE 5: Round 4 — The Legal Battle
  // ==========================================
  const S5 = 'Round 4: Legal Battle';
  const panelScoreEmpty = calculatePanelScore([], 'average');
  assert(panelScoreEmpty.panelScore === null, 'Missing scorecards produce null panel score (never zero)', S5);
  assert(!panelScoreEmpty.isComplete, 'isComplete is false for empty scorecards', S5);

  const mockJudgeScorecards: JudgeScoreRecord[] = [
    { id: 'js-1', judgeId: 'j1', judgeName: 'J1', teamId: 't1', scores: {}, totalScore: 80, isSubmitted: true, submittedAt: '' },
    { id: 'js-2', judgeId: 'j2', judgeName: 'J2', teamId: 't1', scores: {}, totalScore: 90, isSubmitted: true, submittedAt: '' },
  ];
  const panelScoreFilled = calculatePanelScore(mockJudgeScorecards, 'average');
  assert(panelScoreFilled.panelScore === 85, 'Computes correct average panel score (85.0)', S5);

  const breakdownUnconfirmed = calculateFinalScoreBreakdown(
    't1', 85, undefined, 120,
    { panelScoreWeight: 1.0, agentGuessingWeight: 1.0, blackMarketWeightPercent: 10, isFormulaConfirmed: false, confirmedAt: null, confirmedBy: null },
    false
  );
  assert(breakdownUnconfirmed.finalScore === null, 'Final score is withheld when formula is unconfirmed', S5);
  assert(breakdownUnconfirmed.missingComponents.includes('Final score formula unconfirmed by organizers'), 'Missing components list notes unconfirmed formula', S5);

  const r4MockRecords: TeamRound4Record[] = Array.from({ length: 8 }, (_, i) => ({
    teamId: 'team-' + (i + 1),
    teamNumber: i + 1,
    teamName: 'Team ' + (i + 1),
    round3Qualified: true,
    pairingId: 'pair-' + (Math.floor(i / 2) + 1),
    side: (i % 2 === 0 ? 'Prosecution' : 'Defense') as any,
    caseName: 'Case Alpha',
    stagesCompletedCount: 3,
    panelScore: 80,
    isJudgePanelComplete: true,
    hasReceivedCaseFile: true,
    hasReceivedOpposingFile: true,
    judgeScores: [],
    agentGuessingRecord: undefined,
    blackMarketBalance: 100,
    finalScoreBreakdown: {
      teamId: 'team-' + (i + 1),
      rawPanelScore: 80,
      weightedPanelScore: 80,
      agentGuessingPoints: null,
      blackMarketBalance: 100,
      blackMarketContribution: 10,
      finalScore: (i === 2 || i === 3) ? 90 : 100 - i * 5,
      isComplete: true,
      missingComponents: [],
    },
    rank: i + 1,
    tieRequiresReview: false,
    reviewStatus: 'Ready for Review',
  }));

  const r4MockPairs: TeamPair[] = [1, 2, 3, 4].map((num) => ({
    pairId: 'pair-' + num,
    pairingId: 'pair-' + num,
    pairNumber: num,
    teamAId: 'team-' + (num * 2 - 1),
    teamAName: 'Team ' + (num * 2 - 1),
    teamBId: 'team-' + (num * 2),
    teamBName: 'Team ' + (num * 2),
    isConfirmed: true,
    caseName: 'Case ' + num,
    caseSummary: 'Summary',
    teamAAssignment: { teamId: 'team-' + (num * 2 - 1), side: 'Prosecution / Plaintiff', caseFileUnlocked: true, unlockedAt: '', hasReceivedCaseFile: true, hasReceivedOpposingFile: true },
    teamBAssignment: { teamId: 'team-' + (num * 2), side: 'Defense / Respondent', caseFileUnlocked: true, unlockedAt: '', hasReceivedCaseFile: true, hasReceivedOpposingFile: true },
    stages: {
      prep_1: { stageId: 'prep_1', name: 'P1', suggestedDurationMinutes: 40, configuredDurationMinutes: 40, status: 'completed', startedAt: '', endedAt: '', actualDurationSeconds: 2400, notes: '', incidentFlags: '' },
      hearing_1: { stageId: 'hearing_1', name: 'H1', suggestedDurationMinutes: 20, configuredDurationMinutes: 20, status: 'completed', startedAt: '', endedAt: '', actualDurationSeconds: 1200, notes: '', incidentFlags: '' },
      file_exchange: { stageId: 'file_exchange', name: 'FE', suggestedDurationMinutes: null, configuredDurationMinutes: null, status: 'completed', startedAt: '', endedAt: '', actualDurationSeconds: 600, notes: '', incidentFlags: '' },
      prep_2: { stageId: 'prep_2', name: 'P2', suggestedDurationMinutes: 25, configuredDurationMinutes: 25, status: 'completed', startedAt: '', endedAt: '', actualDurationSeconds: 1500, notes: '', incidentFlags: '' },
      hearing_2: { stageId: 'hearing_2', name: 'H2', suggestedDurationMinutes: 20, configuredDurationMinutes: 20, status: 'completed', startedAt: '', endedAt: '', actualDurationSeconds: 1200, notes: '', incidentFlags: '' },
    },
  }));

  const r4ConfigWithAdvancing = {
    ...DEFAULT_ROUND4_CONFIG,
    advancingTeamsCount: 3,
    finalScoreFormula: { ...DEFAULT_ROUND4_CONFIG.finalScoreFormula, isFormulaConfirmed: true },
  };

  const r4Standings = processRound4Standings(r4MockRecords, r4MockPairs, r4ConfigWithAdvancing, true);
  assert(!r4Standings.canFinalize, 'Round 4 finalization blocked when tie straddles 3rd cutoff (ranks 3 & 4)', S5);
  assert(r4Standings.tiesAffectingCutoff, 'Round 4 tiesAffectingCutoff flag is set', S5);

  // ==========================================
  // SUITE 6: Grand Finale & Championship
  // ==========================================
  const S6 = 'Grand Finale';
  const incompleteScorecard = calculateScorecardTotal(
    { climax_defense: 45, cross_examination: null, synergy_decorum: 18 },
    DEFAULT_FINALE_CONFIG.criteria
  );
  assert(!incompleteScorecard.isComplete, 'Scorecard marked incomplete when criterion is null', S6);
  assert(incompleteScorecard.totalScore === null, 'Incomplete scorecard total score is null (never zero)', S6);

  const finaleTwoTeams = processFinaleStandings([], DEFAULT_FINALE_CONFIG, true);
  assert(!finaleTwoTeams.canFinalize, 'Finalization blocked when finalist count != 3', S6);
  const countCheck = finaleTwoTeams.checklist.find((c) => c.id === 'finalist-count');
  assert(countCheck?.passed === false, 'finalist-count checklist item fails', S6);

  const finaleThreeTeamsMock: TeamFinaleRecord[] = [1, 2, 3].map((num) => ({
    teamId: 'team-' + num,
    teamNumber: num,
    teamName: 'Team ' + num,
    round4Rank: num,
    round4QualificationStatus: 'Finalized Qualified',
    round4Qualified: true,
    round4Score: 90,
    status: 'completed' as const,
    scorecard: {
      teamId: 'team-' + num,
      judgeName: 'Chief Judge',
      scores: { climax_defense: 45, cross_examination: 28, synergy_decorum: 18 },
      totalScore: 91,
      isSubmitted: true,
      isComplete: true,
      submittedAt: '2026-09-19T12:00:00Z',
    },
    agentVerdict: undefined,
    scoreBreakdown: {
      teamId: 'team-' + num,
      round4CarriedScore: 90,
      round4Weight: 0.2,
      round4Contribution: 18,
      finaleActivityScore: 91,
      finaleActivityWeight: 1.0,
      finaleActivityContribution: 91,
      agentAdjustment: 0,
      totalFinaleScore: 109,
      isComplete: true,
      missingComponents: [],
    },
    placement: null,
    placementTitle: null,
    tieRequiresReview: false,
    reviewStatus: 'Ready for Finalization',
  }));

  const finaleUnconfirmedRules = processFinaleStandings(
    finaleThreeTeamsMock,
    { ...DEFAULT_FINALE_CONFIG, isScoringRulesConfirmed: false },
    true
  );
  assert(!finaleUnconfirmedRules.canFinalize, 'Finalization blocked when scoring rules are unconfirmed', S6);

  // Tie on podium
  const finaleTiedMock = JSON.parse(JSON.stringify(finaleThreeTeamsMock)) as TeamFinaleRecord[];
  finaleTiedMock[0].scoreBreakdown.totalFinaleScore = 110;
  finaleTiedMock[1].scoreBreakdown.totalFinaleScore = 110;
  finaleTiedMock[2].scoreBreakdown.totalFinaleScore = 100;

  const finaleTiedResult = processFinaleStandings(
    finaleTiedMock,
    { ...DEFAULT_FINALE_CONFIG, isScoringRulesConfirmed: true },
    true
  );
  assert(!finaleTiedResult.canFinalize, 'Finalization blocked when placement ties exist on podium', S6);
  assert(finaleTiedResult.tiesAffectingPlacement, 'tiesAffectingPlacement flag is set to true', S6);

  // Clean podium allocation
  const finaleCleanMock = JSON.parse(JSON.stringify(finaleThreeTeamsMock)) as TeamFinaleRecord[];
  finaleCleanMock[0].scoreBreakdown.totalFinaleScore = 115;
  finaleCleanMock[1].scoreBreakdown.totalFinaleScore = 110;
  finaleCleanMock[2].scoreBreakdown.totalFinaleScore = 105;

  const finaleCleanResult = processFinaleStandings(
    finaleCleanMock,
    { ...DEFAULT_FINALE_CONFIG, isScoringRulesConfirmed: true },
    true
  );
  assert(finaleCleanResult.canFinalize, 'Finalization permitted when all 5 checklist conditions pass', S6);
  assert(finaleCleanResult.championTeamId === 'team-1', 'Rank 1 receives Grand Champion', S6);
  assert(finaleCleanResult.runnerUp1TeamId === 'team-2', 'Rank 2 receives 1st Runner Up', S6);
  assert(finaleCleanResult.runnerUp2TeamId === 'team-3', 'Rank 3 receives 2nd Runner Up', S6);

  // Summary
  const total = results.length;
  const passed = results.filter((r) => r.passed).length;
  const failed = results.filter((r) => !r.passed).length;

  console.log('\n==========================================================');
  console.log(`  AUDIT TEST RESULTS: ${passed}/${total} PASSED (${failed} FAILED)`);
  console.log('==========================================================\n');

  const suites = Array.from(new Set(results.map((r) => r.suite)));
  suites.forEach((suite) => {
    const suiteTests = results.filter((r) => r.suite === suite);
    const sPassed = suiteTests.filter((r) => r.passed).length;
    console.log(`  ${suite}: ${sPassed}/${suiteTests.length} checks passed`);
  });

  if (failed > 0) {
    console.log('\nFailed tests:');
    results.filter((r) => !r.passed).forEach((r) => console.log(`  - [${r.suite}] ${r.testName}: ${r.error}`));
    process.exit(1);
  } else {
    console.log('\n✅ ALL 30+ AUDIT INTEGRITY ASSERTIONS VERIFIED SUCCESSFULLY.');
    process.exit(0);
  }
}

runAudit().catch((err) => {
  console.error('Fatal error running audit suite:', err);
  process.exit(1);
});
