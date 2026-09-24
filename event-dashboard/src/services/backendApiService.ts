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

export interface TeamWalletData {
  id: string;
  team_id: string;
  current_balance: number;
  total_earned: number;
  total_spent: number;
  total_penalties: number;
  is_frozen: boolean;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface WalletTransactionData {
  id: string;
  wallet_id: string;
  team_id: string;
  amount: number;
  transaction_type: string;
  reason: string;
  round_number?: number;
  balance_after: number;
  actor?: string;
  notes?: string;
  is_reversed: boolean;
  created_at: string;
}

export interface SecretAgentDossierData {
  id: string;
  team_id: string;
  participant_id: string;
  codename: string;
  status: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface SecretAgentTaskData {
  id: string;
  dossier_id: string;
  team_id: string;
  title: string;
  description: string;
  target_round: number;
  status: string;
  points_awarded: number;
  evidence?: string;
  verification_notes?: string;
  rejection_reason?: string;
  created_at: string;
  submitted_at?: string;
  verified_at?: string;
}

export interface CodeHuntStatusData {
  team_id: string;
  fragment_1_status: string;
  fragment_2_status: string;
  fragments_recovered_count: number;
  final_code_verified: boolean;
  final_code_input?: string;
  verified_at?: string;
  r4_eligible: boolean;
  gate_reason: string;
}

export interface BlackMarketPurchaseData {
  id: string;
  team_id: string;
  asset_type: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  transaction_id?: string;
  details?: Record<string, any>;
  purchased_by?: string;
  created_at: string;
}

export interface BlackMarketAuctionData {
  id: string;
  item_name: string;
  item_description?: string;
  starting_price: number;
  status: string;
  winning_bid?: number;
  winning_team_id?: string;
  bids_count: number;
  created_at: string;
}

export interface ChampionshipStandingItemData {
  team_id: string;
  team_number: number;
  team_name: string;
  legal_battle_score?: number;
  agent_guessing_points?: number;
  remaining_black_market_points: number;
  black_market_carryover_points: number;
  final_score?: number;
  rank: number;
  is_top_four: boolean;
  podium_position?: number;
  placement_title?: string;
}

export interface TopFourData {
  is_revealed: boolean;
  top_four: ChampionshipStandingItemData[];
  tie_requires_review: boolean;
  tied_teams: string[];
  message?: string;
}

export interface PodiumData {
  is_revealed: boolean;
  podium: ChampionshipStandingItemData[];
  champion?: ChampionshipStandingItemData;
  runner_up1?: ChampionshipStandingItemData;
  runner_up2?: ChampionshipStandingItemData;
  tie_requires_review: boolean;
  tied_teams: string[];
  message?: string;
}

export interface BestSecretAgentData {
  is_revealed: boolean;
  best_agent?: any;
  rankings: any[];
  tie_requires_review: boolean;
  tied_candidate_ids: string[];
  notes?: string;
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
  // Tournament Wallet & Economy Endpoints
  // ==========================================
  async getTeamWallet(teamId: string): Promise<ApiResponse<TeamWalletData>> {
    return apiClient.get<TeamWalletData>(`/teams/${teamId}/wallet`);
  }

  async getTeamWalletTransactions(teamId: string, limit: number = 50, offset: number = 0): Promise<ApiResponse<WalletTransactionData[]>> {
    return apiClient.get<WalletTransactionData[]>(`/teams/${teamId}/wallet/transactions?limit=${limit}&offset=${offset}`);
  }

  async adjustTeamWallet(teamId: string, payload: { amount: number; reason: string; notes?: string }): Promise<ApiResponse<WalletTransactionData>> {
    return apiClient.post<WalletTransactionData>(`/teams/${teamId}/wallet/adjust`, payload);
  }

  async penalizeTeamWallet(teamId: string, payload: { amount: number; reason: string; notes?: string }): Promise<ApiResponse<WalletTransactionData>> {
    return apiClient.post<WalletTransactionData>(`/teams/${teamId}/wallet/penalty`, payload);
  }

  // ==========================================
  // Round 2: Cabo Tournament Engine
  // ==========================================
  async generateCaboTables(payload?: { seed?: number; force_regenerate?: boolean }): Promise<ApiResponse<any>> {
    return apiClient.post<any>('/rounds/2/cabo/generate', payload || {});
  }

  async getCaboGameTables(gameNumber: number): Promise<ApiResponse<any[]>> {
    return apiClient.get<any[]>(`/rounds/2/cabo/games/${gameNumber}`);
  }

  async recordCaboTableScores(gameNumber: number, payload: { table_number: number; scores: any[] }): Promise<ApiResponse<any[]>> {
    return apiClient.post<any[]>(`/rounds/2/cabo/games/${gameNumber}/scores`, payload);
  }

  async getCaboStandings(): Promise<ApiResponse<any[]>> {
    return apiClient.get<any[]>('/rounds/2/cabo/standings');
  }

