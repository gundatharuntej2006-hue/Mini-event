import { apiClient } from './apiClient';
import {
  Team,
  Participant,
  DashboardOverviewData,
  ApiResponse,
  CreateTeamInput,
  UpdateTeamInput,
  CreateParticipantInput,
  UpdateParticipantInput,
  RoundInfo,
} from '../types';
import {
  Submission,
  IntegrationSettings,
  IntegrationSettingsUpdate,
  ExternalRegistrationInput,
} from '../types/integration';

export interface FinalizeRoundPayload {
  finalizedBy?: string;
  notes?: string;
  overrideDiscrepancy?: boolean;
}

export interface FinalizeRoundResult {
  success: boolean;
  roundNumber: number;
  qualifiedTeamIds: string[];
  totalEligible: number;
  message: string;
}

export interface BackendSettings {
  eventName: string;
  eventDate: string;
  venue: string;
  totalSquadsLimit: number;
  squadSizeLimit: number;
  isRegistrationLocked: boolean;
  activeRoundId: number;
}

export interface BackendRound1Record {
  id: string;
  teamId: string;
  teamName?: string;
  teamIdentifier?: string;
  miniRounds: Array<{
    roundNumber: number;
    startTime?: string | null;
    completionTime?: string | null;
    durationSeconds?: number | null;
    hintsUsed: number;
    hintPenaltySeconds: number;
    adjustedSeconds?: number | null;
    isCompleted: boolean;
  }>;
  rawTotalSeconds?: number | null;
  totalPenaltySeconds: number;
  adjustedTotalSeconds?: number | null;
  fastestMiniRoundSeconds?: number | null;
  hiddenCodeRecovered: boolean;
  hiddenCodeRecoveredAt?: string | null;
  hiddenCodeNotes?: string | null;
  rank?: number | null;
  qualificationStatus: string;
  tieRequiresReview: boolean;
  tieReason?: string | null;
  isComplete: boolean;
}

export interface BackendRound2Placement {
  id: string;
  gameNumber: number;
  teamId: string;
  placement: number;
  points: number;
  notes?: string;
  recordedBy?: string;
  recordedAt: string;
}

export interface BackendRound2Standing {
  teamId: string;
  teamName: string;
  teamIdentifier: string;
  game1Points?: number | null;
  game2Points?: number | null;
  game3Points?: number | null;
  totalPoints: number;
  gamesPlayed: number;
  rank?: number | null;
  qualificationStatus: string;
}

export interface BackendRound3Transaction {
  id: string;
  teamId: string;
  amount: number;
  type: 'earn' | 'spend' | 'adjustment' | 'reversal';
  reason: string;
  organizerRef?: string;
  timestamp: string;
  isReversed: boolean;
  reversalTransactionId?: string;
  notes?: string;
}

export interface BackendRound3CodeRecord {
  id: string;
  teamId: string;
  fragments: Array<{
    index: number;
    isDiscovered: boolean;
    code?: string;
    clueStation?: string;
  }>;
  isComplete: boolean;
  verifiedAt?: string;
  verifiedBy?: string;
}

export interface BackendRound3Standing {
  teamId: string;
  teamName: string;
  teamIdentifier: string;
  startingBalance: number;
  totalEarned: number;
  totalSpent: number;
  netAdjustments: number;
  currentBalance: number;
  fragmentsDiscovered: number;
  totalFragments: number;
  isCodeComplete: boolean;
  rank?: number | null;
  qualificationStatus: string;
}

export interface BackendRound4Pair {
  id: string;
  pairNumber: number;
  teamAId?: string;
  teamBId?: string;
  caseId?: string;
  caseName?: string;
  caseDetails?: string;
  teamASide?: string;
  teamBSide?: string;
  teamAHasCaseFile: boolean;
  teamBHasCaseFile: boolean;
  resourcePersonName?: string;
  resourcePersonNotes?: string;
  resourcePersonQuestions?: Array<{
    teamId: string;
    question: string;
    answer?: string;
  }>;
  isConfirmed: boolean;
  confirmedAt?: string;
  confirmedBy?: string;
}

export interface BackendRound4JudgeScore {
  id: string;
  judgeId: string;
  judgeName: string;
  teamId: string;
  scores: Record<string, number>;
  totalScore: number;
  comments?: string;
  submittedAt: string;
}

