import { Team } from '../types/team';
import { CaboGameRecord, CaboConfig } from '../types/round2';
import { DEFAULT_CABO_CONFIG } from '../utils/round2Scoring';

/**
 * Generates initial Cabo games with unplayed state (0/16 tables logged)
 * for the 16 qualified teams under official ODDyssey specifications.
 */
export function generateInitialCaboGames(
  _qualifiedTeams?: Team[],
  _config: CaboConfig = DEFAULT_CABO_CONFIG
): [CaboGameRecord, CaboGameRecord, CaboGameRecord] {
  const game1: CaboGameRecord = {
    gameNumber: 1,
    name: 'Cabo Game 1',
    isCompleted: false,
    placements: {},
  };

  const game2: CaboGameRecord = {
    gameNumber: 2,
    name: 'Cabo Game 2',
    isCompleted: false,
    placements: {},
  };

  const game3: CaboGameRecord = {
    gameNumber: 3,
    name: 'Cabo Game 3',
    isCompleted: false,
    placements: {},
  };

  return [game1, game2, game3];
}