  async finalizeCaboRound(): Promise<ApiResponse<any>> {
    return apiClient.post<any>('/rounds/2/cabo/finalize', {});
  }

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
  // Code Hunt & Final Code Gate
  // ==========================================
  async recordFragment1(teamId: string, payload: { fragment_value: string; overwrite?: boolean }): Promise<ApiResponse<any>> {
    return apiClient.post<any>(`/code-hunt/${teamId}/fragment/1`, payload);
  }

  async recordFragment2(teamId: string, payload: { fragment_value: string; overwrite?: boolean }): Promise<ApiResponse<any>> {
    return apiClient.post<any>(`/code-hunt/${teamId}/fragment/2`, payload);
  }

  async getCodeHuntStatus(teamId: string): Promise<ApiResponse<CodeHuntStatusData>> {
    return apiClient.get<CodeHuntStatusData>(`/code-hunt/${teamId}/status`);
  }

  async verifyFinalCode(teamId: string, payload: { submitted_final_code: string }): Promise<ApiResponse<any>> {
    return apiClient.post<any>(`/code-hunt/${teamId}/verify`, payload);
  }

  async recoverMissingFragment(teamId: string, payload: { fragment_index: number }): Promise<ApiResponse<any>> {
    return apiClient.post<any>(`/code-hunt/${teamId}/recover-missing-fragment`, payload);
  }

  async getCodeHuntEligibilityR4(teamId: string): Promise<ApiResponse<any>> {
    return apiClient.get<any>(`/code-hunt/eligibility/r4/${teamId}`);
  }

  // ==========================================
  // Secret Agent Track
  // ==========================================
  async assignSecretAgent(teamId: string, payload: { participant_id: string; codename: string }): Promise<ApiResponse<SecretAgentDossierData>> {
    return apiClient.post<SecretAgentDossierData>(`/secret-agents/${teamId}/assign`, payload);
  }

  async getSecretAgentDossier(teamId: string): Promise<ApiResponse<SecretAgentDossierData>> {
    return apiClient.get<SecretAgentDossierData>(`/secret-agents/${teamId}/dossier`);
  }

  async getSecretAgentTasks(teamId: string): Promise<ApiResponse<SecretAgentTaskData[]>> {
    return apiClient.get<SecretAgentTaskData[]>(`/secret-agents/${teamId}/tasks`);
  }

  async createSecretAgentTask(teamId: string, payload: { title: string; description: string; target_round: number }): Promise<ApiResponse<SecretAgentTaskData>> {
    return apiClient.post<SecretAgentTaskData>(`/secret-agents/${teamId}/tasks`, payload);
  }

  async submitSecretAgentTask(taskId: string, payload: { evidence?: string; notes?: string }): Promise<ApiResponse<SecretAgentTaskData>> {
    return apiClient.post<SecretAgentTaskData>(`/secret-agents/tasks/${taskId}/submit`, payload);
  }

  async verifySecretAgentTask(taskId: string, payload?: { verification_notes?: string }): Promise<ApiResponse<SecretAgentTaskData>> {
    return apiClient.post<SecretAgentTaskData>(`/secret-agents/tasks/${taskId}/verify`, payload || {});
  }

  async rejectSecretAgentTask(taskId: string, payload: { reason: string }): Promise<ApiResponse<SecretAgentTaskData>> {
    return apiClient.post<SecretAgentTaskData>(`/secret-agents/tasks/${taskId}/reject`, payload);
  }

  // ==========================================
  // Round 3: The Black Market Economy
  // ==========================================
  async getMarketCatalog(): Promise<ApiResponse<any>> {
    return apiClient.get<any>('/rounds/3/catalog');
  }

  async purchaseMarketAsset(payload: {
    team_id: string;
    asset_type: string;
    quantity?: number;
    price?: number;
    details?: any;
  }): Promise<ApiResponse<BlackMarketPurchaseData>> {
    return apiClient.post<BlackMarketPurchaseData>('/rounds/3/purchase', payload);
  }

  async getTeamMarketPurchases(teamId: string): Promise<ApiResponse<BlackMarketPurchaseData[]>> {
    return apiClient.get<BlackMarketPurchaseData[]>(`/rounds/3/purchases/${teamId}`);
  }

  async createMarketAuction(payload: {
    item_name: string;
    item_description?: string;
    starting_price: number;
    asset_type?: string;
    asset_payload?: any;
  }): Promise<ApiResponse<BlackMarketAuctionData>> {
    return apiClient.post<BlackMarketAuctionData>('/rounds/3/auction', payload);
  }

  async getMarketAuctions(): Promise<ApiResponse<BlackMarketAuctionData[]>> {
    return apiClient.get<BlackMarketAuctionData[]>('/rounds/3/auctions');
  }

  async getMarketAuctionDetail(auctionId: string): Promise<ApiResponse<BlackMarketAuctionData>> {
    return apiClient.get<BlackMarketAuctionData>(`/rounds/3/auction/${auctionId}`);
  }

