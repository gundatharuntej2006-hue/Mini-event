export type Round4StageId = 'prep_1' | 'hearing_1' | 'file_exchange' | 'prep_2' | 'hearing_2';

export type StageStatus = 'not_started' | 'in_progress' | 'completed' | 'paused';

export type LegalSide = 'Prosecution / Plaintiff' | 'Defense / Respondent' | 'Unassigned';

export type JudgeAggregationMethod = 'average' | 'sum' | 'single_judge';

export type AgentGuessingOutcome = 'correct' | 'incorrect' | 'pending' | 'none';

export interface StageTimingRecord {
  stageId: Round4StageId;
  name: string;
  suggestedDurationMinutes: number | null; // e.g. 40, 20, null, 25, 20
  configuredDurationMinutes?: number | null;
  status: StageStatus;
  startedAt?: string | null;
  endedAt?: string | null;
  actualDurationSeconds?: number | null;
  notes?: string;
  incidentFlags?: string;
}

export interface TeamCaseAssignment {
  teamId: string;
  side: LegalSide;
  customSideLabel?: string;
  hasReceivedCaseFile: boolean;
  caseFileReceivedAt?: string | null;
  hasReceivedOpposingFile: boolean;
  opposingFileReceivedAt?: string | null;
}

export interface TeamPair {
  pairId: string;               // e.g. "pair-1", "pair-2", "pair-3", "pair-4"
  pairNumber: number;           // 1 to 4
  teamAId: string | null;       // Team ID
  teamBId: string | null;       // Team ID
  isConfirmed: boolean;         // Has organizer reviewed and confirmed this pairing?
  confirmedAt?: string | null;
  confirmedBy?: string | null;
  caseId?: string;              // e.g. "CASE-401"
  caseName?: string;            // e.g. "The State vs. CyberCorp Protocol Breach"
  caseDetails?: string;         // Official case filing notes
  teamAAssignment: TeamCaseAssignment;
  teamBAssignment: TeamCaseAssignment;
  stages: Record<Round4StageId, StageTimingRecord>;
  resourcePersonId?: string;
}

export interface ResourcePersonQuestion {
  id: string;
  teamId: string;
  questionText: string;
  stage: Round4StageId;
  askedAt: string;
  notes?: string;
}

export interface ResourcePersonRecord {
  id: string;
  pairId: string;
  nameOrIdentifier: string;     // e.g. "Faculty Resource Person — Prof. Sharma"
  assignedCaseName?: string;
  questions: ResourcePersonQuestion[];
  notes?: string;
  isQuestioningComplete: boolean;
}

export interface RubricCategoryConfig {
  id: string;
  name: string;
  maxMarks: number;             // e.g. 20, 20, 20, 15, 15, 10
  isConfirmed: boolean;
  description?: string;
}

export interface JudgeScoreRecord {
  id: string;
  judgeId: string;
  judgeName: string;
  teamId: string;
  scores: Record<string, number>; // categoryId -> score (0 to maxMarks)
  totalScore: number;
  comments?: string;
  submittedAt?: string | null;
  isSubmitted: boolean;
}

export interface AgentGuessingRecord {
  teamId: string;
  outcome: AgentGuessingOutcome;
  pointsAwarded: number | null; // null if unconfigured/unverified
  isVerified: boolean;
  verifiedBy?: string | null;
  verifiedAt?: string | null;
  notes?: string;
}

export interface FinalScoreFormulaConfig {
  panelScoreWeight: number;          // Default: 1.0 (100% of panel score)
  agentGuessingWeight: number;       // Default: 1.0 (100% of agent guessing points)
  blackMarketWeightPercent: number;  // Suggested: 10% (0.10)
  isFormulaConfirmed: boolean;       // Must be explicitly confirmed by organizer
  confirmedAt?: string | null;
  confirmedBy?: string | null;
}

