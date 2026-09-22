export type MiniRoundStatus = 'Not Started' | 'In Progress' | 'Completed';

export interface CheckpointRecord {
  checkpointId: string;
  name: string;
  arrivalTime?: string | null;
}

export interface MiniRoundTiming {
  miniRoundNumber: 1 | 2 | 3;
  status: MiniRoundStatus;
  startTime?: string | null;
  completionTime?: string | null;
  checkpoints: CheckpointRecord[];
  hintsUsed: number;
  durationSeconds?: number | null;
  hintPenaltySeconds?: number | null;
  adjustedSeconds?: number | null;
}

export type Round1QualificationStatus =
  | 'Provisional Qualified'
  | 'Provisional Eliminated'
  | 'Incomplete'
  | 'Tie Review Needed'
  | 'Finalized Qualified'
  | 'Finalized Eliminated';

export interface TeamRound1Record {
  teamId: string;
  teamNumber: number;
  teamName: string;
  miniRounds: [MiniRoundTiming, MiniRoundTiming, MiniRoundTiming];
  rawTotalSeconds?: number | null;
  totalPenaltySeconds: number;
  adjustedTotalSeconds?: number | null;
  fastestMiniRoundSeconds?: number | null;
  isComplete: boolean;
  rank?: number | null;
  tieRequiresReview?: boolean;
  tieReason?: string;
  qualificationStatus: Round1QualificationStatus;
}

export interface Round1Config {
  penaltyPerHintSeconds: number; // Demo default: 120s (2 min). Unconfirmed rule—pending official organizer confirmation.
  checkpointNames: string[]; // Configurable station placeholders (e.g. 'Checkpoint 1 [Location TBD]') until confirmed by organizers.
  isFinalized: boolean;
  finalizedAt?: string | null;
  hiddenCodeRecovered: boolean;
  hiddenCodeRecoveredByTeamId?: string | null;
  hiddenCodeRecoveredAt?: string | null;
  hiddenCodeNotes?: string;
}

export interface UpdateMiniRoundTimingInput {
  miniRoundNumber: 1 | 2 | 3;
  startTime?: string | null;
  completionTime?: string | null;
  hintsUsed?: number;
  checkpoints?: { checkpointId: string; name: string; arrivalTime?: string | null }[];
}
