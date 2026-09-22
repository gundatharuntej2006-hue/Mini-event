import { Team } from '../types/team';
import { TeamRound1Record, Round1Config, MiniRoundTiming, CheckpointRecord } from '../types/round1';
import { computeTeamTotals } from '../utils/round1Scoring';

export const DEFAULT_ROUND1_CONFIG: Round1Config = {
  // DEMO DEFAULT: 120 seconds (2 mins) per hint.
  // NOTE: Official penalty duration is not confirmed by organizers and is subject to change.
  penaltyPerHintSeconds: 120,
  checkpointNames: [
    'Checkpoint 1 [Location TBD]',
    'Checkpoint 2 [Location TBD]',
    'Checkpoint 3 [Location TBD]',
  ],
  isFinalized: false,
  finalizedAt: null,
  hiddenCodeRecovered: false,
  hiddenCodeRecoveredByTeamId: null,
  hiddenCodeRecoveredAt: null,
  hiddenCodeNotes: 'Code Fragment #01 concealment location pending official organizer assignment. Physical tag recovery.',
};

function createMiniRound(
  mrNum: 1 | 2 | 3,
  checkpointNames: string[],
  status: 'Not Started' | 'In Progress' | 'Completed',
  startHour: number,
  startMinute: number,
  durationMinutes: number,
  hints: number,
  penaltyPerHintSeconds: number = 120
): MiniRoundTiming {
  const today = new Date();
  const baseDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());

  const makeIso = (h: number, m: number, s: number) => {
    const d = new Date(baseDate);
    d.setHours(h, m, s, 0);
    return d.toISOString();
  };

  const checkpoints: CheckpointRecord[] = checkpointNames.map((name, i) => {
    let arrival: string | null = null;
    if (status === 'Completed' || (status === 'In Progress' && i < 2)) {
      const offset = Math.round((durationMinutes * 60 * (i + 1)) / 4);
      const totalSecs = startMinute * 60 + offset;
      const h = startHour + Math.floor(totalSecs / 3600);
      const m = Math.floor((totalSecs % 3600) / 60);
      const s = totalSecs % 60;
      arrival = makeIso(h, m, s);
    }
    return {
      checkpointId: `cp-${mrNum}-${i + 1}`,
      name,
      arrivalTime: arrival,
    };
  });

  if (status === 'Not Started') {
    return {
      miniRoundNumber: mrNum,
      status: 'Not Started',
      checkpoints,
      hintsUsed: 0,
      durationSeconds: null,
      hintPenaltySeconds: 0,
      adjustedSeconds: null,
    };
  }

  const startTime = makeIso(startHour, startMinute, 0);

  if (status === 'In Progress') {
    return {
      miniRoundNumber: mrNum,
      status: 'In Progress',
      startTime,
      completionTime: null,
      checkpoints,
      hintsUsed: hints,
      durationSeconds: null,
      hintPenaltySeconds: hints * penaltyPerHintSeconds,
      adjustedSeconds: null,
    };
  }

  // Completed
  const endTotalSecs = startMinute * 60 + durationMinutes * 60;
  const endH = startHour + Math.floor(endTotalSecs / 3600);
  const endM = Math.floor((endTotalSecs % 3600) / 60);
  const endS = endTotalSecs % 60;
  const completionTime = makeIso(endH, endM, endS);
  const durationSeconds = durationMinutes * 60;
  const hintPenaltySeconds = hints * penaltyPerHintSeconds;

  return {
    miniRoundNumber: mrNum,
    status: 'Completed',
    startTime,
    completionTime,
    checkpoints,
    hintsUsed: hints,
    durationSeconds,
    hintPenaltySeconds,
    adjustedSeconds: durationSeconds + hintPenaltySeconds,
  };
}