export interface BackendRound4AgentGuess {
  id: string;
  teamId: string;
  outcome: 'correct' | 'incorrect' | 'pending';
  pointsAwarded?: number;
  isVerified: boolean;
  verifiedBy?: string;
  verifiedAt?: string;
  notes?: string;
}

export interface BackendRound4Standing {
  teamId: string;
  teamName: string;
  teamIdentifier: string;
  pairNumber?: number;
  opponentTeamId?: string;
  opponentTeamName?: string;
  side?: string;
  juryScore: number;
  agentGuessPoints: number;
  totalScore: number;
  rank?: number | null;
  qualificationStatus: string;
}

export interface BackendFinaleScorecard {
  id: string;
  teamId: string;
  judgeName: string;
  scores: Record<string, number>;
  totalScore?: number;
  isComplete: boolean;
  comments?: string;
  submittedAt?: string;
}

export interface BackendFinaleAgentVerdict {
  id: string;
  teamId: string;
  suspectedAgent?: string;
  actualAgent?: string;
  isCorrect?: boolean;
  bonusPoints?: number;
  penaltyPoints?: number;
  isVerified: boolean;
  verifiedBy?: string;
  verifiedAt?: string;
  notes?: string;
}

export interface BackendFinaleStanding {
  teamId: string;
  teamName: string;
  teamIdentifier: string;
  carryoverScore: number;
  juryScore: number;
  agentVerdictScore: number;
  grandTotalScore: number;
  rank: number;
  podiumTitle: string;
}

class BackendApiService {
  // ==========================================
  // Teams & Participants
  // ==========================================
  async getTeams(): Promise<ApiResponse<Team[]>> {
    return apiClient.get<Team[]>('/teams');
  }

  async getTeam(id: string): Promise<ApiResponse<Team>> {
    return apiClient.get<Team>(`/teams/${id}`);
  }

  async createTeam(input: CreateTeamInput): Promise<ApiResponse<Team>> {
    return apiClient.post<Team>('/teams', input);
  }

  async updateTeam(id: string, input: UpdateTeamInput): Promise<ApiResponse<Team>> {
    return apiClient.put<Team>(`/teams/${id}`, input);
  }

  async deleteTeam(id: string): Promise<ApiResponse<{ id: string }>> {
    return apiClient.delete<{ id: string }>(`/teams/${id}`);
  }

  async getParticipants(): Promise<ApiResponse<Participant[]>> {
    return apiClient.get<Participant[]>('/participants');
  }

  async createParticipant(input: CreateParticipantInput): Promise<ApiResponse<Participant>> {
    return apiClient.post<Participant>('/participants', input);
  }

  async updateParticipant(id: string, input: UpdateParticipantInput): Promise<ApiResponse<Participant>> {
    return apiClient.put<Participant>(`/participants/${id}`, input);
  }

  async deleteParticipant(id: string): Promise<ApiResponse<{ id: string }>> {
    return apiClient.delete<{ id: string }>(`/participants/${id}`);
  }

  async toggleParticipantCheckIn(id: string, checkedIn?: boolean): Promise<ApiResponse<Participant>> {
    return apiClient.patch<Participant>(`/participants/${id}/check-in`, { checkedIn });
  }

  async transferParticipant(id: string, targetTeamId: string): Promise<ApiResponse<Participant>> {
    return apiClient.post<Participant>(`/participants/${id}/transfer`, { targetTeamId });
  }

  // ==========================================
  // Dashboard & Settings
  // ==========================================
  async getDashboardOverview(): Promise<ApiResponse<DashboardOverviewData>> {
    return apiClient.get<DashboardOverviewData>('/dashboard/overview');
  }

  async getSettings(): Promise<ApiResponse<BackendSettings>> {
    return apiClient.get<BackendSettings>('/settings');
  }

  async updateSettings(input: Partial<BackendSettings>): Promise<ApiResponse<BackendSettings>> {
    return apiClient.put<BackendSettings>('/settings', input);
  }

  // ==========================================
  // Tournament Rounds State & Finalization
  // ==========================================
  async getRounds(): Promise<ApiResponse<RoundInfo[]>> {
    return apiClient.get<RoundInfo[]>('/rounds');
  }

  async getRound(roundNum: number): Promise<ApiResponse<RoundInfo>> {
    return apiClient.get<RoundInfo>(`/rounds/${roundNum}`);
  }