export interface TeamFinalScoreBreakdown {
  teamId: string;
  rawPanelScore: number | null;
  weightedPanelScore: number | null;
  agentGuessingPoints: number | null;
  blackMarketBalance: number;
  blackMarketContribution: number;
  finalScore: number | null;
  isComplete: boolean;
  missingComponents: string[];
}

export interface Round4Config {
  rubricCategories: RubricCategoryConfig[];
  isRubricConfirmed: boolean;
  judgeAggregation: JudgeAggregationMethod;
  judgesList: { id: string; name: string }[];
  isGuessingRulesConfigured: boolean;
  guessingPointsForCorrect: number | null;
  guessingPointsForIncorrect: number | null;
  finalScoreFormula: FinalScoreFormulaConfig;
  advancingTeamsCount: number | null; // Configurable: null = unconfirmed (e.g. Top 3 for Grand Finale)
  pairingsConfirmed?: boolean;
  pairingsConfirmedAt?: string | null;
  pairingsConfirmedBy?: string | null;
  isFinalized: boolean;
  finalizedAt?: string | null;
}

export type Round4ReviewStatus =
  | 'Round 3 Pending'
  | 'Pending Pairing'
  | 'Pairing Unconfirmed'
  | 'Case Unassigned'
  | 'Preparation Stage'
  | 'Hearing Stage'
  | 'Awaiting Scores'
  | 'Scores Incomplete'
  | 'Ready for Review'
  | 'Tie Review Needed'
  | 'Formula Unconfirmed'
  | 'Finalized Qualified'
  | 'Finalized Eliminated';

export interface TeamRound4Record {
  teamId: string;
  teamNumber: number;
  teamName: string;
  pairId?: string | null;
  pairNumber?: number | null;
  opponentTeamId?: string | null;
  opponentTeamName?: string | null;
  side: LegalSide;
  caseName?: string | null;
  hasReceivedCaseFile: boolean;
  hasReceivedOpposingFile: boolean;
  stagesCompletedCount: number;
  judgeScores: JudgeScoreRecord[];
  panelScore: number | null;
  isJudgePanelComplete: boolean;
  agentGuessingRecord?: AgentGuessingRecord;
  blackMarketBalance: number;
  finalScoreBreakdown: TeamFinalScoreBreakdown;
  rank?: number | null;
  tieRequiresReview?: boolean;
  tieReason?: string;
  reviewStatus: Round4ReviewStatus;
}

export interface Round4ChecklistItem {
  id: string;
  label: string;
  passed: boolean;
  details?: string;
  severity: 'blocker' | 'warning';
}

export interface Round4EngineResult {
  records: TeamRound4Record[];
  canFinalize: boolean;
  blockReason?: string | null;
  checklist: Round4ChecklistItem[];
  tiesAffectingCutoff: boolean;
  advancingTeamIds: string[];
  eliminatedTeamIds: string[];
}

export interface Round4SummaryStats {
  round3Finalized: boolean;
  eligibleTeamsCount: number;        // 8 expected
  pairsConfiguredCount: number;      // 4 expected
  pairingsConfirmed: boolean;
  casesAssignedCount: number;
  prep1CompletedCount: number;
  hearing1CompletedCount: number;
  fileExchangeCompletedCount: number;
  prep2CompletedCount: number;
  hearing2CompletedCount: number;
  judgingCompletedCount: number;
  agentGuessesVerifiedCount: number;
  scoringFormulaConfirmed: boolean;
  isRubricConfirmed: boolean;
  canFinalize: boolean;
  isFinalized: boolean;
}

export interface Round4Data {
  config: Round4Config;
  pairs: TeamPair[];
  resourcePersons: Record<string, ResourcePersonRecord>;
  judgeScores: Record<string, JudgeScoreRecord[]>;
  agentGuesses: Record<string, AgentGuessingRecord>;
  records: TeamRound4Record[];
  stats: Round4SummaryStats;
  engine: Round4EngineResult;
  round3Finalized: boolean;
  round3QualifiedTeamsCount: number;
}