export function generateInitialRound1Records(
  teams: Team[],
  config: Round1Config = DEFAULT_ROUND1_CONFIG
): TeamRound1Record[] {
  return teams.map((team, idx) => {
    const cpNames = config.checkpointNames;

    let mr1: MiniRoundTiming;
    let mr2: MiniRoundTiming;
    let mr3: MiniRoundTiming;

    if (idx < 26) {
      // Completed teams
      // Baseline durations between 12m and 26m
      const baseD1 = 13 + (idx % 7);
      const baseD2 = 14 + ((idx * 3) % 9);
      const baseD3 = 12 + ((idx * 5) % 8);
      const hints1 = idx % 4 === 0 ? 1 : 0;
      const hints2 = idx % 5 === 0 ? 1 : idx % 9 === 0 ? 2 : 0;
      const hints3 = idx % 6 === 0 ? 1 : 0;

      // Ensure Team 8 and Team 9 have tied adjusted total time to showcase tie-breaker
      let d1 = baseD1;
      let d2 = baseD2;
      let d3 = baseD3;
      let h1 = hints1;
      let h2 = hints2;
      let h3 = hints3;

      if (idx === 7) {
        // Team 8: (14m + 16m + 18m) + 2m hint = 50m = 3000s. Fastest mini: 14m (840s)
        d1 = 14;
        d2 = 16;
        d3 = 18;
        h1 = 1;
        h2 = 0;
        h3 = 0;
      } else if (idx === 8) {
        // Team 9: (15m + 17m + 18m) + 0m hint = 50m = 3000s. Fastest mini: 15m (900s)
        d1 = 15;
        d2 = 17;
        d3 = 18;
        h1 = 0;
        h2 = 0;
        h3 = 0;
      }

      mr1 = createMiniRound(1, cpNames, 'Completed', 10, 0, d1, h1, config.penaltyPerHintSeconds);
      mr2 = createMiniRound(2, cpNames, 'Completed', 10, 30, d2, h2, config.penaltyPerHintSeconds);
      mr3 = createMiniRound(3, cpNames, 'Completed', 11, 0, d3, h3, config.penaltyPerHintSeconds);
    } else if (idx === 26 || idx === 27) {
      // MR1 & MR2 done, MR3 in progress
      mr1 = createMiniRound(1, cpNames, 'Completed', 10, 5, 18, 1, config.penaltyPerHintSeconds);
      mr2 = createMiniRound(2, cpNames, 'Completed', 10, 35, 20, 0, config.penaltyPerHintSeconds);
      mr3 = createMiniRound(3, cpNames, 'In Progress', 11, 10, 15, 0, config.penaltyPerHintSeconds);
    } else if (idx === 28) {
      // MR1 done, MR2 in progress
      mr1 = createMiniRound(1, cpNames, 'Completed', 10, 10, 22, 0, config.penaltyPerHintSeconds);
      mr2 = createMiniRound(2, cpNames, 'In Progress', 10, 45, 15, 1, config.penaltyPerHintSeconds);
      mr3 = createMiniRound(3, cpNames, 'Not Started', 11, 15, 0, 0, config.penaltyPerHintSeconds);
    } else {
      // MR1 not started
      mr1 = createMiniRound(1, cpNames, 'Not Started', 10, 0, 0, 0, config.penaltyPerHintSeconds);
      mr2 = createMiniRound(2, cpNames, 'Not Started', 10, 0, 0, 0, config.penaltyPerHintSeconds);
      mr3 = createMiniRound(3, cpNames, 'Not Started', 10, 0, 0, 0, config.penaltyPerHintSeconds);
    }

    const rawRecord: TeamRound1Record = {
      teamId: team.id,
      teamNumber: team.teamNumber,
      teamName: team.name,
      miniRounds: [mr1, mr2, mr3],
      totalPenaltySeconds: 0,
      isComplete: false,
      qualificationStatus: 'Incomplete',
    };

    return computeTeamTotals(rawRecord, config.penaltyPerHintSeconds);
  });
}
