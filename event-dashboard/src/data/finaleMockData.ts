import { Team } from '../types/team';
import {
  FinaleScorecard,
  FinaleSecretAgentVerdict,
  FinaleScoringCriterion,
} from '../types/finale';

/**
 * Generates initial demo scorecards for the 3 Grand Finale finalist squads.
 */
export function generateInitialFinaleScorecards(
  teams: Team[],
  criteria: FinaleScoringCriterion[]
): Record<string, FinaleScorecard> {
  const top3 = teams.slice(0, 3);
  const scorecards: Record<string, FinaleScorecard> = {};

  const sampleMarks: Record<number, Record<string, number>> = {
    0: { climax_defense: 46, cross_examination: 28, synergy_decorum: 19 }, // 93
    1: { climax_defense: 44, cross_examination: 26, synergy_decorum: 18 }, // 88
    2: { climax_defense: 41, cross_examination: 25, synergy_decorum: 17 }, // 83
  };

  top3.forEach((team, idx) => {
    const marks = sampleMarks[idx] || {};
    const scoresRecord: Record<string, number | null> = {};
    let sum = 0;

    criteria.forEach((crit) => {
      const val = marks[crit.id] ?? Math.round(crit.maxMarks * 0.8);
      scoresRecord[crit.id] = val;
      sum += val;
    });

    scorecards[team.id] = {
      teamId: team.id,
      judgeName: 'Grand Faculty Tribunal Panel',
      scores: scoresRecord,
      totalScore: Number(sum.toFixed(2)),
      isComplete: true,
      submittedAt: new Date(Date.now() - 3600000).toISOString(),
      comments: `Excellent oral defense demonstrated by ${team.name} during the final assembly.`,
      lastEditedBy: 'Chief Presiding Judge',
      lastEditedAt: new Date().toISOString(),
    };
  });

  return scorecards;
}

/**
 * Generates initial secret agent unmasking verdicts for the 3 finalists.
 */
export function generateInitialFinaleAgentVerdicts(teams: Team[]): Record<string, FinaleSecretAgentVerdict> {
  const top3 = teams.slice(0, 3);
  const verdicts: Record<string, FinaleSecretAgentVerdict> = {};

  top3.forEach((team, idx) => {
    verdicts[team.id] = {
      teamId: team.id,
      suspectedAgentNameOrId: `Operative from Squad T-${String((idx + 4)).padStart(2, '0')}`,
      actualAgentNameOrId: `Operative from Squad T-${String((idx + 4)).padStart(2, '0')}`,
      isCorrect: true,
      bonusPoints: 25, // Demo default bonus
      penaltyPoints: 0,
      isVerified: true,
      verifiedBy: 'Chief Marshal',
      verifiedAt: new Date().toISOString(),
      notes: 'Unmasking cryptographic token verified by organizing committee.',
    };
  });

  return verdicts;
}
