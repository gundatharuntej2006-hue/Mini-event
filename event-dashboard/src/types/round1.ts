export type MiniRoundStatus = 'Not Started' | 'In Progress' | 'Completed';

export interface CheckpointRecord {
  checkpointId: string;
  name: string;
  arrivalTime?: string | null;
}

export interface MiniRoundTiming {
  miniRoundNumber: 1 | 2 | 3;
  gateName?: string;
  status: MiniRoundStatus;
  startTime?: string | null;
  completionTime?: string | null;
  checkpoints: CheckpointRecord[];
  hintsUsed: number;
  durationSeconds?: number | null;
  hintPenaltySeconds?: number | null;
  phonePenaltiesCount?: number;
  phonePenaltySeconds?: number;
  separationPenaltiesCount?: number;
  separationPenaltySeconds?: number;
  clueTamperingDeduction?: number;
  isDisqualified?: boolean;
  disqualificationReason?: string | null;
  adjustedSeconds?: number | null;
}

export type Round1QualificationStatus =
  | 'Provisional Qualified'
  | 'Provisional Eliminated'
  | 'Incomplete'
  | 'Disqualified'
  | 'Tie Review Needed'
  | 'Finalized Qualified'
  | 'Finalized Eliminated';

export interface TeamRound1Record {
  teamId: string;
  teamNumber: number;
  teamName: string;
  miniRounds: [MiniRoundTiming, MiniRoundTiming, MiniRoundTiming];
  rawTotalSeconds?: number | null;
  hintsCount?: number;
  hintPenaltiesSeconds?: number;
  phonePenaltiesCount?: number;
  phonePenaltySeconds?: number;
  separationPenaltiesCount?: number;
  separationPenaltySeconds?: number;
  clueTamperingDeduction?: number;
  isDisqualified?: boolean;
  disqualificationReason?: string | null;
  totalPenaltySeconds: number;
  adjustedTotalSeconds?: number | null;
  fastestMiniRoundSeconds?: number | null;
  isComplete: boolean;
  rank?: number | null;
  rankPoints?: number | null;
  tieRequiresReview?: boolean;
  tieReason?: string;
  qualificationStatus: Round1QualificationStatus;
  gate1FragmentStatus?: string;
  gate2FragmentStatus?: string;
  gate3Confirmed?: boolean;
  gate3ConfirmedAt?: string | null;
  gate_1_seconds?: number | null;
  gate_2_seconds?: number | null;
  gate_3_seconds?: number | null;
}

export interface Round1Config {
  penaltyPerHintSeconds: number; // Official ODDyssey: 300s (5 min)
  penaltyPerPhoneSeconds?: number; // Official ODDyssey: 600s (10 min)
  penaltyPerSeparationSeconds?: number; // Official ODDyssey: 300s (5 min)
  clueTamperingDeductionPoints?: number; // Official ODDyssey: 20 pts
  qualifiersCount?: number; // Official: 16
  checkpointNames: string[]; // Official: GATE 42, Map Point J, Lock 48 / Stationary
  isFinalized: boolean;
  finalizedAt?: string | null;
  startedAt?: string | null;
  startedBy?: string | null;
  isStarted?: boolean;
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
  phonePenaltiesCount?: number;
  separationPenaltiesCount?: number;
  clueTamperingDeduction?: number;
  isDisqualified?: boolean;
  disqualificationReason?: string | null;
  checkpoints?: { checkpointId: string; name: string; arrivalTime?: string | null }[];
}

export interface GateCheckinRecord {
  id: string;
  team_id: string;
  team_name: string;
  round_number: number;
  gate_number: number;
  scanned_at: string;
  is_duplicate: boolean;
  attempt_number: number;
  status: string;
  notes?: string | null;
  created_at?: string | null;
}

export interface GateNavigationData {
  raw_text: string;
  system_status: string;
  fragment_info: string;
  access_key?: string | null;
  protocol_status?: string | null;
  instructions: string;
  fallback_instructions: string;
}

export interface GateCheckinResult {
  checkin_id: string;
  team_id: string;
  team_name: string;
  team_number?: number;
  round_number: number;
  gate_number: number;
  scanned_at: string;
  official_scanned_at: string;
  is_duplicate: boolean;
  attempt_number: number;
  status: string;
  notes?: string | null;
  split_seconds?: number | null;
  split_time_formatted?: string | null;
  navigation: GateNavigationData;
}

export interface RouteAllocationItem {
  team_identifier: string;
  team_id?: string | null;
  team_name?: string | null;
  cp1_location: number;
  cp1_set: string;
  cp1_completed: boolean;
  cp1_completed_at?: string | null;
  cp2_location: number;
  cp2_set: string;
  cp2_completed: boolean;
  cp2_completed_at?: string | null;
  cp3_location: number;
  cp3_set: string;
  cp3_completed: boolean;
  cp3_completed_at?: string | null;
  total_time_seconds?: number | null;
  rank?: number | null;
  is_qualified: boolean;
}

export interface RouteAllocationMatrix {
  allocations: RouteAllocationItem[];
  is_valid: boolean;
  validation_errors: string[];
  is_frozen: boolean;
  summary: {
    total_teams: number;
    cp1_completed: number;
    cp2_completed: number;
    cp3_completed: number;
    qualified_count: number;
    organizer_note?: string;
  };
}

export interface ParticipantCurrentState {
  team_identifier: string;
  team_name: string;
  current_checkpoint: number;
  current_location_number?: number | null;
  location_name?: string | null;
  location_riddle?: string | null;
  location_target?: string | null;
  qr_scanned: boolean;
  attempts_used: number;
  attempts_remaining: number;
  is_locked: boolean;
  is_round_active: boolean;
  is_complete: boolean;
  status_message: string;
}

export interface LocationVolunteerItem {
  checkpoint_number: number;
  location_number: number;
  location_name: string;
  expected_teams: {
    team_identifier: string;
    team_name: string;
    assigned_set: string;
    is_completed: boolean;
  }[];
}

export interface EnvelopePreparationItem {
  checkpoint: number;
  location: number;
  team_identifier: string;
  team_name: string;
  question_set: string;
}

export interface TeamAuditDetails {
  team_identifier: string;
  team_name: string;
  current_checkpoint: number;
  total_time_seconds?: number | null;
  is_completed: boolean;
  is_locked: boolean;
  allocations: {
    cp1: { location: number; location_name: string; set: string; completed: boolean; completed_at?: string | null };
    cp2: { location: number; location_name: string; set: string; completed: boolean; completed_at?: string | null };
    cp3: { location: number; location_name: string; set: string; completed: boolean; completed_at?: string | null };
  };
  attempts: {
    checkpoint_number: number;
    attempt_number: number;
    submitted_answer: string;
    is_correct: boolean;
    created_at: string;
  }[];
  scans: {
    checkpoint_number: number;
    location_number: number;
    is_valid_location: boolean;
    scanned_at: string;
  }[];
}