  async updateRound(roundNum: number, payload: Partial<RoundInfo>): Promise<ApiResponse<RoundInfo>> {
    return apiClient.put<RoundInfo>(`/rounds/${roundNum}`, payload);
  }

  async finalizeRound(roundNum: number, payload: FinalizeRoundPayload): Promise<ApiResponse<FinalizeRoundResult>> {
    return apiClient.post<FinalizeRoundResult>(`/rounds/${roundNum}/finalize`, payload);
  }

  // ==========================================
  // Round 1: Clue Hunt / Expedition
  // ==========================================
  async getRound1Records(): Promise<ApiResponse<BackendRound1Record[]>> {
    return apiClient.get<BackendRound1Record[]>('/rounds/1/records');
  }

  async updateRound1Record(teamId: string, payload: {
    miniRounds?: unknown[];
    hiddenCodeRecovered?: boolean;
    hiddenCodeNotes?: string;
  }): Promise<ApiResponse<BackendRound1Record>> {
    return apiClient.put<BackendRound1Record>(`/rounds/1/records/${teamId}`, payload);
  }

  async batchUpdateRound1Records(records: unknown[]): Promise<ApiResponse<BackendRound1Record[]>> {
    return apiClient.post<BackendRound1Record[]>('/rounds/1/records/batch', { records });
  }

  // ==========================================
  // Round 2: Cabo Tournament
  // ==========================================
  async getRound2Placements(gameNumber?: number): Promise<ApiResponse<BackendRound2Placement[]>> {
    const q = gameNumber !== undefined ? `?gameNumber=${gameNumber}` : '';
    return apiClient.get<BackendRound2Placement[]>(`/rounds/2/placements${q}`);
  }

  async recordRound2Placement(payload: {
    gameNumber: number;
    teamId: string;
    placement: number;
    points?: number;
    notes?: string;
  }): Promise<ApiResponse<BackendRound2Placement>> {
    return apiClient.post<BackendRound2Placement>('/rounds/2/placements', payload);
  }

  async submitRound2Game(payload: {
    gameNumber: number;
    placements: Array<{ teamId: string; placement: number; points?: number; notes?: string }>;
  }): Promise<ApiResponse<BackendRound2Placement[]>> {
    return apiClient.post<BackendRound2Placement[]>('/rounds/2/game/submit', payload);
  }

  async getRound2Standings(): Promise<ApiResponse<BackendRound2Standing[]>> {
    return apiClient.get<BackendRound2Standing[]>('/rounds/2/standings');
  }

  // ==========================================
  // Round 3: The Black Market Economy
  // ==========================================
  async getRound3Transactions(teamId?: string): Promise<ApiResponse<BackendRound3Transaction[]>> {
    const q = teamId ? `?teamId=${teamId}` : '';
    return apiClient.get<BackendRound3Transaction[]>(`/rounds/3/transactions${q}`);
  }

  async createRound3Transaction(payload: {
    teamId: string;
    amount: number;
    type: 'earn' | 'spend' | 'adjustment';
    reason: string;
    organizerRef?: string;
    notes?: string;
  }): Promise<ApiResponse<BackendRound3Transaction>> {
    return apiClient.post<BackendRound3Transaction>('/rounds/3/transactions', payload);
  }

  async reverseRound3Transaction(transactionId: string): Promise<ApiResponse<BackendRound3Transaction>> {
    return apiClient.post<BackendRound3Transaction>(`/rounds/3/transactions/${transactionId}/reverse`, {});
  }

  async transferRound3Funds(payload: {
    fromTeamId: string;
    toTeamId: string;
    amount: number;
    reason: string;
    notes?: string;
  }): Promise<ApiResponse<[BackendRound3Transaction, BackendRound3Transaction]>> {
    return apiClient.post<[BackendRound3Transaction, BackendRound3Transaction]>('/rounds/3/transfer', payload);
  }

  async getRound3Codes(): Promise<ApiResponse<BackendRound3CodeRecord[]>> {
    return apiClient.get<BackendRound3CodeRecord[]>('/rounds/3/codes');
  }

  async updateRound3CodeFragment(payload: {
    teamId: string;
    fragmentIndex: number;
    isDiscovered: boolean;
    code?: string;
    clueStation?: string;
  }): Promise<ApiResponse<BackendRound3CodeRecord>> {
    return apiClient.put<BackendRound3CodeRecord>('/rounds/3/codes/fragment', payload);
  }

