import { Team } from '../types/team';
import { CaboGameRecord, CaboConfig } from '../types/round2';
import { DEFAULT_CABO_CONFIG } from '../utils/round2Scoring';

/**
 * Generates initial Cabo games with realistic mock data for 24 teams.
 * In the default state:
 * - Game 1 is completed (24/24 teams placed)
 * - Game 2 is completed (24/24 teams placed)
 * - Game 3 has 20/24 teams placed (4 teams in progress/pending)
 * This allows testing both complete and incomplete states out of the box.
 */
export function generateInitialCaboGames(
  qualifiedTeams: Team[],
  config: CaboConfig = DEFAULT_CABO_CONFIG
): [CaboGameRecord, CaboGameRecord, CaboGameRecord] {
  const g1Placements: Record<string, { teamId: string; placement: number; points: number; recordedAt: string }> = {};
  const g2Placements: Record<string, { teamId: string; placement: number; points: number; recordedAt: string }> = {};
  const g3Placements: Record<string, { teamId: string; placement: number; points: number; recordedAt: string }> = {};

  const now = new Date();
  const makeTime = (offsetMinutes: number) =>
    new Date(now.getTime() - offsetMinutes * 60000).toISOString();

  // Create a realistic permutation of placements for each game
  // Ensure exactly 1..24 are assigned uniquely
  const n = qualifiedTeams.length; // Expected 24

  // Game 1 permutation
  const perm1 = Array.from({ length: n }, (_, i) => i + 1);

  // Game 2 permutation (different order)
  const perm2: number[] = [];
  for (let i = 0; i < n; i++) {
    perm2.push(((i * 7 + 5) % n) + 1);
  }

  // Game 3 permutation
  const perm3: number[] = [];
  for (let i = 0; i < n; i++) {
    perm3.push(((i * 11 + 3) % n) + 1);
  }

  qualifiedTeams.forEach((team, idx) => {
    if (idx < n) {
      // Game 1: all teams placed
      const p1 = perm1[idx];
      const pts1 = config.pointTable[p1] ?? 0;
      g1Placements[team.id] = {
        teamId: team.id,
        placement: p1,
        points: pts1,
        recordedAt: makeTime(90 - idx),
      };

      // Game 2: all teams placed
      const p2 = perm2[idx];
      const pts2 = config.pointTable[p2] ?? 0;
      g2Placements[team.id] = {
        teamId: team.id,
        placement: p2,
        points: pts2,
        recordedAt: makeTime(45 - idx),
      };

      // Game 3: 20 teams placed, 4 teams pending to demonstrate incomplete results rule
      if (idx < 20) {
        const p3 = perm3[idx];
        const pts3 = config.pointTable[p3] ?? 0;
        g3Placements[team.id] = {
          teamId: team.id,
          placement: p3,
          points: pts3,
          recordedAt: makeTime(15 - idx),
        };
      }
    }
  });

  const game1: CaboGameRecord = {
    gameNumber: 1,
    name: 'Cabo Game 1',
    isCompleted: Object.keys(g1Placements).length === n,
    placements: g1Placements,
  };

  const game2: CaboGameRecord = {
    gameNumber: 2,
    name: 'Cabo Game 2',
    isCompleted: Object.keys(g2Placements).length === n,
    placements: g2Placements,
  };

  const game3: CaboGameRecord = {
    gameNumber: 3,
    name: 'Cabo Game 3',
    isCompleted: Object.keys(g3Placements).length === n,
    placements: g3Placements,
  };

  return [game1, game2, game3];
}
