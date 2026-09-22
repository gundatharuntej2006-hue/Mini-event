export type FinaleStatus =
  | 'not_started'
  | 'in_progress'
  | 'completed'
  | 'pending_review'
  | 'finalized';

export type FinaleReviewStatus =
  | 'Round 4 Pending'
  | 'Finalist Discrepancy'
  | 'Rules Unconfirmed'
  | 'Awaiting Scores'
  | 'Scores Incomplete'
  | 'Tie Review Needed'
  | 'Ready for Finalization'
  | 'Finalized Champion'
  | 'Finalized 1st Runner Up'
  | 'Finalized 2nd Runner Up'
  | 'Finalized';

export interface FinaleScoringCriterion {
  id: string;
  name: string;
  maxMarks: number;
  weight: number; // Multiplier (e.g. 1.0)
  description?: string;
  isConfirmed: boolean; // Pending official confirmation by organizers
}

export interface FinaleScorecard {
  teamId: string;
  judgeName: string;
  scores: Record<string, number | null>; // categoryId -> score (null if unentered, NEVER treated as zero)
  totalScore: number | null;
  isComplete: boolean;
  submittedAt?: string | null;
  comments?: string;
  lastEditedBy?: string | null;
  lastEditedAt?: string | null;
}

export interface FinaleSecretAgentVerdict {
  teamId: string;
  suspectedAgentNameOrId?: string;
  actualAgentNameOrId?: string;
  isCorrect: boolean | null; // null if unrecorded/pending
  bonusPoints: number | null; // null if unconfigured
  penaltyPoints: number | null;
  isVerified: boolean;
  verifiedBy?: string | null;
  verifiedAt?: string | null;
  notes?: string;
}

export interface FinaleScoreBreakdown {
  teamId: string;
  round4CarriedScore: number | null;
  round4Weight: number; // e.g. 0.2 (20%)
  round4Contribution: number;
  finaleActivityScore: number | null;
  finaleActivityWeight: number; // e.g. 1.0 (100%)
  finaleActivityContribution: number | null;
  agentAdjustment: number;
  totalFinaleScore: number | null;
  isComplete: boolean;
  missingComponents: string[];
}

export interface TeamFinaleRecord {
  teamId: string;
  teamNumber: number;
  teamName: string;
  round4Rank: number;
  round4Score: number | null;
  round4QualificationStatus: string;
  status: FinaleStatus;
  reviewStatus: FinaleReviewStatus;
  scorecard: FinaleScorecard;
  agentVerdict?: FinaleSecretAgentVerdict;
  scoreBreakdown: FinaleScoreBreakdown;
  placement?: 1 | 2 | 3 | null;
  placementTitle?: 'Grand Champion' | '1st Runner Up' | '2nd Runner Up' | null;
  tieRequiresReview?: boolean;
  tieReason?: string;
}

export interface FinaleChecklistItem {
  id: string;
  label: string;
  passed: boolean;
  details?: string;
  severity: 'blocker' | 'warning';
}

export interface FinaleEngineResult {
  records: TeamFinaleRecord[];
  canFinalize: boolean;
  blockReason?: string | null;
  checklist: FinaleChecklistItem[];
  tiesAffectingPlacement: boolean;
  championTeamId?: string | null;
  runnerUp1TeamId?: string | null;
  runnerUp2TeamId?: string | null;
}

export interface FinaleConfig {
  isScoringRulesConfirmed: boolean; // Pending official organizer confirmation
  confirmedAt?: string | null;
  confirmedBy?: string | null;
  criteria: FinaleScoringCriterion[];
  round4ScoreCarriedOver: boolean;
  round4ScoreWeight: number; // Suggested: 0.2 (20%)
  finaleActivityWeight: number; // Suggested: 1.0 (100%)
  agentBonusPointsForCorrect: number | null; // Configurable: null = unconfirmed
  agentPenaltyPointsForIncorrect: number | null;
  scoringDirection: 'higher_wins' | 'lower_wins';
  isFinalized: boolean;
  finalizedAt?: string | null;
  finalizedBy?: string | null;
}

export interface FinaleSummaryStats {
  round4Finalized: boolean;
  eligibleTeamsCount: number; // Expected: 3
  rulesConfirmed: boolean;
  scorecardsCompletedCount: number; // 0..3
  agentVerdictsVerifiedCount: number; // 0..3
  canFinalize: boolean;
  isFinalized: boolean;
  championTeamName?: string | null;
  runnerUp1TeamName?: string | null;
  runnerUp2TeamName?: string | null;
}

export interface FinaleData {
  config: FinaleConfig;
  records: TeamFinaleRecord[];
  stats: FinaleSummaryStats;
  engine: FinaleEngineResult;
  round4Finalized: boolean;
  round4QualifiedTeamsCount: number;
}