  async placeAuctionBid(auctionId: string, payload: { team_id: string; bid_amount: number }): Promise<ApiResponse<any>> {
    return apiClient.post<any>(`/rounds/3/auction/${auctionId}/bid`, payload);
  }

  async resolveMarketAuction(auctionId: string, payload?: { override_winner_team_id?: string; override_winning_bid?: number; notes?: string }): Promise<ApiResponse<any>> {
    return apiClient.post<any>(`/rounds/3/auction/${auctionId}/resolve`, payload || {});
  }

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

  async createRound4Pair(payload: {
    pair_number: number;
    team_a_id: string;
    team_b_id: string;
    case_name?: string;
    team_a_side?: string;
    team_b_side?: string;
  }): Promise<ApiResponse<any>> {
    return apiClient.post<any>('/rounds/4/pairs', payload);
  }

  async autoPairRound4Teams(payload?: { seed?: number }): Promise<ApiResponse<BackendRound4Pair[]>> {
    return apiClient.post<BackendRound4Pair[]>('/rounds/4/pairs/auto', payload || {});
  }

  async confirmRound4Pairs(): Promise<ApiResponse<any>> {
    return apiClient.post<any>('/rounds/4/pairs/confirm', {});
  }

  async unlockRound4Pairs(): Promise<ApiResponse<any>> {
    return apiClient.post<any>('/rounds/4/pairs/unlock', {});
  }

  async updateRound4Pair(pairNumber: number, payload: Partial<BackendRound4Pair>): Promise<ApiResponse<BackendRound4Pair>> {
    return apiClient.put<BackendRound4Pair>(`/rounds/4/pairs/${pairNumber}`, payload);
  }

  async updateRound4Stage(pairId: string, stageId: string, payload: { status?: string; actual_duration_seconds?: number }): Promise<ApiResponse<any>> {
    return apiClient.put<any>(`/rounds/4/stages/${pairId}/${stageId}`, payload);
  }

  async submitRound4JudgeScore(payload: {
    judgeId: string;
    judgeName: string;
    teamId: string;
    scores: Record<string, number>;
    comments?: string;
  }): Promise<ApiResponse<BackendRound4JudgeScore>> {
    return apiClient.post<BackendRound4JudgeScore>(`/rounds/4/judging/${payload.teamId}/scores`, {
      judge_id: payload.judgeId,
      judge_name: payload.judgeName,
      scores: payload.scores,
      comments: payload.comments,
    });
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

  async getRound4Qualification(): Promise<ApiResponse<any>> {
    return apiClient.get<any>('/rounds/4/qualification');
  }

  // ==========================================
  // Grand Finale & Championship (Step 14 & 15)
  // ==========================================
  async submitFinaleGuesses(payload: {
    guessing_team_id: string;
    guesses: Array<{
      target_team_id: string;
      suspected_agent_name?: string;
      suspected_participant_id?: string;
    }>;
  }): Promise<ApiResponse<any>> {
    return apiClient.post<any>('/rounds/finale/guesses/submit', payload);
  }

  async getFinaleTeamGuesses(teamId: string): Promise<ApiResponse<any>> {
    return apiClient.get<any>(`/rounds/finale/guesses/${teamId}`);
  }

  async getFinaleFinalScore(teamId?: string): Promise<ApiResponse<any>> {
    const q = teamId ? `?team_id=${teamId}` : '';
    return apiClient.get<any>(`/finale/final-score${q}`);
  }

  async getFinaleStandings(): Promise<ApiResponse<BackendFinaleStanding[]>> {
    return apiClient.get<BackendFinaleStanding[]>('/finale/standings');
  }

  async getFinaleTopFour(): Promise<ApiResponse<TopFourData>> {
    return apiClient.get<TopFourData>('/finale/top-four');
  }

  async getFinalePodium(): Promise<ApiResponse<PodiumData>> {
    return apiClient.get<PodiumData>('/finale/podium');
  }

  async getFinaleBestSecretAgent(): Promise<ApiResponse<BestSecretAgentData>> {
    return apiClient.get<BestSecretAgentData>('/finale/best-secret-agent');
  }

  async getFinaleQualification(): Promise<ApiResponse<any>> {
    return apiClient.get<any>('/finale/qualification');
  }

  async finalizeFinale(payload?: { override_discrepancy?: boolean }): Promise<ApiResponse<any>> {
    return apiClient.post<any>('/finale/finalize', payload || {});
  }

  async revealFinaleStage(payload: { stage: 'top_four' | 'podium' | 'secret_agents' | 'all' }): Promise<ApiResponse<any>> {
    return apiClient.post<any>('/finale/reveal', payload);
  }

  async resolveFinaleTie(payload: { tie_type: string; decisions: Record<string, any>; notes?: string }): Promise<ApiResponse<any>> {
    return apiClient.post<any>('/finale/resolve-tie', payload);
  }

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