  async getRound3Standings(): Promise<ApiResponse<BackendRound3Standing[]>> {
    return apiClient.get<BackendRound3Standing[]>('/rounds/3/standings');
  }

  // ==========================================
  // Round 4: The Legal Battle
  // ==========================================
  async getRound4Pairs(): Promise<ApiResponse<BackendRound4Pair[]>> {
    return apiClient.get<BackendRound4Pair[]>('/rounds/4/pairs');
  }

  async updateRound4Pair(pairNumber: number, payload: Partial<BackendRound4Pair>): Promise<ApiResponse<BackendRound4Pair>> {
    return apiClient.put<BackendRound4Pair>(`/rounds/4/pairs/${pairNumber}`, payload);
  }

  async autoPairRound4Teams(): Promise<ApiResponse<BackendRound4Pair[]>> {
    return apiClient.post<BackendRound4Pair[]>('/rounds/4/pairs/auto', {});
  }

  async submitRound4JudgeScore(payload: {
    judgeId: string;
    judgeName: string;
    teamId: string;
    scores: Record<string, number>;
    comments?: string;
  }): Promise<ApiResponse<BackendRound4JudgeScore>> {
    return apiClient.post<BackendRound4JudgeScore>('/rounds/4/scores', payload);
  }

  async submitRound4AgentGuess(payload: {
    teamId: string;
    outcome: 'correct' | 'incorrect' | 'pending';
    pointsAwarded?: number;
    notes?: string;
  }): Promise<ApiResponse<BackendRound4AgentGuess>> {
    return apiClient.post<BackendRound4AgentGuess>('/rounds/4/agent-guess', payload);
  }

  async getRound4Standings(): Promise<ApiResponse<BackendRound4Standing[]>> {
    return apiClient.get<BackendRound4Standing[]>('/rounds/4/standings');
  }

  // ==========================================
  // Grand Finale (Round 5)
  // ==========================================
  async getFinaleScorecards(): Promise<ApiResponse<BackendFinaleScorecard[]>> {
    return apiClient.get<BackendFinaleScorecard[]>('/rounds/5/scorecards');
  }

  async submitFinaleScorecard(payload: {
    teamId: string;
    judgeName: string;
    scores: Record<string, number>;
    comments?: string;
  }): Promise<ApiResponse<BackendFinaleScorecard>> {
    return apiClient.post<BackendFinaleScorecard>('/rounds/5/scorecards', payload);
  }

  async submitFinaleAgentVerdict(payload: {
    teamId: string;
    suspectedAgent?: string;
    actualAgent?: string;
    isCorrect?: boolean;
    bonusPoints?: number;
    penaltyPoints?: number;
    notes?: string;
  }): Promise<ApiResponse<BackendFinaleAgentVerdict>> {
    return apiClient.post<BackendFinaleAgentVerdict>('/rounds/5/agent-verdict', payload);
  }

  async getFinaleStandings(): Promise<ApiResponse<BackendFinaleStanding[]>> {
    return apiClient.get<BackendFinaleStanding[]>('/rounds/5/standings');
  }

  // ==========================================
  // Google Forms & External Integrations
  // ==========================================
  async getIntegrationSettings(): Promise<ApiResponse<IntegrationSettings>> {
    return apiClient.get<IntegrationSettings>('/integrations/settings');
  }

  async updateIntegrationSettings(input: IntegrationSettingsUpdate): Promise<ApiResponse<IntegrationSettings>> {
    return apiClient.patch<IntegrationSettings>('/integrations/settings', input);
  }

  async getSubmissions(statusFilter?: string): Promise<ApiResponse<Submission[]>> {
    const query = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : '';
    return apiClient.get<Submission[]>(`/integrations/submissions${query}`);
  }

  async performSubmissionAction(
    id: string,
    action: 'approve' | 'reject' | 'retry',
    reason?: string
  ): Promise<ApiResponse<Submission>> {
    return apiClient.post<Submission>(`/integrations/submissions/${id}/action`, { action, reason });
  }

  async submitPublicRegistration(payload: ExternalRegistrationInput): Promise<ApiResponse<Submission>> {
    return apiClient.post<Submission>('/integrations/registration/public-submit', payload);
  }

  async simulateGoogleFormWebhook(testPayload?: any): Promise<ApiResponse<Submission>> {
    return apiClient.post<Submission>('/integrations/google-forms/test-payload', testPayload || {});
  }
}

export const backendApiService = new BackendApiService();
