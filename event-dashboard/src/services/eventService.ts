import { API_CONFIG, isLiveMode } from './apiConfig';
import { apiClient } from './apiClient';
import { backendApiService } from './backendApiService';
import {
  Team,
  Participant,
  RoundInfo,
  DashboardOverviewData,
  ActivityLogItem,
  ApiResponse,
  CreateTeamInput,
  UpdateTeamInput,
  CreateParticipantInput,
  UpdateParticipantInput,
  TeamRound1Record,
  Round1Config,
  UpdateMiniRoundTimingInput,
  MiniRoundTiming,
} from '../types';
import {
  MOCK_TEAMS,
  MOCK_ROUNDS,
  MOCK_PROGRESSION_STEPS,
  MOCK_RECENT_ACTIVITIES,
} from '../data/mockData';
import {
  DEFAULT_ROUND1_CONFIG,
  generateInitialRound1Records,
} from '../data/round1MockData';
import {
  processRound1Standings,
  computeTeamTotals,
  ScoringEngineResult,
} from '../utils/round1Scoring';
import {
  CaboConfig,
  CaboGameRecord,
  CaboGamePlacement,
  TeamRound2Record,
  Round2Data,
} from '../types/round2';
import {
  DEFAULT_CABO_CONFIG,
  computeTeamRound2Points,
  processRound2Standings,
  computeRound2SummaryStats,
} from '../utils/round2Scoring';
import { generateInitialCaboGames } from '../data/round2MockData';
import {
  BlackMarketConfig,
  BlackMarketTransaction,
  TeamCodeRecord,
  TeamRound3Record,
  Round3Data,
} from '../types/round3';
import {
  DEFAULT_ROUND3_CONFIG,
  computeTeamLedger,
  evaluateTeamCodeStatus,
  processRound3Standings,
  computeRound3SummaryStats,
} from '../utils/round3Economy';
import {
  generateInitialRound3Transactions,
  generateInitialRound3CodeRecords,
} from '../data/round3MockData';
import {
  Round4Config,
  TeamPair,
  ResourcePersonRecord,
  ResourcePersonQuestion,
  JudgeScoreRecord,
  AgentGuessingRecord,
  AgentGuessingOutcome,
  StageTimingRecord,
  TeamRound4Record,
  Round4Data,
  Round4StageId,
  LegalSide,
} from '../types/round4';
import {
  DEFAULT_ROUND4_CONFIG,
  createInitialPairStages,
  calculatePanelScore,
  calculateFinalScoreBreakdown,
  processRound4Standings,
  computeRound4SummaryStats,
} from '../utils/round4Scoring';
import {
  generateInitialRound4Pairs,
  generateInitialRound4ResourcePersons,
  generateInitialRound4JudgeScores,
  generateInitialRound4AgentGuesses,
} from '../data/round4MockData';
import {
  FinaleConfig,
  FinaleScorecard,
  FinaleSecretAgentVerdict,
  TeamFinaleRecord,
  FinaleData,
  FinaleStatus,
  FinaleReviewStatus,
} from '../types/finale';
import {
  DEFAULT_FINALE_CONFIG,
  calculateScorecardTotal,
  calculateFinaleScoreBreakdown,
  processFinaleStandings,
  computeFinaleSummaryStats,
} from '../utils/finaleScoring';
import {
  generateInitialFinaleScorecards,
  generateInitialFinaleAgentVerdicts,
} from '../data/finaleMockData';

const STORAGE_KEY = 'event_hq_demo_state_v1';

interface DemoStorageState {
  teams: Team[];
  participants: Participant[];
  activities: ActivityLogItem[];
  round1Records: TeamRound1Record[];
  round1Config: Round1Config;
  round2Config: CaboConfig;
  round2Games: [CaboGameRecord, CaboGameRecord, CaboGameRecord];
  round3Config: BlackMarketConfig;
  round3Transactions: BlackMarketTransaction[];
  round3CodeRecords: Record<string, TeamCodeRecord>;
  round4Config: Round4Config;
  round4Pairs: TeamPair[];
  round4ResourcePersons: Record<string, ResourcePersonRecord>;
  round4JudgeScores: Record<string, JudgeScoreRecord[]>;
  round4AgentGuesses: Record<string, AgentGuessingRecord>;
  finaleConfig: FinaleConfig;
  finaleScorecards: Record<string, FinaleScorecard>;
  finaleAgentVerdicts: Record<string, FinaleSecretAgentVerdict>;
}

/**
 * EventService manages tournament data, rosters, check-in, and round scoring.
 * Operates in local demo persistence mode with strict validation rules.
 */
class EventService {
  private listeners = new Set<() => void>();
  private state: DemoStorageState;

  constructor() {
    this.state = this.loadInitialState();
    if (typeof window !== 'undefined') {
      window.addEventListener('app_mode_change', () => {
        this.notifyChange();
      });
    }
  }

  // ==========================================
  // Persistence & Pub/Sub
  // ==========================================

  private loadInitialState(): DemoStorageState {
    const defaultTeams: Team[] = JSON.parse(JSON.stringify(MOCK_TEAMS));
    const defaultParticipants: Participant[] = defaultTeams.flatMap((t) => t.members);
    const defaultConfig: Round1Config = JSON.parse(JSON.stringify(DEFAULT_ROUND1_CONFIG));
    const defaultR1Records: TeamRound1Record[] = generateInitialRound1Records(
      defaultTeams,
      defaultConfig
    );

    const defaultR2Config: CaboConfig = JSON.parse(JSON.stringify(DEFAULT_CABO_CONFIG));
    const defaultR1Standings = processRound1Standings(
      defaultR1Records,
      defaultConfig.penaltyPerHintSeconds,
      defaultConfig.isFinalized
    );
    const defaultEligibleTeams = defaultR1Standings.records
      .filter((r) => r.rank !== null && r.rank !== undefined && r.rank <= 24)
      .map((r) => defaultTeams.find((t) => t.id === r.teamId)!)
      .filter(Boolean);
    const defaultR2Games = generateInitialCaboGames(defaultEligibleTeams, defaultR2Config);

    const defaultR3Config: BlackMarketConfig = JSON.parse(JSON.stringify(DEFAULT_ROUND3_CONFIG));
    const defaultR2Raw = defaultEligibleTeams.map((team) =>
      computeTeamRound2Points(
        team.id,
        team.teamNumber,
        team.name,
        defaultConfig.isFinalized,
        defaultR2Games,
        defaultR2Config.pointTable
      )
    );
    const defaultR2Standings = processRound2Standings(defaultR2Raw, defaultR2Config, defaultConfig.isFinalized);
    const defaultR3EligibleTeams = defaultR2Standings.records
      .filter((r) => r.rank !== null && r.rank !== undefined && r.rank <= 12)
      .map((r) => defaultTeams.find((t) => t.id === r.teamId)!)
      .filter(Boolean);
    const defaultR3Transactions = generateInitialRound3Transactions(defaultR3EligibleTeams);
    const defaultR3CodeRecords = generateInitialRound3CodeRecords(defaultR3EligibleTeams);

    const defaultR4Config: Round4Config = JSON.parse(JSON.stringify(DEFAULT_ROUND4_CONFIG));
    const defaultR3Raw = defaultR3EligibleTeams.map((team) => {
      const ledger = computeTeamLedger(team.id, defaultR3Transactions, defaultR3Config.startingBalance);
      const codeRecord = evaluateTeamCodeStatus(defaultR3CodeRecords[team.id], team.id, defaultR3Config);
      return {
        teamId: team.id,
        teamNumber: team.teamNumber,
        teamName: team.name,
        round2Qualified: defaultR2Config.isFinalized,
        ledger,
        codeRecord,
        rank: null,
        tieRequiresReview: false,
        qualificationStatus: 'Standings Provisional' as const,
      };
    });
    const defaultR3Standings = processRound3Standings(defaultR3Raw, defaultR3Config, defaultR2Config.isFinalized);
    const defaultR4EligibleTeams = defaultR3Standings.records
      .filter((r) => r.rank !== null && r.rank !== undefined && r.rank <= 8)
      .map((r) => defaultTeams.find((t) => t.id === r.teamId)!)
      .filter(Boolean);
    const defaultR4Pairs = generateInitialRound4Pairs(defaultR4EligibleTeams);
    const defaultR4ResourcePersons = generateInitialRound4ResourcePersons(defaultR4Pairs);
    const defaultR4JudgeScores = generateInitialRound4JudgeScores(defaultR4EligibleTeams);
    const defaultR4AgentGuesses = generateInitialRound4AgentGuesses(defaultR4EligibleTeams);

    const defaultFinaleEligibleTeams = defaultR4EligibleTeams.slice(0, 3);
    const defaultFinaleConfig: FinaleConfig = JSON.parse(JSON.stringify(DEFAULT_FINALE_CONFIG));
    const defaultFinaleScorecards = generateInitialFinaleScorecards(defaultFinaleEligibleTeams, defaultFinaleConfig.criteria);
    const defaultFinaleAgentVerdicts = generateInitialFinaleAgentVerdicts(defaultFinaleEligibleTeams);

    if (typeof window !== 'undefined' && window.localStorage) {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) {
          const parsed = JSON.parse(raw);
          if (Array.isArray(parsed.teams) && Array.isArray(parsed.participants)) {
            const config = parsed.round1Config || defaultConfig;
            // Sanitize unconfirmed/invented checkpoint locations in existing demo storage
            if (
              Array.isArray(config.checkpointNames) &&
              config.checkpointNames.some(
                (n: string) =>
                  n.includes('Quadrangle') || n.includes('Library') || n.includes('Innovation Hub')
              )
            ) {
              config.checkpointNames = [
                'Checkpoint 1 [Location TBD]',
                'Checkpoint 2 [Location TBD]',
                'Checkpoint 3 [Location TBD]',
              ];
              if (config.hiddenCodeNotes && config.hiddenCodeNotes.includes('Quadrangle')) {
                config.hiddenCodeNotes =
                  'Code Fragment #01 concealment location pending official organizer assignment. Physical tag recovery.';
              }
            }

            let r1Records: TeamRound1Record[] =
              Array.isArray(parsed.round1Records) && parsed.round1Records.length > 0
                ? parsed.round1Records
                : generateInitialRound1Records(parsed.teams, config);

            // Sanitize checkpoint station names in team mini-rounds if they contained old invented names
            r1Records = r1Records.map((r: TeamRound1Record) => {
              let changed = false;
              const newMR = r.miniRounds.map((mr) => {
                const newCP = mr.checkpoints.map((cp, cIdx) => {
                  if (
                    cp.name.includes('Quadrangle') ||
                    cp.name.includes('Library') ||
                    cp.name.includes('Innovation Hub')
                  ) {
                    changed = true;
                    return { ...cp, name: config.checkpointNames[cIdx] || `Checkpoint ${cIdx + 1} [Location TBD]` };
                  }
                  return cp;
                });
                return { ...mr, checkpoints: newCP };
              }) as [MiniRoundTiming, MiniRoundTiming, MiniRoundTiming];

              return changed ? { ...r, miniRounds: newMR } : r;
            });

            const r2Config: CaboConfig = parsed.round2Config || defaultR2Config;
            const r2Games: [CaboGameRecord, CaboGameRecord, CaboGameRecord] =
              Array.isArray(parsed.round2Games) && parsed.round2Games.length === 3
                ? parsed.round2Games
                : defaultR2Games;

            const r3Config: BlackMarketConfig = parsed.round3Config || defaultR3Config;
            const r3Transactions: BlackMarketTransaction[] =
              Array.isArray(parsed.round3Transactions)
                ? parsed.round3Transactions
                : defaultR3Transactions;
            const r3CodeRecords: Record<string, TeamCodeRecord> =
              parsed.round3CodeRecords && typeof parsed.round3CodeRecords === 'object'
                ? parsed.round3CodeRecords
                : defaultR3CodeRecords;

            const r4Config: Round4Config = parsed.round4Config || defaultR4Config;
            const r4Pairs: TeamPair[] = Array.isArray(parsed.round4Pairs)
              ? parsed.round4Pairs
              : defaultR4Pairs;
            const r4ResourcePersons: Record<string, ResourcePersonRecord> =
              parsed.round4ResourcePersons && typeof parsed.round4ResourcePersons === 'object'
                ? parsed.round4ResourcePersons
                : defaultR4ResourcePersons;
            const r4JudgeScores: Record<string, JudgeScoreRecord[]> =
              parsed.round4JudgeScores && typeof parsed.round4JudgeScores === 'object'
                ? parsed.round4JudgeScores
                : defaultR4JudgeScores;
            const r4AgentGuesses: Record<string, AgentGuessingRecord> =
              parsed.round4AgentGuesses && typeof parsed.round4AgentGuesses === 'object'
                ? parsed.round4AgentGuesses
                : defaultR4AgentGuesses;

            const fConfig: FinaleConfig = parsed.finaleConfig || defaultFinaleConfig;
            const fScorecards: Record<string, FinaleScorecard> =
              parsed.finaleScorecards && typeof parsed.finaleScorecards === 'object'
                ? parsed.finaleScorecards
                : defaultFinaleScorecards;
            const fAgentVerdicts: Record<string, FinaleSecretAgentVerdict> =
              parsed.finaleAgentVerdicts && typeof parsed.finaleAgentVerdicts === 'object'
                ? parsed.finaleAgentVerdicts
                : defaultFinaleAgentVerdicts;

            return {
              teams: parsed.teams,
              participants: parsed.participants,
              activities: Array.isArray(parsed.activities)
                ? parsed.activities
                : JSON.parse(JSON.stringify(MOCK_RECENT_ACTIVITIES)),
              round1Records: r1Records,
              round1Config: config,
              round2Config: r2Config,
              round2Games: r2Games,
              round3Config: r3Config,
              round3Transactions: r3Transactions,
              round3CodeRecords: r3CodeRecords,
              round4Config: r4Config,
              round4Pairs: r4Pairs,
              round4ResourcePersons: r4ResourcePersons,
              round4JudgeScores: r4JudgeScores,
              round4AgentGuesses: r4AgentGuesses,
              finaleConfig: fConfig,
              finaleScorecards: fScorecards,
              finaleAgentVerdicts: fAgentVerdicts,
            };
          }
        }
      } catch (err) {
        console.warn('Failed to load demo state from localStorage:', err);
      }
    }

    const initialState: DemoStorageState = {
      teams: defaultTeams,
      participants: defaultParticipants,
      activities: JSON.parse(JSON.stringify(MOCK_RECENT_ACTIVITIES)),
      round1Records: defaultR1Records,
      round1Config: defaultConfig,
      round2Config: defaultR2Config,
      round2Games: defaultR2Games,
      round3Config: defaultR3Config,
      round3Transactions: defaultR3Transactions,
      round3CodeRecords: defaultR3CodeRecords,
      round4Config: defaultR4Config,
      round4Pairs: defaultR4Pairs,
      round4ResourcePersons: defaultR4ResourcePersons,
      round4JudgeScores: defaultR4JudgeScores,
      round4AgentGuesses: defaultR4AgentGuesses,
      finaleConfig: defaultFinaleConfig,
      finaleScorecards: defaultFinaleScorecards,
      finaleAgentVerdicts: defaultFinaleAgentVerdicts,
    };

    this.saveStateToStorage(initialState);
    return initialState;
  }

  private saveStateToStorage(state: DemoStorageState): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      } catch (err) {
        console.warn('Failed to persist demo state to localStorage:', err);
      }
    }
  }

  private notifyChange(): void {
    this.saveStateToStorage(this.state);
    this.listeners.forEach((listener) => {
      try {
        listener();
      } catch (err) {
        console.error('Subscriber notification error:', err);
      }
    });
  }

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  resetToDemoData(): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.removeItem(STORAGE_KEY);
    }
    this.state = this.loadInitialState();
    this.notifyChange();
  }

  // ==========================================
  // Dashboard & Overview
  // ==========================================

  async getDashboardOverview(): Promise<ApiResponse<DashboardOverviewData>> {
    if (API_CONFIG.isMockEnabled) {
      const teams = this.state.teams;
      const participants = this.state.participants;
      const checkedInParticipants = participants.filter((p) => p.checkedIn).length;
      const completeRosterTeams = teams.filter((t) => t.members.length === 5).length;
      const incompleteRosterTeams = teams.filter((t) => t.members.length < 5).length;
      const fullyCheckedInTeams = teams.filter(
        (t) => t.members.length === 5 && t.members.every((m) => m.checkedIn)
      ).length;


      return {
        success: true,
        data: {
          stats: {
            totalTeams: teams.length,
            totalParticipants: participants.length,
            currentRoundName: this.state.finaleConfig?.isFinalized
              ? 'Grand Finale: Championship'
              : this.state.round4Config?.isFinalized
              ? 'Grand Finale: Championship'
              : this.state.round3Config?.isFinalized
              ? 'Round 4: The Legal Battle'
              : this.state.round2Config?.isFinalized
              ? 'Round 3: The Black Market'
              : this.state.round1Config?.isFinalized
              ? 'Round 2: Cabo'
              : 'Round 1: The Great Expedition',
            currentRoundNumber: this.state.finaleConfig?.isFinalized
              ? 5
              : this.state.round4Config?.isFinalized
              ? 5
              : this.state.round3Config?.isFinalized
              ? 4
              : this.state.round2Config?.isFinalized
              ? 3
              : this.state.round1Config?.isFinalized
              ? 2
              : 1,
            currentRoundStatus: this.state.finaleConfig?.isFinalized
              ? 'Completed'
              : 'Live',
            qualifiedTeamsTarget: this.state.round4Config?.isFinalized
              ? 3
              : this.state.round3Config?.isFinalized
              ? 8
              : this.state.round2Config?.isFinalized
              ? 12
              : this.state.round1Config?.isFinalized
              ? 24
              : 32,
            activeTeamsRemaining: this.state.round4Config?.isFinalized
              ? 3
              : this.state.round3Config?.isFinalized
              ? 8
              : this.state.round2Config?.isFinalized
              ? 12
              : this.state.round1Config?.isFinalized
              ? 24
              : teams.length,
            eventProgressPercentage: this.state.finaleConfig?.isFinalized
              ? 100
              : this.state.round4Config?.isFinalized
              ? 85
              : this.state.round3Config?.isFinalized
              ? 70
              : this.state.round2Config?.isFinalized
              ? 50
              : this.state.round1Config?.isFinalized
              ? 30
              : 15,
            checkedInTeams: fullyCheckedInTeams,
            checkedInParticipants: checkedInParticipants,
            completeRosterTeams: completeRosterTeams,
            incompleteRosterTeams: incompleteRosterTeams,
            agentsAssigned: teams.length,
            fragmentsDiscovered: this.state.round1Config?.hiddenCodeRecovered ? 7 : 6,
            totalFragments: 32,
          },
          progression: MOCK_PROGRESSION_STEPS.map((step) => {
            if (step.roundNumber === 1 && this.state.round1Config?.isFinalized) {
              return { ...step, status: 'Completed' };
            }
            if (step.roundNumber === 2) {
              if (this.state.round2Config?.isFinalized) return { ...step, status: 'Completed' };
              if (this.state.round1Config?.isFinalized) return { ...step, status: 'Live' };
            }
            if (step.roundNumber === 3) {
              if (this.state.round3Config?.isFinalized) return { ...step, status: 'Completed' };
              if (this.state.round2Config?.isFinalized) return { ...step, status: 'Live' };
            }
            if (step.roundNumber === 4) {
              if (this.state.round4Config?.isFinalized) return { ...step, status: 'Completed' };
              if (this.state.round3Config?.isFinalized) return { ...step, status: 'Live' };
            }
            if (step.roundNumber === 5) {
              if (this.state.finaleConfig?.isFinalized) return { ...step, status: 'Completed' };
              if (this.state.round4Config?.isFinalized) return { ...step, status: 'Live' };
            }
            return step;
          }),
          recentActivities: this.state.activities,
        },
        isMockData: true,
        timestamp: new Date().toISOString(),
      };
    }

    const res = await apiClient.get<DashboardOverviewData>('/dashboard/overview');
    if (res && res.data) {
      if (!Array.isArray(res.data.progression)) {
        res.data.progression = [];
      }
      if (!Array.isArray(res.data.recentActivities)) {
        res.data.recentActivities = [];
      }
    }
    return res;
  }

  async getSummaryCounts(): Promise<{ teamsCount: number; participantsCount: number }> {
    if (API_CONFIG.isMockEnabled) {
      return {
        teamsCount: this.state.teams.length,
        participantsCount: this.state.participants.length,
      };
    }
    try {
      const res = await this.getDashboardOverview();
      return {
        teamsCount: res.data?.stats?.totalTeams ?? 0,
        participantsCount: res.data?.stats?.totalParticipants ?? 0,
      };
    } catch {
      return {
        teamsCount: 0,
        participantsCount: 0,
      };
    }
  }

  // ==========================================
  // Team Management
  // ==========================================

  async getTeams(): Promise<ApiResponse<Team[]>> {
    if (API_CONFIG.isMockEnabled) {
      return {
        success: true,
        data: [...this.state.teams],
        isMockData: true,
        timestamp: new Date().toISOString(),
      };
    }
    return apiClient.get<Team[]>('/teams');
  }

  async getTeamById(id: string): Promise<ApiResponse<Team>> {
    const team = this.state.teams.find((t) => t.id === id);
    if (!team) {
      throw new Error(`Team with ID "${id}" not found.`);
    }
    return {
      success: true,
      data: { ...team },
      isMockData: true,
      timestamp: new Date().toISOString(),
    };
  }

  async createTeam(input: CreateTeamInput): Promise<ApiResponse<Team>> {
    if (isLiveMode()) {
      const res = await backendApiService.createTeam(input);
      this.notifyChange();
      return res;
    }
    if (this.state.round1Config?.isFinalized) {
      throw new Error('Cannot register new squads: Tournament rounds have officially commenced and Round 1 is finalized.');
    }

    if (this.state.teams.length >= 32) {
      throw new Error('Tournament capacity reached. Maximum of 32 squads can be registered.');
    }

    const trimmedName = input.name.trim();
    if (!trimmedName) throw new Error('Team name is required.');

    const existing = this.state.teams.find(
      (t) => t.name.toLowerCase() === trimmedName.toLowerCase()
    );
    if (existing) {
      throw new Error(`A team named "${trimmedName}" already exists.`);
    }

    // Validate members if provided
    let createdMembers: Participant[] = [];
    let leaderName = 'None Assigned';

    if (input.members && input.members.length > 0) {
      if (input.members.length !== 5) {
        throw new Error(`A squad must be registered with exactly 5 participants (received ${input.members.length}).`);
      }
      const leaders = input.members.filter((m) => m.role === 'Leader');
      if (leaders.length !== 1) {
        throw new Error(`A squad must have exactly one leader (found ${leaders.length}).`);
      }
      leaderName = leaders[0].name.trim();

      // Check required fields
      for (let i = 0; i < input.members.length; i++) {
        const m = input.members[i];
        if (!m.name?.trim()) throw new Error(`Member ${i + 1} full name is required.`);
        if (!m.usn?.trim()) throw new Error(`Member ${i + 1} USN is required.`);
        if (!m.email?.trim()) throw new Error(`Member ${i + 1} institutional email is required.`);
      }

      // Check intra-form duplicates
      const submittedUsns = input.members.map((m) => m.usn.trim().toUpperCase());
      if (new Set(submittedUsns).size !== submittedUsns.length) {
        throw new Error('Duplicate USN detected within the submitted squad members.');
      }
      const submittedEmails = input.members.map((m) => m.email.trim().toLowerCase());
      if (new Set(submittedEmails).size !== submittedEmails.length) {
        throw new Error('Duplicate email detected within the submitted squad members.');
      }

      // Check existing participants
      for (const m of input.members) {
        const normUsn = m.usn.trim().toUpperCase();
        if (this.state.participants.some((p) => p.usn.toUpperCase() === normUsn)) {
          throw new Error(`Participant with USN "${normUsn}" is already registered.`);
        }
        const normEmail = m.email.trim().toLowerCase();
        if (this.state.participants.some((p) => p.email.toLowerCase() === normEmail)) {
          throw new Error(`Participant with email "${normEmail}" is already registered.`);
        }
      }
    }

    const maxNum = this.state.teams.reduce((max, t) => Math.max(max, t.teamNumber || 0), 0);
    const nextNum = maxNum + 1;
    const teamId = `team-${nextNum}`;

    if (input.members && input.members.length > 0) {
      createdMembers = input.members.map((m, idx) => ({
        id: `part-${teamId}-${idx + 1}`,
        name: m.name.trim(),
        email: m.email.trim().toLowerCase(),
        usn: m.usn.trim().toUpperCase(),
        phone: m.phone?.trim() || undefined,
        role: m.role,
        checkedIn: false,
        teamId: teamId,
        teamName: trimmedName,
      }));
      this.state.participants.push(...createdMembers);
    }

    const newTeam: Team = {
      id: teamId,
      teamNumber: nextNum,
      name: trimmedName,
      leaderName: leaderName,
      membersCount: createdMembers.length,
      members: createdMembers,
      status: 'Registered',
      currentRound: 1,
      isQualifiedForNextRound: false,
      totalScore: 0,
      assignedTable: input.assignedTable?.trim() || `Table ${nextNum}`,
      createdAt: new Date().toISOString(),
    };

    this.state.teams.push(newTeam);
    this.syncRound1Teams();

    this.logActivity({
      category: 'team',
      title: `[DEMO] Team Created: ${trimmedName}`,
      description: `New squad registered with ID ${teamId} and ${createdMembers.length} members. Assigned to ${newTeam.assignedTable}.`,
      teamTag: `T-${String(nextNum).padStart(2, '0')}`,
      badgeType: 'info',
    });

    this.notifyChange();

    return {
      success: true,
      data: newTeam,
      isMockData: true,
      timestamp: new Date().toISOString(),
    };
  }

  async updateTeam(id: string, input: UpdateTeamInput): Promise<ApiResponse<Team>> {
    if (isLiveMode()) {
      const res = await backendApiService.updateTeam(id, input);
      this.notifyChange();
      return res;
    }
    const team = this.state.teams.find((t) => t.id === id);
    if (!team) throw new Error(`Team with ID "${id}" not found.`);

    if (input.name !== undefined) {
      const trimmed = input.name.trim();
      if (!trimmed) throw new Error('Team name cannot be empty.');
      const duplicate = this.state.teams.find(
        (t) => t.id !== id && t.name.toLowerCase() === trimmed.toLowerCase()
      );
      if (duplicate) throw new Error(`Another team is already named "${trimmed}".`);
      team.name = trimmed;

      team.members.forEach((m) => {
        m.teamName = trimmed;
        const globalPart = this.state.participants.find((p) => p.id === m.id);
        if (globalPart) globalPart.teamName = trimmed;
      });

      // Update in round1Records
      const r1Record = this.state.round1Records.find((r) => r.teamId === id);
      if (r1Record) r1Record.teamName = trimmed;
    }

    if (input.assignedTable !== undefined) {
      team.assignedTable = input.assignedTable.trim();
    }

    if (input.status !== undefined) {
      team.status = input.status;
    }

    this.notifyChange();

    return {
      success: true,
      data: { ...team },
      isMockData: true,
      timestamp: new Date().toISOString(),
    };
  }

  async deleteTeam(id: string): Promise<ApiResponse<{ id: string }>> {
    if (isLiveMode()) {
      const res = await backendApiService.deleteTeam(id);
      this.notifyChange();
      return res;
    }
    if (this.state.round1Config?.isFinalized) {
      throw new Error('Cannot delete squad: Tournament rounds have officially commenced and Round 1 is finalized.');
    }

    const teamIndex = this.state.teams.findIndex((t) => t.id === id);
    if (teamIndex === -1) throw new Error(`Team with ID "${id}" not found.`);

    const team = this.state.teams[teamIndex];

    if (team.members && team.members.length > 0) {
      throw new Error(
        `Cannot delete "${team.name}": This squad currently has ${team.members.length} assigned participant(s). Please unassign or transfer all members before deleting the team.`
      );
    }

    this.state.teams.splice(teamIndex, 1);
    this.state.round1Records = this.state.round1Records.filter((r) => r.teamId !== id);

    this.logActivity({
      category: 'team',
      title: `[DEMO] Team Deleted: ${team.name}`,
      description: `Team ${team.id} removed from tournament roster.`,
      badgeType: 'warning',
    });

    this.notifyChange();

    return {
      success: true,
      data: { id },
      isMockData: true,
      timestamp: new Date().toISOString(),
    };
  }

  // ==========================================
  // Participant Management
  // ==========================================

  async getParticipants(): Promise<ApiResponse<Participant[]>> {
    if (API_CONFIG.isMockEnabled) {
      return {
        success: true,
        data: [...this.state.participants],
        isMockData: true,
        timestamp: new Date().toISOString(),
      };
    }
    return apiClient.get<Participant[]>('/participants');
  }

  async getParticipantById(id: string): Promise<ApiResponse<Participant>> {
    const participant = this.state.participants.find((p) => p.id === id);
    if (!participant) throw new Error(`Participant with ID "${id}" not found.`);
    return {
      success: true,
      data: { ...participant },
      isMockData: true,
      timestamp: new Date().toISOString(),
    };
  }

  async createParticipant(input: CreateParticipantInput): Promise<ApiResponse<Participant>> {
    if (isLiveMode()) {
      const res = await backendApiService.createParticipant(input);
      this.notifyChange();
      return res;
    }
    const trimmedName = input.name.trim();
    const trimmedEmail = input.email.trim();
    const trimmedUsn = input.usn.trim().toUpperCase();

    if (!trimmedName) throw new Error('Participant name is required.');
    if (!trimmedEmail) throw new Error('Email address is required.');
    if (!trimmedUsn) throw new Error('USN is required.');

    const duplicateUsn = this.state.participants.find(
      (p) => p.usn.toUpperCase() === trimmedUsn
    );
    if (duplicateUsn) {
      throw new Error(`USN "${trimmedUsn}" is already registered to ${duplicateUsn.name}.`);
    }

    let assignedTeam: Team | undefined;
    if (input.teamId) {
      assignedTeam = this.state.teams.find((t) => t.id === input.teamId);
      if (!assignedTeam) {
        throw new Error(`Target team "${input.teamId}" does not exist.`);
      }
      if (assignedTeam.members.length >= 5) {
        throw new Error(
          `Cannot assign to "${assignedTeam.name}": Squad already has maximum capacity of 5 participants.`
        );
      }
    }

    const newId = `part-${Date.now()}-${Math.floor(Math.random() * 1000)}`;

    const newParticipant: Participant = {
      id: newId,
      name: trimmedName,
      email: trimmedEmail,
      usn: trimmedUsn,
      phone: input.phone?.trim() || undefined,
      role: input.role || (assignedTeam && assignedTeam.members.length === 0 ? 'Leader' : 'Member'),
      checkedIn: input.checkedIn ?? false,
      teamId: assignedTeam ? assignedTeam.id : null,
      teamName: assignedTeam ? assignedTeam.name : undefined,
    };

    this.state.participants.push(newParticipant);

    if (assignedTeam) {
      assignedTeam.members.push(newParticipant);
      assignedTeam.membersCount = assignedTeam.members.length;
      if (newParticipant.role === 'Leader') {
        assignedTeam.leaderName = newParticipant.name;
      }
      this.syncTeamCheckInStatus(assignedTeam);
    }

    this.logActivity({
      category: 'checkin',
      title: `[DEMO] Participant Registered: ${trimmedName}`,
      description: assignedTeam
        ? `Added to ${assignedTeam.name} (${assignedTeam.members.length}/5 members).`
        : 'Registered as unassigned student.',
      teamTag: assignedTeam ? `T-${String(assignedTeam.teamNumber).padStart(2, '0')}` : undefined,
      badgeType: 'info',
    });

    this.notifyChange();

    return {
      success: true,
      data: newParticipant,
      isMockData: true,
      timestamp: new Date().toISOString(),
    };
  }

  async updateParticipant(
    id: string,
    input: UpdateParticipantInput
  ): Promise<ApiResponse<Participant>> {
    if (isLiveMode()) {
      const res = await backendApiService.updateParticipant(id, input);
      this.notifyChange();
      return res;
    }
    const participant = this.state.participants.find((p) => p.id === id);
    if (!participant) throw new Error(`Participant with ID "${id}" not found.`);

    if (input.name !== undefined) {
      const trimmed = input.name.trim();
      if (!trimmed) throw new Error('Participant name cannot be empty.');
      participant.name = trimmed;
    }

    if (input.email !== undefined) {
      const trimmed = input.email.trim();
      if (!trimmed) throw new Error('Email cannot be empty.');
      participant.email = trimmed;
    }

    if (input.usn !== undefined) {
      const trimmed = input.usn.trim().toUpperCase();
      if (!trimmed) throw new Error('USN cannot be empty.');
      const duplicateUsn = this.state.participants.find(
        (p) => p.id !== id && p.usn.toUpperCase() === trimmed
      );
      if (duplicateUsn) {
        throw new Error(`USN "${trimmed}" is already assigned to ${duplicateUsn.name}.`);
      }
      participant.usn = trimmed;
    }

    if (input.phone !== undefined) {
      participant.phone = input.phone.trim() || undefined;
    }

    if (input.role !== undefined) {
      participant.role = input.role;
    }

    if (input.checkedIn !== undefined) {
      participant.checkedIn = input.checkedIn;
    }

    // Handle Team Transfer
    if (input.teamId !== undefined && input.teamId !== participant.teamId) {
      const oldTeamId = participant.teamId;
      const newTeamId = input.teamId;

      if (oldTeamId) {
        const oldTeam = this.state.teams.find((t) => t.id === oldTeamId);
        if (oldTeam) {
          oldTeam.members = oldTeam.members.filter((m) => m.id !== id);
          oldTeam.membersCount = oldTeam.members.length;
          if (participant.role === 'Leader') {
            const nextLeader = oldTeam.members.find((m) => m.role === 'Leader') || oldTeam.members[0];
            oldTeam.leaderName = nextLeader ? nextLeader.name : 'None Assigned';
          }
          this.syncTeamCheckInStatus(oldTeam);
        }
      }

      if (newTeamId) {
        const newTeam = this.state.teams.find((t) => t.id === newTeamId);
        if (!newTeam) throw new Error(`Target team with ID "${newTeamId}" does not exist.`);
        if (newTeam.members.length >= 5) {
          throw new Error(
            `Cannot transfer to "${newTeam.name}": Squad already has maximum capacity of 5 participants.`
          );
        }

        participant.teamId = newTeam.id;
        participant.teamName = newTeam.name;
        newTeam.members.push({ ...participant });
        newTeam.membersCount = newTeam.members.length;
        if (participant.role === 'Leader') {
          newTeam.leaderName = participant.name;
        }
        this.syncTeamCheckInStatus(newTeam);
      } else {
        participant.teamId = null;
        participant.teamName = undefined;
      }
    } else if (participant.teamId) {
      const team = this.state.teams.find((t) => t.id === participant.teamId);
      if (team) {
        const memberIdx = team.members.findIndex((m) => m.id === id);
        if (memberIdx !== -1) {
          team.members[memberIdx] = { ...participant };
          if (participant.role === 'Leader') {
            team.leaderName = participant.name;
          }
          this.syncTeamCheckInStatus(team);
        }
      }
    }

    this.notifyChange();

    return {
      success: true,
      data: { ...participant },
      isMockData: true,
      timestamp: new Date().toISOString(),
    };
  }

  async deleteParticipant(id: string): Promise<ApiResponse<{ id: string }>> {
    if (isLiveMode()) {
      const res = await backendApiService.deleteParticipant(id);
      this.notifyChange();
      return res;
    }
    const partIdx = this.state.participants.findIndex((p) => p.id === id);
    if (partIdx === -1) throw new Error(`Participant with ID "${id}" not found.`);

    const participant = this.state.participants[partIdx];

    if (participant.teamId) {
      const team = this.state.teams.find((t) => t.id === participant.teamId);
      if (team) {
        team.members = team.members.filter((m) => m.id !== id);
        team.membersCount = team.members.length;
        if (participant.role === 'Leader') {
          const nextLeader = team.members.find((m) => m.role === 'Leader') || team.members[0];
          team.leaderName = nextLeader ? nextLeader.name : 'None Assigned';
        }
        this.syncTeamCheckInStatus(team);
      }
    }

    this.state.participants.splice(partIdx, 1);

    this.logActivity({
      category: 'checkin',
      title: `[DEMO] Participant Removed: ${participant.name}`,
      description: `Student USN ${participant.usn} deleted from registry.`,
      badgeType: 'warning',
    });

    this.notifyChange();

    return {
      success: true,
      data: { id },
      isMockData: true,
      timestamp: new Date().toISOString(),
    };
  }

  // ==========================================
  // Check-In Management
  // ==========================================

  async toggleParticipantCheckIn(
    id: string,
    forcedStatus?: boolean
  ): Promise<ApiResponse<Participant>> {
    if (isLiveMode()) {
      const res = await backendApiService.toggleParticipantCheckIn(id, forcedStatus);
      this.notifyChange();
      return res;
    }
    const participant = this.state.participants.find((p) => p.id === id);
    if (!participant) throw new Error(`Participant with ID "${id}" not found.`);

    participant.checkedIn = forcedStatus !== undefined ? forcedStatus : !participant.checkedIn;

    if (participant.teamId) {
      const team = this.state.teams.find((t) => t.id === participant.teamId);
      if (team) {
        const member = team.members.find((m) => m.id === id);
        if (member) member.checkedIn = participant.checkedIn;
        this.syncTeamCheckInStatus(team);
      }
    }

    this.logActivity({
      category: 'checkin',
      title: participant.checkedIn
        ? `[DEMO] Check-in: ${participant.name}`
        : `[DEMO] Check-in Revoked: ${participant.name}`,
      description: `Status updated to ${participant.checkedIn ? 'Checked In' : 'Pending'}.`,
      teamTag: participant.teamName ? participant.teamName.split(' ')[0] : undefined,
      badgeType: participant.checkedIn ? 'success' : 'warning',
    });

    this.notifyChange();

    return {
      success: true,
      data: { ...participant },
      isMockData: true,
      timestamp: new Date().toISOString(),
    };
  }

  private syncTeamCheckInStatus(team: Team): void {
    if (team.status === 'Disqualified' || team.status === 'Eliminated') {
      return;
    }
    const totalMembers = team.members.length;
    const checkedInCount = team.members.filter((m) => m.checkedIn).length;

    if (totalMembers === 5 && checkedInCount === 5) {
      team.status = 'Checked In';
    } else {
      team.status = 'Registered';
    }
  }

  // ==========================================
  // Round 1: The Great Expedition
  // ==========================================

  private syncRound1Teams(): void {
    if (!this.state.round1Records) {
      this.state.round1Records = generateInitialRound1Records(
        this.state.teams,
        this.state.round1Config
      );
      return;
    }

    const currentTeamIds = new Set(this.state.teams.map((t) => t.id));

    this.state.round1Records = this.state.round1Records.filter((r) =>
      currentTeamIds.has(r.teamId)
    );

    this.state.teams.forEach((team) => {
      const exists = this.state.round1Records.find((r) => r.teamId === team.id);
      if (!exists) {
        const cpNames = this.state.round1Config.checkpointNames;
        const emptyMR = (num: 1 | 2 | 3): MiniRoundTiming => ({
          miniRoundNumber: num,
          status: 'Not Started',
          hintsUsed: 0,
          durationSeconds: null,
          hintPenaltySeconds: 0,
          adjustedSeconds: null,
          checkpoints: cpNames.map((name, i) => ({
            checkpointId: `cp-${num}-${i + 1}`,
            name,
            arrivalTime: null,
          })),
        });

        const newRec: TeamRound1Record = {
          teamId: team.id,
          teamNumber: team.teamNumber,
          teamName: team.name,
          miniRounds: [emptyMR(1), emptyMR(2), emptyMR(3)],
          totalPenaltySeconds: 0,
          isComplete: false,
          qualificationStatus: 'Incomplete',
        };
        this.state.round1Records.push(newRec);
      } else {
        exists.teamName = team.name;
        exists.teamNumber = team.teamNumber;
      }
    });
  }

  async getRound1Data(): Promise<{
    records: TeamRound1Record[];
    config: Round1Config;
    engine: ScoringEngineResult;
  }> {
    if (isLiveMode()) {
      try {
        const [recordsResp, roundResp] = await Promise.all([
          backendApiService.getRound1Records(),
          backendApiService.getRound(1),
        ]);
        if (roundResp.success && roundResp.data) {
          this.state.round1Config.isFinalized = !!roundResp.data.isFinalized;
          if (roundResp.data.finalizedAt) {
            this.state.round1Config.finalizedAt = roundResp.data.finalizedAt;
          }
        }
        if (recordsResp.success && recordsResp.data && recordsResp.data.length > 0) {
          recordsResp.data.forEach((bRec) => {
            const existing = this.state.round1Records.find((r) => r.teamId === bRec.teamId);
            if (existing) {
              if (bRec.miniRounds && bRec.miniRounds.length === 3) {
                bRec.miniRounds.forEach((bmr, idx) => {
                  if (existing.miniRounds[idx]) {
                    existing.miniRounds[idx].startTime = bmr.startTime || null;
                    existing.miniRounds[idx].completionTime = bmr.completionTime || null;
                    existing.miniRounds[idx].hintsUsed = bmr.hintsUsed || 0;
                  }
                });
              }
              if (bRec.hiddenCodeRecovered) {
                this.state.round1Config.hiddenCodeRecovered = true;
                this.state.round1Config.hiddenCodeRecoveredByTeamId = bRec.teamId;
                if (bRec.hiddenCodeNotes) {
                  this.state.round1Config.hiddenCodeNotes = bRec.hiddenCodeNotes;
                }
              }
            }
          });
        }
      } catch (err) {
        console.warn('Failed to load Round 1 records from backend in Live Mode:', err);
      }
    }

    this.syncRound1Teams();

    const engine = processRound1Standings(
      this.state.round1Records,
      this.state.round1Config.penaltyPerHintSeconds,
      this.state.round1Config.isFinalized
    );

    return {
      records: engine.records,
      config: { ...this.state.round1Config },
      engine,
    };
  }

  async updateRound1MiniRoundTiming(
    teamId: string,
    input: UpdateMiniRoundTimingInput
  ): Promise<TeamRound1Record> {
    const record = this.state.round1Records.find((r) => r.teamId === teamId);
    if (!record) {
      throw new Error(`Round 1 record for squad "${teamId}" not found.`);
    }

    const mrIdx = input.miniRoundNumber - 1;
    const targetMR = record.miniRounds[mrIdx];

    if (input.startTime !== undefined) {
      targetMR.startTime = input.startTime;
    }

    if (input.completionTime !== undefined) {
      if (input.completionTime && targetMR.startTime) {
        const start = new Date(targetMR.startTime).getTime();
        const end = new Date(input.completionTime).getTime();
        if (end < start) {
          throw new Error('Completion timestamp cannot precede mini-round start timestamp.');
        }
      }
      targetMR.completionTime = input.completionTime;
    }

    if (input.hintsUsed !== undefined) {
      targetMR.hintsUsed = Math.max(0, input.hintsUsed);
    }

    if (input.checkpoints !== undefined) {
      targetMR.checkpoints = input.checkpoints;
    }

    const updated = computeTeamTotals(record, this.state.round1Config.penaltyPerHintSeconds);
    const recIdx = this.state.round1Records.findIndex((r) => r.teamId === teamId);
    this.state.round1Records[recIdx] = updated;

    if (isLiveMode()) {
      try {
        await backendApiService.updateRound1Record(teamId, {
          miniRounds: updated.miniRounds.map((mr) => ({
            roundNumber: mr.miniRoundNumber,
            startTime: mr.startTime,
            completionTime: mr.completionTime,
            hintsUsed: mr.hintsUsed,
            isCompleted: !!(mr.startTime && mr.completionTime),
          })),
        });
      } catch (err) {
        console.warn('Failed to sync Round 1 timing with backend:', err);
      }
    }

    this.notifyChange();
    return updated;
  }

  async updateRound1Config(input: Partial<Round1Config>): Promise<Round1Config> {
    this.state.round1Config = {
      ...this.state.round1Config,
      ...input,
    };

    this.state.round1Records = this.state.round1Records.map((rec) => {
      if (input.checkpointNames) {
        rec.miniRounds.forEach((mr) => {
          mr.checkpoints = input.checkpointNames!.map((name, i) => ({
            checkpointId: `cp-${mr.miniRoundNumber}-${i + 1}`,
            name,
            arrivalTime: mr.checkpoints[i]?.arrivalTime || null,
          }));
        });
      }
      return computeTeamTotals(rec, this.state.round1Config.penaltyPerHintSeconds);
    });

    this.notifyChange();
    return this.state.round1Config;
  }

  async recordRound1HiddenCode(
    recovered: boolean,
    teamId?: string | null,
    notes?: string
  ): Promise<Round1Config> {
    this.state.round1Config.hiddenCodeRecovered = recovered;
    this.state.round1Config.hiddenCodeRecoveredByTeamId = recovered ? teamId : null;
    this.state.round1Config.hiddenCodeRecoveredAt = recovered ? new Date().toISOString() : null;
    if (notes !== undefined) {
      this.state.round1Config.hiddenCodeNotes = notes;
    }

    if (isLiveMode() && teamId) {
      try {
        await backendApiService.updateRound1Record(teamId, {
          hiddenCodeRecovered: recovered,
          hiddenCodeNotes: notes,
        });
      } catch (err) {
        console.warn('Failed to sync hidden code with backend:', err);
      }
    }

    const team = teamId ? this.state.teams.find((t) => t.id === teamId) : null;
    this.logActivity({
      category: 'clue',
      title: recovered ? '[DEMO] Round 1 Code Fragment Claimed' : '[DEMO] Code Claim Reset',
      description: recovered
        ? `Organizers recorded recovery of Round 1 Fragment by ${team ? team.name : 'Marshal Desk'}.`
        : 'Round 1 Hidden Code Fragment marked unrecovered.',
      badgeType: recovered ? 'success' : 'warning',
    });

    this.notifyChange();
    return this.state.round1Config;
  }

  async finalizeRound1(): Promise<{ success: boolean; qualifiedTeamsCount: number }> {
    const engine = processRound1Standings(
      this.state.round1Records,
      this.state.round1Config.penaltyPerHintSeconds,
      this.state.round1Config.isFinalized
    );

    if (!engine.canFinalize) {
      throw new Error(`Cannot finalize Round 1: ${engine.blockReason || 'Requirements not met.'}`);
    }

    if (isLiveMode()) {
      const resp = await backendApiService.finalizeRound(1, {
        finalizedBy: 'Chief Arbiter',
      });
      if (!resp.success) {
        throw new Error(resp.message || 'Failed to finalize Round 1 on backend');
      }
    }

    this.state.round1Config.isFinalized = true;
    this.state.round1Config.finalizedAt = new Date().toISOString();

    engine.records.forEach((rec) => {
      const team = this.state.teams.find((t) => t.id === rec.teamId);
      if (team && rec.rank !== null && rec.rank !== undefined) {
        if (rec.rank <= 24) {
          team.isQualifiedForNextRound = true;
          rec.qualificationStatus = 'Finalized Qualified';
        } else {
          team.isQualifiedForNextRound = false;
          team.status = 'Eliminated';
          rec.qualificationStatus = 'Finalized Eliminated';
        }
      }
    });

    this.logActivity({
      category: 'qualification',
      title: '[FINALIZED] Round 1: The Great Expedition Concluded',
      description: 'Official results sealed. Exactly 24 squads advanced to Round 2 (Cabo). 8 squads eliminated.',
      badgeType: 'success',
    });

    this.notifyChange();
    return { success: true, qualifiedTeamsCount: 24 };
  }

  async resetRound1Timings(): Promise<void> {
    this.state.round1Config.isFinalized = false;
    this.state.round1Config.finalizedAt = null;
    this.state.round1Records = generateInitialRound1Records(this.state.teams, this.state.round1Config);

    this.state.teams.forEach((t) => {
      t.isQualifiedForNextRound = false;
      if (t.status === 'Eliminated') {
        t.status = 'Registered';
      }
    });

    this.logActivity({
      category: 'system',
      title: '[RESET] Round 1 Timing Records Reset',
      description: 'Timings restored to initial state without altering team rosters.',
      badgeType: 'warning',
    });

    this.notifyChange();
  }

  async simulateCompleteFieldRound1(): Promise<void> {
    const cpNames = this.state.round1Config.checkpointNames;
    const baseToday = new Date();

    this.state.round1Records = this.state.teams.map((team, idx) => {
      const d1 = 12 + (idx % 8);
      const d2 = 13 + ((idx * 2) % 9);
      const d3 = 11 + ((idx * 3) % 7);
      const hints = idx % 5 === 0 ? 1 : 0;

      const makeIso = (h: number, m: number, s: number) => {
        const d = new Date(baseToday);
        d.setHours(h, m, s, 0);
        return d.toISOString();
      };

      const mr1: MiniRoundTiming = {
        miniRoundNumber: 1,
        status: 'Completed',
        startTime: makeIso(10, 0, 0),
        completionTime: makeIso(10, d1, 0),
        durationSeconds: d1 * 60,
        hintsUsed: 0,
        hintPenaltySeconds: 0,
        adjustedSeconds: d1 * 60,
        checkpoints: cpNames.map((name, cIdx) => ({
          checkpointId: `cp-1-${cIdx + 1}`,
          name,
          arrivalTime: makeIso(10, Math.round((d1 * (cIdx + 1)) / 4), 0),
        })),
      };

      const mr2: MiniRoundTiming = {
        miniRoundNumber: 2,
        status: 'Completed',
        startTime: makeIso(10, 30, 0),
        completionTime: makeIso(10, 30 + d2, 0),
        durationSeconds: d2 * 60,
        hintsUsed: hints,
        hintPenaltySeconds: hints * this.state.round1Config.penaltyPerHintSeconds,
        adjustedSeconds: d2 * 60 + hints * this.state.round1Config.penaltyPerHintSeconds,
        checkpoints: cpNames.map((name, cIdx) => ({
          checkpointId: `cp-2-${cIdx + 1}`,
          name,
          arrivalTime: makeIso(10, 30 + Math.round((d2 * (cIdx + 1)) / 4), 0),
        })),
      };

      const mr3: MiniRoundTiming = {
        miniRoundNumber: 3,
        status: 'Completed',
        startTime: makeIso(11, 0, 0),
        completionTime: makeIso(11, d3, 0),
        durationSeconds: d3 * 60,
        hintsUsed: 0,
        hintPenaltySeconds: 0,
        adjustedSeconds: d3 * 60,
        checkpoints: cpNames.map((name, cIdx) => ({
          checkpointId: `cp-3-${cIdx + 1}`,
          name,
          arrivalTime: makeIso(11, Math.round((d3 * (cIdx + 1)) / 4), 0),
        })),
      };

      const rec: TeamRound1Record = {
        teamId: team.id,
        teamNumber: team.teamNumber,
        teamName: team.name,
        miniRounds: [mr1, mr2, mr3],
        totalPenaltySeconds: 0,
        isComplete: false,
        qualificationStatus: 'Incomplete',
      };

      return computeTeamTotals(rec, this.state.round1Config.penaltyPerHintSeconds);
    });

    this.logActivity({
      category: 'system',
      title: '[SIMULATION] Complete Field Timing Applied',
      description: 'All 32 squads assigned completed valid timing for qualification testing.',
      badgeType: 'info',
    });

    this.notifyChange();
  }

  private logActivity(item: Omit<ActivityLogItem, 'id' | 'timestamp'>): void {
    const newActivity: ActivityLogItem = {
      id: `act-${Date.now()}-${Math.floor(Math.random() * 100)}`,
      timestamp: new Date().toISOString(),
      ...item,
    };
    this.state.activities.unshift(newActivity);
    if (this.state.activities.length > 25) {
      this.state.activities.pop();
    }
  }

  // ==========================================
  // Round 2: Cabo Service Methods
  // ==========================================

  getEligibleRound2Teams(): Team[] {
    const isR1Finalized = this.state.round1Config.isFinalized;
    if (isR1Finalized) {
      // Use official finalized Round 1 qualified teams (Rank <= 24)
      const qualifiedRecs = this.state.round1Records.filter(
        (r) => r.rank !== null && r.rank !== undefined && r.rank <= 24
      );
      return qualifiedRecs
        .map((r) => this.state.teams.find((t) => t.id === r.teamId)!)
        .filter(Boolean);
    } else {
      // Provisional eligible teams based on current provisional Round 1 standings
      const r1Standings = processRound1Standings(
        this.state.round1Records,
        this.state.round1Config.penaltyPerHintSeconds,
        false
      );
      const provisionalRecs = r1Standings.records.filter(
        (r) => r.rank !== null && r.rank !== undefined && r.rank <= 24
      );
      return provisionalRecs
        .map((r) => this.state.teams.find((t) => t.id === r.teamId)!)
        .filter(Boolean);
    }
  }

  async getRound2Data(): Promise<Round2Data> {
    const eligibleTeams = this.getEligibleRound2Teams();
    const round1Finalized = this.state.round1Config.isFinalized;
    const config = this.state.round2Config || DEFAULT_CABO_CONFIG;

    if (!this.state.round2Games) {
      this.state.round2Games = generateInitialCaboGames(eligibleTeams, config);
    }

    if (isLiveMode()) {
      try {
        const [placementsResp, roundResp] = await Promise.all([
          backendApiService.getRound2Placements(),
          backendApiService.getRound(2),
        ]);
        if (roundResp.success && roundResp.data) {
          this.state.round2Config.isFinalized = !!roundResp.data.isFinalized;
          if (roundResp.data.finalizedAt) {
            this.state.round2Config.finalizedAt = roundResp.data.finalizedAt;
          }
        }
        if (placementsResp.success && placementsResp.data && this.state.round2Games) {
          placementsResp.data.forEach((p) => {
            const gIdx = p.gameNumber - 1;
            if (this.state.round2Games[gIdx]) {
              this.state.round2Games[gIdx].placements[p.teamId] = {
                teamId: p.teamId,
                placement: p.placement,
                points: p.points,
                recordedAt: p.recordedAt,
                notes: p.notes,
              };
            }
          });
        }
      } catch (err) {
        console.warn('Failed to sync Round 2 data from backend in Live Mode:', err);
      }
    }

    const games = this.state.round2Games;

    // Compute raw records for each eligible team
    const rawRecords: TeamRound2Record[] = eligibleTeams.map((team) =>
      computeTeamRound2Points(
        team.id,
        team.teamNumber,
        team.name,
        round1Finalized,
        games,
        config.pointTable
      )
    );

    // Compute standings, ranks, ties affecting cutoff, canFinalize
    const engine = processRound2Standings(rawRecords, config, round1Finalized);

    // Compute overview stats
    const stats = computeRound2SummaryStats(
      engine.records,
      games,
      config,
      round1Finalized,
      eligibleTeams.length
    );

    return {
      config,
      games,
      records: engine.records,
      stats,
      engine,
      round1Finalized,
      round1QualifiedTeamsCount: eligibleTeams.length,
    };
  }

  async recordCaboGamePlacement(
    gameNumber: 1 | 2 | 3,
    teamId: string,
    placement: number,
    notes?: string
  ): Promise<Round2Data> {
    if (this.state.round2Config.isFinalized) {
      throw new Error('Round 2 is officially finalized. Placements are sealed and cannot be modified.');
    }

    if (!Number.isInteger(placement) || placement < 1 || placement > 24) {
      throw new Error(`Placement must be a positive whole integer between 1 and 24. Received: ${placement}`);
    }

    const eligibleTeams = this.getEligibleRound2Teams();
    const team = eligibleTeams.find((t) => t.id === teamId);
    if (!team) {
      throw new Error(`Team with ID "${teamId}" is not among the eligible Round 2 participating squads.`);
    }

    const gameIdx = gameNumber - 1;
    const targetGame = this.state.round2Games[gameIdx];

    // Check duplicate placement policy
    if (this.state.round2Config.tiePolicy === 'strict_unique') {
      const existingEntry = Object.values(targetGame.placements).find(
        (p) => p.placement === placement && p.teamId !== teamId
      );
      if (existingEntry) {
        const existingTeam = this.state.teams.find((t) => t.id === existingEntry.teamId);
        throw new Error(
          `Placement #${placement} is already assigned to "${existingTeam ? existingTeam.name : 'another squad'}" in Game ${gameNumber}. Under Strict Placement Policy, duplicate placements are not permitted.`
        );
      }
    }

    const points = this.state.round2Config.pointTable[placement] ?? 0;

    targetGame.placements[teamId] = {
      teamId,
      placement,
      points,
      recordedAt: new Date().toISOString(),
      notes: notes || undefined,
    };

    targetGame.isCompleted = Object.keys(targetGame.placements).length === eligibleTeams.length;

    if (isLiveMode()) {
      try {
        await backendApiService.recordRound2Placement({
          gameNumber,
          teamId,
          placement,
          points,
          notes,
        });
      } catch (err) {
        console.warn('Failed to sync Round 2 placement with backend:', err);
      }
    }

    this.logActivity({
      category: 'score',
      title: `[CABO] Game ${gameNumber} Placement Logged`,
      description: `Recorded Placement #${placement} (${points} pts) for ${team.name} in Game ${gameNumber}.`,
      badgeType: 'info',
    });

    this.notifyChange();
    return this.getRound2Data();
  }

  async clearCaboGamePlacement(gameNumber: 1 | 2 | 3, teamId: string): Promise<Round2Data> {
    if (this.state.round2Config.isFinalized) {
      throw new Error('Round 2 is officially finalized. Results are sealed.');
    }

    const gameIdx = gameNumber - 1;
    const targetGame = this.state.round2Games[gameIdx];
    if (targetGame.placements[teamId]) {
      delete targetGame.placements[teamId];
      targetGame.isCompleted = false;
      this.notifyChange();
    }
    return this.getRound2Data();
  }

  async updateCaboConfig(update: Partial<CaboConfig>): Promise<Round2Data> {
    if (this.state.round2Config.isFinalized) {
      throw new Error('Round 2 is officially finalized. Configuration is sealed.');
    }

    if (update.scoringDirection) {
      this.state.round2Config.scoringDirection = update.scoringDirection;
    }
    if (update.tiePolicy) {
      this.state.round2Config.tiePolicy = update.tiePolicy;
    }
    if (update.pointTable) {
      this.state.round2Config.pointTable = { ...update.pointTable };
      // Recalculate points for all existing game placements across all 3 games
      this.state.round2Games.forEach((game) => {
        Object.values(game.placements).forEach((placement) => {
          placement.points = this.state.round2Config.pointTable[placement.placement] ?? 0;
        });
      });
    }

    this.logActivity({
      category: 'system',
      title: '[CABO] Scoring Configuration Updated',
      description: `Updated Cabo parameters: Direction=${this.state.round2Config.scoringDirection}, TiePolicy=${this.state.round2Config.tiePolicy}. Points recalculated.`,
      badgeType: 'warning',
    });

    this.notifyChange();
    return this.getRound2Data();
  }

  async finalizeRound2(): Promise<{ success: boolean; qualifiedTeamsCount: number }> {
    const data = await this.getRound2Data();
    if (!data.engine.canFinalize) {
      throw new Error(`Cannot finalize Round 2: ${data.engine.blockReason || 'Requirements not satisfied.'}`);
    }

    if (isLiveMode()) {
      const resp = await backendApiService.finalizeRound(2, {
        finalizedBy: 'Chief Arbiter',
      });
      if (!resp.success) {
        throw new Error(resp.message || 'Failed to finalize Round 2 on backend');
      }
    }

    this.state.round2Config.isFinalized = true;
    this.state.round2Config.finalizedAt = new Date().toISOString();

    // Mark status on qualified teams without deleting eliminated teams
    data.engine.records.forEach((rec) => {
      const team = this.state.teams.find((t) => t.id === rec.teamId);
      if (team && rec.rank !== null && rec.rank !== undefined) {
        if (rec.rank <= 12) {
          rec.qualificationStatus = 'Finalized Qualified';
        } else {
          rec.qualificationStatus = 'Finalized Eliminated';
        }
      }
    });

    this.logActivity({
      category: 'qualification',
      title: '[FINALIZED] Round 2: Cabo Concluded',
      description: 'Official results sealed. Exactly 12 squads advanced to Round 3 (The Black Market). 12 squads eliminated.',
      badgeType: 'success',
    });

    this.notifyChange();
    return { success: true, qualifiedTeamsCount: 12 };
  }

  async resetRound2Placements(): Promise<void> {
    if (this.state.round2Config.isFinalized) {
      throw new Error('Round 2 is officially finalized. Placements are sealed and cannot be reset.');
    }

    this.state.round2Games.forEach((g) => {
      g.placements = {};
      g.isCompleted = false;
    });

    this.logActivity({
      category: 'system',
      title: '[RESET] Cabo Game Placements Reset',
      description: 'All 3 Cabo game placement records cleared. Roster and configuration preserved.',
      badgeType: 'warning',
    });

    this.notifyChange();
  }

  async simulateCompleteRound2Games(): Promise<void> {
    if (this.state.round2Config.isFinalized) {
      throw new Error('Round 2 is officially finalized.');
    }

    const eligibleTeams = this.getEligibleRound2Teams();
    const config = this.state.round2Config;
    const n = eligibleTeams.length; // 24

    // Distinct permutations 1..24 with realistic spread and clear separation at 12th cutoff
    const perm1 = Array.from({ length: n }, (_, i) => i + 1);
    const perm2: number[] = [];
    for (let i = 0; i < n; i++) {
      perm2.push(((i * 5 + 3) % n) + 1);
    }
    const perm3: number[] = [];
    for (let i = 0; i < n; i++) {
      perm3.push(((i * 7 + 11) % n) + 1);
    }

    const now = new Date().toISOString();

    const g1: Record<string, CaboGamePlacement> = {};
    const g2: Record<string, CaboGamePlacement> = {};
    const g3: Record<string, CaboGamePlacement> = {};

    eligibleTeams.forEach((team, idx) => {
      const p1 = perm1[idx];
      const p2 = perm2[idx];
      const p3 = perm3[idx];

      g1[team.id] = {
        teamId: team.id,
        placement: p1,
        points: config.pointTable[p1] ?? 0,
        recordedAt: now,
      };
      g2[team.id] = {
        teamId: team.id,
        placement: p2,
        points: config.pointTable[p2] ?? 0,
        recordedAt: now,
      };
      g3[team.id] = {
        teamId: team.id,
        placement: p3,
        points: config.pointTable[p3] ?? 0,
        recordedAt: now,
      };
    });

    this.state.round2Games = [
      { gameNumber: 1, name: 'Cabo Game 1', isCompleted: true, placements: g1 },
      { gameNumber: 2, name: 'Cabo Game 2', isCompleted: true, placements: g2 },
      { gameNumber: 3, name: 'Cabo Game 3', isCompleted: true, placements: g3 },
    ];

    this.logActivity({
      category: 'system',
      title: '[SIMULATION] Complete Cabo Games Applied',
      description: 'All 24 participating squads assigned completed valid placements across Games 1, 2, and 3.',
      badgeType: 'info',
    });

    this.notifyChange();
  }

  // ==========================================
  // Round 3: The Black Market Methods
  // ==========================================

  getEligibleRound3Teams(): Team[] {
    if (this.state.round2Config.isFinalized) {
      // Official finalized Round 2 results: Top 12 squads
      const r2Raw = this.getEligibleRound2Teams().map((team) =>
        computeTeamRound2Points(
          team.id,
          team.teamNumber,
          team.name,
          true,
          this.state.round2Games,
          this.state.round2Config.pointTable
        )
      );
      const r2Standings = processRound2Standings(r2Raw, this.state.round2Config, true);
      const qualifiedRecs = r2Standings.records.filter(
        (r) => r.rank !== null && r.rank !== undefined && r.rank <= 12
      );
      return qualifiedRecs
        .map((r) => this.state.teams.find((t) => t.id === r.teamId)!)
        .filter(Boolean);
    } else {
      // Provisional eligible teams based on current provisional Round 2 standings
      const r2Eligible = this.getEligibleRound2Teams();
      const r2Raw = r2Eligible.map((team) =>
        computeTeamRound2Points(
          team.id,
          team.teamNumber,
          team.name,
          this.state.round1Config.isFinalized,
          this.state.round2Games,
          this.state.round2Config.pointTable
        )
      );
      const r2Standings = processRound2Standings(
        r2Raw,
        this.state.round2Config,
        this.state.round1Config.isFinalized
      );
      const provisionalRecs = r2Standings.records.filter(
        (r) => r.rank !== null && r.rank !== undefined && r.rank <= 12
      );
      return provisionalRecs
        .map((r) => this.state.teams.find((t) => t.id === r.teamId)!)
        .filter(Boolean);
    }
  }

  async getRound3Data(): Promise<Round3Data> {
    const eligibleTeams = this.getEligibleRound3Teams();
    const round2Finalized = this.state.round2Config.isFinalized;
    const config = this.state.round3Config || DEFAULT_ROUND3_CONFIG;

    if (!this.state.round3Transactions) {
      this.state.round3Transactions = generateInitialRound3Transactions(eligibleTeams);
    }
    if (!this.state.round3CodeRecords) {
      this.state.round3CodeRecords = generateInitialRound3CodeRecords(eligibleTeams);
    }

    if (isLiveMode()) {
      try {
        const [rResp, tResp, cResp] = await Promise.all([
          backendApiService.getRound(3),
          backendApiService.getRound3Transactions(),
          backendApiService.getRound3Codes(),
        ]);
        if (rResp.success && rResp.data) {
          this.state.round3Config.isFinalized = !!rResp.data.isFinalized;
          if (rResp.data.finalizedAt) {
            this.state.round3Config.finalizedAt = rResp.data.finalizedAt;
          }
        }
        if (tResp.success && tResp.data && tResp.data.length > 0) {
          this.state.round3Transactions = tResp.data.map((tx) => ({
            id: tx.id,
            teamId: tx.teamId,
            amount: tx.amount,
            type: tx.type,
            reason: tx.reason,
            organizerRef: tx.organizerRef || 'Marshal-Console',
            timestamp: tx.timestamp,
            isReversed: tx.isReversed,
            reversalTransactionId: tx.reversalTransactionId,
            notes: tx.notes,
          }));
        }
        if (cResp.success && cResp.data && cResp.data.length > 0) {
          cResp.data.forEach((c) => {
            this.state.round3CodeRecords[c.teamId] = {
              teamId: c.teamId,
              fragments: (c.fragments || []).map((f) => ({
                fragmentIndex: f.index,
                recoveredAt: c.verifiedAt || new Date().toISOString(),
                recoveredBy: c.verifiedBy || 'Checkpoint-Marshal',
                notes: f.clueStation,
              })),
              isComplete: c.isComplete,
              verifiedAt: c.verifiedAt || null,
              verifiedBy: c.verifiedBy || null,
            };
          });
        }
      } catch (err) {
        console.warn('Failed to sync Round 3 data from backend in Live Mode:', err);
      }
    }

    const transactions = this.state.round3Transactions;
    const codeRecords = this.state.round3CodeRecords;

    // Compute raw records for each eligible team
    const rawRecords: TeamRound3Record[] = eligibleTeams.map((team) => {
      const ledger = computeTeamLedger(team.id, transactions, config.startingBalance);
      const codeRecord = evaluateTeamCodeStatus(codeRecords[team.id], team.id, config);

      return {
        teamId: team.id,
        teamNumber: team.teamNumber,
        teamName: team.name,
        round2Qualified: round2Finalized,
        ledger,
        codeRecord,
        rank: null,
        tieRequiresReview: false,
        qualificationStatus: round2Finalized ? 'Standings Provisional' : 'Round 2 Pending',
      };
    });

    // Run standings & qualification engine
    const engine = processRound3Standings(rawRecords, config, round2Finalized);

    // Compute summary KPI statistics
    const stats = computeRound3SummaryStats(
      engine.records,
      transactions,
      config,
      round2Finalized,
      eligibleTeams.length
    );

    return {
      config,
      transactions,
      codeRecords,
      records: engine.records,
      stats,
      engine,
      round2Finalized,
      round2QualifiedTeamsCount: eligibleTeams.length,
    };
  }

  async recordBlackMarketTransaction(input: {
    teamId: string;
    amount: number;
    type: 'earn' | 'spend' | 'adjustment';
    reason: string;
    organizerRef?: string;
    notes?: string;
  }): Promise<BlackMarketTransaction> {
    if (this.state.round3Config.isFinalized) {
      throw new Error('Round 3 is officially finalized. Financial ledgers are sealed and cannot be modified.');
    }

    if (typeof input.amount !== 'number' || isNaN(input.amount) || input.amount === 0) {
      throw new Error('Transaction amount must be a non-zero valid number.');
    }

    if ((input.type === 'earn' || input.type === 'spend') && input.amount < 0) {
      throw new Error(`${input.type === 'earn' ? 'Earn' : 'Spend'} amount must be a positive number.`);
    }

    const eligibleTeams = this.getEligibleRound3Teams();
    const team = eligibleTeams.find((t) => t.id === input.teamId);
    if (!team) {
      throw new Error(`Team with ID "${input.teamId}" is not among the eligible Round 3 participating squads.`);
    }

    if (!input.reason || input.reason.trim().length === 0) {
      throw new Error('A valid reason or description is required for every ledger transaction.');
    }

    // Check negative balance policy
    if (!this.state.round3Config.allowNegativeBalance) {
      const currentLedger = computeTeamLedger(
        input.teamId,
        this.state.round3Transactions,
        this.state.round3Config.startingBalance
      );

      let projectedBalance = currentLedger.currentBalance;
      if (input.type === 'spend') {
        projectedBalance -= input.amount;
      } else if (input.type === 'adjustment') {
        projectedBalance += input.amount;
      }

      if (projectedBalance < 0) {
        throw new Error(
          `Transaction rejected: Team "${team.name}" current balance is ${currentLedger.currentBalance} pts. This transaction would cause the balance to drop to ${projectedBalance} pts, which violates the zero-deficit policy.`
        );
      }
    }

    const txId = `tx-${input.type}-${input.teamId}-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
    const newTx: BlackMarketTransaction = {
      id: txId,
      teamId: input.teamId,
      amount: input.amount,
      type: input.type,
      reason: input.reason.trim(),
      organizerRef: input.organizerRef?.trim() || 'Marshal-Console',
      timestamp: new Date().toISOString(),
      isReversed: false,
      notes: input.notes?.trim(),
    };

    this.state.round3Transactions.push(newTx);

    if (isLiveMode()) {
      try {
        await backendApiService.createRound3Transaction({
          teamId: input.teamId,
          amount: input.amount,
          type: input.type,
          reason: input.reason,
          organizerRef: input.organizerRef,
          notes: input.notes,
        });
      } catch (err) {
        console.warn('Failed to sync Round 3 transaction with backend:', err);
      }
    }

    this.logActivity({
      category: 'score',
      title: `[TRANSACTION] ${input.type.toUpperCase()}: ${team.name}`,
      description: `${input.type === 'earn' ? '+' : input.type === 'spend' ? '-' : input.amount >= 0 ? '+' : ''}${input.amount} pts · ${input.reason.trim()} (${newTx.organizerRef})`,
      badgeType: input.type === 'earn' ? 'success' : input.type === 'spend' ? 'warning' : 'info',
    });

    this.notifyChange();
    return newTx;
  }

  async reverseBlackMarketTransaction(
    transactionId: string,
    reason: string,
    organizerRef?: string
  ): Promise<{ reversalTransaction: BlackMarketTransaction }> {
    if (this.state.round3Config.isFinalized) {
      throw new Error('Round 3 is officially finalized. Financial ledgers are sealed and cannot be modified.');
    }

    if (!reason || reason.trim().length === 0) {
      throw new Error('A reason is strictly required when executing an audited transaction reversal.');
    }

    const targetTx = this.state.round3Transactions.find((t) => t.id === transactionId);
    if (!targetTx) {
      throw new Error(`Transaction with ID "${transactionId}" was not found.`);
    }

    if (targetTx.isReversed) {
      throw new Error(`Transaction "${transactionId}" has already been reversed and cannot be reversed again.`);
    }

    if (targetTx.type === 'reversal') {
      throw new Error('Reversal transactions cannot themselves be reversed. Enter a new compensating adjustment if needed.');
    }

    const team = this.state.teams.find((t) => t.id === targetTx.teamId);

    // Check negative balance policy if reversing an 'earn' or positive 'adjustment'
    if (
      !this.state.round3Config.allowNegativeBalance &&
      (targetTx.type === 'earn' || (targetTx.type === 'adjustment' && targetTx.amount > 0))
    ) {
      const currentLedger = computeTeamLedger(
        targetTx.teamId,
        this.state.round3Transactions,
        this.state.round3Config.startingBalance
      );
      const projectedBalance = currentLedger.currentBalance - targetTx.amount;
      if (projectedBalance < 0) {
        throw new Error(
          `Reversal rejected: Team "${team?.name || 'Squad'}" current balance is ${currentLedger.currentBalance} pts. Reversing this +${targetTx.amount} pt transaction would drop their balance to ${projectedBalance} pts, violating the zero-deficit policy.`
        );
      }
    }

    const revId = `tx-rev-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
    const reversalTx: BlackMarketTransaction = {
      id: revId,
      teamId: targetTx.teamId,
      amount: targetTx.amount,
      type: 'reversal',
      reason: `Reversal of ${targetTx.id}: ${reason.trim()}`,
      organizerRef: organizerRef?.trim() || 'Chief-Auditor',
      timestamp: new Date().toISOString(),
      isReversed: false,
      reversedTransactionId: targetTx.id,
    };

    // Mark target transaction as reversed and link the reversal transaction ID
    targetTx.isReversed = true;
    targetTx.reversalTransactionId = revId;

    // Append reversal record to transaction ledger
    this.state.round3Transactions.push(reversalTx);

    if (isLiveMode()) {
      try {
        await backendApiService.reverseRound3Transaction(transactionId);
      } catch (err) {
        console.warn('Failed to sync transaction reversal with backend:', err);
      }
    }

    this.logActivity({
      category: 'system',
      title: `[AUDIT REVERSAL] Transaction Reversed for ${team?.name || 'Team'}`,
      description: `Reversed ${targetTx.type.toUpperCase()} #${targetTx.id} (${targetTx.amount} pts). Reason: ${reason.trim()} (Logged by ${reversalTx.organizerRef})`,
      badgeType: 'danger',
    });

    this.notifyChange();
    return { reversalTransaction: reversalTx };
  }

  async updateRound3Config(patch: Partial<BlackMarketConfig>): Promise<void> {
    if (this.state.round3Config.isFinalized) {
      throw new Error('Round 3 is officially finalized. Configuration is sealed and cannot be modified.');
    }

    this.state.round3Config = {
      ...this.state.round3Config,
      ...patch,
      hiddenCodeConfig: {
        ...this.state.round3Config.hiddenCodeConfig,
        ...(patch.hiddenCodeConfig || {}),
      },
    };

    this.logActivity({
      category: 'system',
      title: '[CONFIG UPDATE] Round 3 Economy Rules Updated',
      description: `Metric: ${this.state.round3Config.rankingMetric}, Direction: ${this.state.round3Config.scoringDirection}, Confirmed: ${this.state.round3Config.isScoringConfigured}`,
      badgeType: 'info',
    });

    this.notifyChange();
  }

  async recordTeamCodeFragment(
    teamId: string,
    fragmentIndex: number,
    notes?: string,
    organizerRef?: string
  ): Promise<void> {
    if (this.state.round3Config.isFinalized) {
      throw new Error('Round 3 is officially finalized. Code records are sealed and cannot be modified.');
    }

    if (!Number.isInteger(fragmentIndex) || fragmentIndex < 1) {
      throw new Error('Fragment index must be a positive whole integer (1, 2, 3...).');
    }

    if (!this.state.round3CodeRecords[teamId]) {
      this.state.round3CodeRecords[teamId] = {
        teamId,
        fragments: [],
        isComplete: false,
        verifiedAt: null,
        verifiedBy: null,
      };
    }

    const record = this.state.round3CodeRecords[teamId];
    const existing = record.fragments.find((f) => f.fragmentIndex === fragmentIndex);
    if (existing) {
      throw new Error(`Fragment #${fragmentIndex} has already been recorded for this squad.`);
    }

    record.fragments.push({
      fragmentIndex,
      recoveredAt: new Date().toISOString(),
      recoveredBy: organizerRef?.trim() || 'Checkpoint-Marshal',
      notes: notes?.trim(),
    });

    // Sort fragments ascending
    record.fragments.sort((a, b) => a.fragmentIndex - b.fragmentIndex);

    if (isLiveMode()) {
      try {
        await backendApiService.updateRound3CodeFragment({
          teamId,
          fragmentIndex,
          isDiscovered: true,
          clueStation: notes,
        });
      } catch (err) {
        console.warn('Failed to sync code fragment with backend:', err);
      }
    }

    const team = this.state.teams.find((t) => t.id === teamId);
    this.logActivity({
      category: 'clue',
      title: `[CODE FRAGMENT] Fragment #${fragmentIndex} Logged: ${team?.name || 'Team'}`,
      description: `Fragment recovered and verified by ${organizerRef || 'Marshal'}.`,
      badgeType: 'info',
    });

    this.notifyChange();
  }

  async removeTeamCodeFragment(teamId: string, fragmentIndex: number): Promise<void> {
    if (this.state.round3Config.isFinalized) {
      throw new Error('Round 3 is officially finalized.');
    }

    const record = this.state.round3CodeRecords[teamId];
    if (!record) return;

    record.fragments = record.fragments.filter((f) => f.fragmentIndex !== fragmentIndex);

    if (isLiveMode()) {
      try {
        await backendApiService.updateRound3CodeFragment({
          teamId,
          fragmentIndex,
          isDiscovered: false,
        });
      } catch (err) {
        console.warn('Failed to sync fragment removal with backend:', err);
      }
    }

    this.notifyChange();
  }

  async verifyTeamCode(teamId: string, organizerRef?: string): Promise<void> {
    if (this.state.round3Config.isFinalized) {
      throw new Error('Round 3 is officially finalized.');
    }

    if (!this.state.round3CodeRecords[teamId]) {
      this.state.round3CodeRecords[teamId] = {
        teamId,
        fragments: [],
        isComplete: false,
        verifiedAt: null,
        verifiedBy: null,
      };
    }

    const record = this.state.round3CodeRecords[teamId];
    record.verifiedAt = new Date().toISOString();
    record.verifiedBy = organizerRef?.trim() || 'Chief-Marshal';

    const team = this.state.teams.find((t) => t.id === teamId);
    this.logActivity({
      category: 'clue',
      title: `[CODE VERIFIED] Secret Code Verified for ${team?.name || 'Team'}`,
      description: `Organizer stamp assigned by ${record.verifiedBy}.`,
      badgeType: 'success',
    });

    this.notifyChange();
  }

  async finalizeRound3(): Promise<{ success: boolean; qualifiedTeamsCount: number }> {
    if (this.state.round3Config.isFinalized) {
      throw new Error('Round 3 is already finalized.');
    }

    const data = await this.getRound3Data();
    if (!data.engine.canFinalize) {
      throw new Error(data.engine.blockReason || 'Round 3 cannot be finalized at this time.');
    }

    if (isLiveMode()) {
      const resp = await backendApiService.finalizeRound(3, {
        finalizedBy: 'Chief Arbiter',
      });
      if (!resp.success) {
        throw new Error(resp.message || 'Failed to finalize Round 3 on backend');
      }
    }

    this.state.round3Config.isFinalized = true;
    this.state.round3Config.finalizedAt = new Date().toISOString();

    // Mark status on qualified teams without deleting eliminated teams
    data.engine.records.forEach((rec) => {
      const team = this.state.teams.find((t) => t.id === rec.teamId);
      if (team && rec.rank !== null && rec.rank !== undefined) {
        if (rec.rank <= 8) {
          rec.qualificationStatus = 'Finalized Qualified';
        } else {
          rec.qualificationStatus = 'Finalized Eliminated';
        }
      }
    });

    this.logActivity({
      category: 'qualification',
      title: '[FINALIZED] Round 3: The Black Market Concluded',
      description: 'Official results sealed. Exactly 8 finalist squads advanced to Round 4 (The Legal Battle). 4 squads eliminated.',
      badgeType: 'success',
    });

    this.notifyChange();
    return { success: true, qualifiedTeamsCount: 8 };
  }

  async resetRound3Ledger(): Promise<void> {
    if (this.state.round3Config.isFinalized) {
      throw new Error('Round 3 is officially finalized. Ledgers are sealed and cannot be reset.');
    }

    this.state.round3Transactions = [];
    const eligible = this.getEligibleRound3Teams();
    this.state.round3CodeRecords = {};
    eligible.forEach((t) => {
      this.state.round3CodeRecords[t.id] = {
        teamId: t.id,
        fragments: [],
        isComplete: false,
        verifiedAt: null,
        verifiedBy: null,
      };
    });

    this.logActivity({
      category: 'system',
      title: '[RESET] Black Market Ledgers Reset',
      description: 'All financial transactions and code fragment records cleared. Configuration preserved.',
      badgeType: 'warning',
    });

    this.notifyChange();
  }

  async simulateRound3Field(): Promise<void> {
    if (this.state.round3Config.isFinalized) {
      throw new Error('Round 3 is officially finalized.');
    }

    const eligible = this.getEligibleRound3Teams();
    this.state.round3Transactions = generateInitialRound3Transactions(eligible);
    this.state.round3CodeRecords = generateInitialRound3CodeRecords(eligible);

    // Set official configuration confirmed so organizers can test clean finalization
    this.state.round3Config.isScoringConfigured = true;
    this.state.round3Config.hiddenCodeConfig.isConfigured = true;
    this.state.round3Config.hiddenCodeConfig.requiredFragmentCount = 2;

    this.logActivity({
      category: 'system',
      title: '[SIMULATION] Complete Black Market Data Applied',
      description: 'Generated trading transactions, audited reversals, and fragment records for all 12 participating squads.',
      badgeType: 'info',
    });

    this.notifyChange();
  }

  // ==========================================
  // Round 4: The Legal Battle Methods
  // ==========================================

  getEligibleRound4Teams(): Team[] {
    if (this.state.round3Config.isFinalized) {
      // Official finalized Round 3 results: Top 8 squads
      const r3Data = this.getEligibleRound3Teams().map((team) => {
        const ledger = computeTeamLedger(
          team.id,
          this.state.round3Transactions,
          this.state.round3Config.startingBalance
        );
        const codeRecord = evaluateTeamCodeStatus(
          this.state.round3CodeRecords[team.id],
          team.id,
          this.state.round3Config
        );
        return {
          teamId: team.id,
          teamNumber: team.teamNumber,
          teamName: team.name,
          round2Qualified: true,
          ledger,
          codeRecord,
          rank: null,
          tieRequiresReview: false,
          qualificationStatus: 'Standings Provisional' as const,
        };
      });
      const r3Standings = processRound3Standings(r3Data, this.state.round3Config, true);
      const qualifiedRecs = r3Standings.records.filter(
        (r) => r.rank !== null && r.rank !== undefined && r.rank <= 8
      );
      return qualifiedRecs
        .map((r) => this.state.teams.find((t) => t.id === r.teamId)!)
        .filter(Boolean);
    } else {
      // Provisional eligible teams based on current Round 3 provisional standings
      const r3Eligible = this.getEligibleRound3Teams();
      const r3Data = r3Eligible.map((team) => {
        const ledger = computeTeamLedger(
          team.id,
          this.state.round3Transactions,
          this.state.round3Config.startingBalance
        );
        const codeRecord = evaluateTeamCodeStatus(
          this.state.round3CodeRecords[team.id],
          team.id,
          this.state.round3Config
        );
        return {
          teamId: team.id,
          teamNumber: team.teamNumber,
          teamName: team.name,
          round2Qualified: this.state.round2Config.isFinalized,
          ledger,
          codeRecord,
          rank: null,
          tieRequiresReview: false,
          qualificationStatus: this.state.round2Config.isFinalized
            ? ('Standings Provisional' as const)
            : ('Round 2 Pending' as const),
        };
      });
      const r3Standings = processRound3Standings(
        r3Data,
        this.state.round3Config,
        this.state.round2Config.isFinalized
      );
      const provisionalRecs = r3Standings.records.filter(
        (r) => r.rank !== null && r.rank !== undefined && r.rank <= 8
      );
      return provisionalRecs
        .map((r) => this.state.teams.find((t) => t.id === r.teamId)!)
        .filter(Boolean);
    }
  }

  async getRound4Data(): Promise<Round4Data> {
    const eligibleTeams = this.getEligibleRound4Teams();
    const round3Finalized = this.state.round3Config.isFinalized;
    const config = this.state.round4Config || DEFAULT_ROUND4_CONFIG;

    if (!this.state.round4Pairs || this.state.round4Pairs.length === 0) {
      this.state.round4Pairs = generateInitialRound4Pairs(eligibleTeams);
    }
    if (!this.state.round4ResourcePersons || Object.keys(this.state.round4ResourcePersons).length === 0) {
      this.state.round4ResourcePersons = generateInitialRound4ResourcePersons(this.state.round4Pairs);
    }
    if (!this.state.round4JudgeScores) {
      this.state.round4JudgeScores = generateInitialRound4JudgeScores(eligibleTeams);
    }
    if (!this.state.round4AgentGuesses) {
      this.state.round4AgentGuesses = generateInitialRound4AgentGuesses(eligibleTeams);
    }

    if (isLiveMode()) {
      try {
        const rResp = await backendApiService.getRound(4);
        if (rResp.success && rResp.data) {
          this.state.round4Config.isFinalized = !!rResp.data.isFinalized;
          if (rResp.data.finalizedAt) {
            this.state.round4Config.finalizedAt = rResp.data.finalizedAt;
          }
        }
      } catch (err) {
        console.warn('Failed to sync Round 4 status from backend in Live Mode:', err);
      }
    }

    const pairs = this.state.round4Pairs;
    const judgeScoresMap = this.state.round4JudgeScores;
    const agentGuessesMap = this.state.round4AgentGuesses;

    // Compute raw records for each eligible team
    const rawRecords: TeamRound4Record[] = eligibleTeams.map((team) => {
      // Find pair
      const pair = pairs.find(
        (p) => p.teamAId === team.id || p.teamBId === team.id
      );

      const isTeamA = pair ? pair.teamAId === team.id : false;
      const assignment = pair
        ? isTeamA
          ? pair.teamAAssignment
          : pair.teamBAssignment
        : null;

      const side: LegalSide = assignment ? assignment.side : 'Unassigned';
      const caseName = pair ? pair.caseName : null;
      const hasReceivedCaseFile = assignment ? assignment.hasReceivedCaseFile : false;
      const hasReceivedOpposingFile = assignment ? assignment.hasReceivedOpposingFile : false;

      // Opponent details
      const opponentTeamId = pair ? (isTeamA ? pair.teamBId : pair.teamAId) : null;
      const opponentTeam = opponentTeamId
        ? this.state.teams.find((t) => t.id === opponentTeamId)
        : null;

      // Stages completed count
      let stagesCompletedCount = 0;
      if (pair) {
        Object.values(pair.stages).forEach((st) => {
          if (st.status === 'completed') stagesCompletedCount++;
        });
      }

      // Panel scores
      const teamJudgeScores = judgeScoresMap[team.id] || [];
      const { panelScore, isComplete: isJudgePanelComplete } = calculatePanelScore(
        teamJudgeScores,
        config.judgeAggregation
      );

      // Agent guessing
      const agentRecord = agentGuessesMap[team.id];

      // Black Market balance
      const bmCurrentBalance = computeTeamLedger(
        team.id,
        this.state.round3Transactions,
        this.state.round3Config.startingBalance
      ).currentBalance;

      // Final score breakdown
      const finalScoreBreakdown = calculateFinalScoreBreakdown(
        team.id,
        panelScore,
        agentRecord,
        bmCurrentBalance,
        config.finalScoreFormula,
        config.isGuessingRulesConfigured
      );

      return {
        teamId: team.id,
        teamNumber: team.teamNumber,
        teamName: team.name,
        pairId: pair ? pair.pairId : null,
        pairNumber: pair ? pair.pairNumber : null,
        opponentTeamId,
        opponentTeamName: opponentTeam ? opponentTeam.name : null,
        side,
        caseName,
        hasReceivedCaseFile,
        hasReceivedOpposingFile,
        stagesCompletedCount,
        judgeScores: teamJudgeScores,
        panelScore,
        isJudgePanelComplete,
        agentGuessingRecord: agentRecord,
        blackMarketBalance: bmCurrentBalance,
        finalScoreBreakdown,
        rank: null,
        tieRequiresReview: false,
        reviewStatus: round3Finalized ? 'Pending Pairing' : 'Round 3 Pending',
      };
    });

    // Run pure engine
    const engine = processRound4Standings(rawRecords, pairs, config, round3Finalized);

    // Run summary stats
    const stats = computeRound4SummaryStats(
      engine.records,
      pairs,
      config,
      round3Finalized,
      eligibleTeams.length,
      engine
    );

    return {
      config,
      pairs,
      resourcePersons: this.state.round4ResourcePersons,
      judgeScores: this.state.round4JudgeScores,
      agentGuesses: this.state.round4AgentGuesses,
      records: engine.records,
      stats,
      engine,
      round3Finalized,
      round3QualifiedTeamsCount: eligibleTeams.length,
    };
  }

  async randomizeAndFormPairings(): Promise<void> {
    if (this.state.round4Config.isFinalized) {
      throw new Error('Round 4 is officially finalized. Pairings are sealed.');
    }
    if (this.state.round4Config.pairingsConfirmed) {
      throw new Error(
        'Pairings are already officially confirmed and locked. Please explicitly unlock or reset pairings to re-pair squads.'
      );
    }

    const eligible = this.getEligibleRound4Teams();
    if (eligible.length !== 8) {
      throw new Error(`Exactly 8 squads are required to form 4 pairs. Found ${eligible.length} squads.`);
    }

    // Shuffle teams randomly using Fisher-Yates
    const shuffled = [...eligible];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }

    // Retain existing case templates/titles if already configured
    const existingCases = this.state.round4Pairs.map((p) => ({
      caseId: p.caseId,
      caseName: p.caseName,
      caseDetails: p.caseDetails,
    }));

    const newPairs: TeamPair[] = [];
    for (let i = 0; i < 4; i++) {
      const teamA = shuffled[i * 2];
      const teamB = shuffled[i * 2 + 1];
      const existing = existingCases[i] || {};

      newPairs.push({
        pairId: `pair-${i + 1}`,
        pairNumber: i + 1,
        teamAId: teamA.id,
        teamBId: teamB.id,
        isConfirmed: false,
        confirmedAt: null,
        confirmedBy: null,
        caseId: existing.caseId || `CASE-40${i + 1}`,
        caseName: existing.caseName || `Fictional Case #${i + 1}`,
        caseDetails: existing.caseDetails || 'Official case filing facts and evidence log pending organizer entry.',
        teamAAssignment: {
          teamId: teamA.id,
          side: 'Prosecution / Plaintiff',
          hasReceivedCaseFile: false,
          caseFileReceivedAt: null,
          hasReceivedOpposingFile: false,
          opposingFileReceivedAt: null,
        },
        teamBAssignment: {
          teamId: teamB.id,
          side: 'Defense / Respondent',
          hasReceivedCaseFile: false,
          caseFileReceivedAt: null,
          hasReceivedOpposingFile: false,
          opposingFileReceivedAt: null,
        },
        stages: createInitialPairStages(),
        resourcePersonId: `rp-pair-${i + 1}`,
      });
    }

    this.state.round4Pairs = newPairs;

    // Refresh resource persons for new pairs
    this.state.round4ResourcePersons = generateInitialRound4ResourcePersons(newPairs);

    if (isLiveMode()) {
      try {
        await backendApiService.autoPairRound4Teams();
      } catch (err) {
        console.warn('Failed to sync auto-pairings with backend:', err);
      }
    }

    this.logActivity({
      category: 'system',
      title: '[LEGAL BATTLE] Random Pairings Generated',
      description: 'Randomly paired 8 finalist squads into 4 head-to-head courtroom matchups. Status: Unconfirmed (Review Required).',
      badgeType: 'warning',
    });

    this.notifyChange();
  }

  async confirmPairings(organizerRef?: string): Promise<void> {
    if (this.state.round4Config.isFinalized) {
      throw new Error('Round 4 is officially finalized.');
    }

    if (this.state.round4Pairs.length !== 4) {
      throw new Error('All 4 matchup pairs must be formed before confirming.');
    }

    const now = new Date().toISOString();
    const confirmedBy = organizerRef || 'Event Head / Technical Lead';

    this.state.round4Pairs.forEach((p) => {
      p.isConfirmed = true;
      p.confirmedAt = now;
      p.confirmedBy = confirmedBy;
    });

    this.state.round4Config.pairingsConfirmed = true;
    this.state.round4Config.pairingsConfirmedAt = now;
    this.state.round4Config.pairingsConfirmedBy = confirmedBy;

    this.logActivity({
      category: 'system',
      title: '[LEGAL BATTLE] Pairings Officially Confirmed',
      description: `All 4 courtroom matchups and case assignments confirmed and locked by ${confirmedBy}.`,
      badgeType: 'success',
    });

    this.notifyChange();
  }

  async resetPairings(): Promise<void> {
    if (this.state.round4Config.isFinalized) {
      throw new Error('Round 4 is officially finalized. Pairings cannot be unlocked.');
    }

    this.state.round4Pairs.forEach((p) => {
      p.isConfirmed = false;
      p.confirmedAt = null;
      p.confirmedBy = null;
    });

    this.state.round4Config.pairingsConfirmed = false;
    this.state.round4Config.pairingsConfirmedAt = undefined;
    this.state.round4Config.pairingsConfirmedBy = undefined;

    this.logActivity({
      category: 'system',
      title: '[LEGAL BATTLE] Pairings Unlocked for Re-pairing',
      description: 'Courtroom matchup locks removed. Pairings can now be modified or re-randomized.',
      badgeType: 'warning',
    });

    this.notifyChange();
  }

  async updatePairDetails(pairId: string, patch: Partial<TeamPair>): Promise<void> {
    if (this.state.round4Config.isFinalized) {
      throw new Error('Round 4 is officially finalized. Matchups cannot be modified.');
    }

    const pair = this.state.round4Pairs.find((p) => p.pairId === pairId);
    if (!pair) {
      throw new Error(`Pair with ID "${pairId}" not found.`);
    }

    Object.assign(pair, patch);

    // If caseName changed, update resource person as well
    if (patch.caseName && this.state.round4ResourcePersons[pairId]) {
      this.state.round4ResourcePersons[pairId].assignedCaseName = patch.caseName;
    }

    this.logActivity({
      category: 'system',
      title: `[MATCHUP UPDATE] Pair #${pair.pairNumber} Details Updated`,
      description: `Updated case and assignment details for ${pair.caseName || 'Matchup'}.`,
      badgeType: 'info',
    });

    this.notifyChange();
  }

  async updateStageTiming(
    pairId: string,
    stageId: Round4StageId,
    patch: Partial<StageTimingRecord>
  ): Promise<void> {
    if (this.state.round4Config.isFinalized) {
      throw new Error('Round 4 is officially finalized.');
    }

    const pair = this.state.round4Pairs.find((p) => p.pairId === pairId);
    if (!pair) {
      throw new Error(`Pair with ID "${pairId}" not found.`);
    }

    const stage = pair.stages[stageId];
    if (!stage) {
      throw new Error(`Stage "${stageId}" not found in Pair #${pair.pairNumber}.`);
    }

    Object.assign(stage, patch);

    // Auto calculate actual duration if started and ended are set and actual is null
    if (stage.startedAt && stage.endedAt && stage.actualDurationSeconds === null) {
      const diffMs = new Date(stage.endedAt).getTime() - new Date(stage.startedAt).getTime();
      if (diffMs >= 0) {
        stage.actualDurationSeconds = Math.round(diffMs / 1000);
      }
    }

    this.logActivity({
      category: 'system',
      title: `[COURT TIMING] Pair #${pair.pairNumber} Stage: ${stage.name}`,
      description: `Status updated to "${stage.status}". Actual duration: ${stage.actualDurationSeconds ? Math.round(stage.actualDurationSeconds / 60) + ' min' : 'Pending'}.`,
      badgeType: 'info',
    });

    this.notifyChange();
  }

  async recordResourcePersonQuestion(input: {
    pairId: string;
    teamId: string;
    questionText: string;
    stage: Round4StageId;
    notes?: string;
  }): Promise<void> {
    if (this.state.round4Config.isFinalized) {
      throw new Error('Round 4 is officially finalized.');
    }

    let rp = this.state.round4ResourcePersons[input.pairId];
    if (!rp) {
      const pair = this.state.round4Pairs.find((p) => p.pairId === input.pairId);
      rp = {
        id: `rp-${input.pairId}`,
        pairId: input.pairId,
        nameOrIdentifier: `Faculty Resource Person (Pair #${pair?.pairNumber || '?'})`,
        assignedCaseName: pair?.caseName,
        questions: [],
        isQuestioningComplete: false,
      };
      this.state.round4ResourcePersons[input.pairId] = rp;
    }

    const newQuestion: ResourcePersonQuestion = {
      id: `q-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      teamId: input.teamId,
      questionText: input.questionText.trim(),
      stage: input.stage,
      askedAt: new Date().toISOString(),
      notes: input.notes,
    };

    rp.questions.push(newQuestion);

    const team = this.state.teams.find((t) => t.id === input.teamId);
    this.logActivity({
      category: 'system',
      title: `[RESOURCE INQUIRY] Query Logged for ${team?.name || 'Squad'}`,
      description: `Squad asked: "${input.questionText.substring(0, 60)}${input.questionText.length > 60 ? '...' : ''}" in ${input.stage}.`,
      badgeType: 'info',
    });

    this.notifyChange();
  }

  async updateResourcePerson(pairId: string, patch: Partial<ResourcePersonRecord>): Promise<void> {
    if (this.state.round4Config.isFinalized) {
      throw new Error('Round 4 is officially finalized.');
    }

    const rp = this.state.round4ResourcePersons[pairId];
    if (!rp) {
      throw new Error(`Resource person record for Pair "${pairId}" not found.`);
    }

    Object.assign(rp, patch);
    this.notifyChange();
  }

  async recordJudgeScore(input: {
    teamId: string;
    judgeId: string;
    judgeName: string;
    scores: Record<string, number>;
    comments?: string;
  }): Promise<void> {
    if (this.state.round4Config.isFinalized) {
      throw new Error('Round 4 is officially finalized. Judge scorecards are sealed.');
    }

    const config = this.state.round4Config;
    // Validate each category score
    let total = 0;
    config.rubricCategories.forEach((cat) => {
      const score = input.scores[cat.id];
      if (typeof score !== 'number' || isNaN(score) || score < 0 || score > cat.maxMarks) {
        throw new Error(
          `Invalid score for "${cat.name}": must be between 0 and ${cat.maxMarks} marks (Received: ${score}).`
        );
      }
      total += score;
    });

    if (!this.state.round4JudgeScores[input.teamId]) {
      this.state.round4JudgeScores[input.teamId] = [];
    }

    const existingIndex = this.state.round4JudgeScores[input.teamId].findIndex(
      (js) => js.judgeId === input.judgeId
    );

    const record: JudgeScoreRecord = {
      id: `js-${input.teamId}-${input.judgeId}`,
      judgeId: input.judgeId,
      judgeName: input.judgeName,
      teamId: input.teamId,
      scores: { ...input.scores },
      totalScore: Number(total.toFixed(2)),
      comments: input.comments,
      submittedAt: new Date().toISOString(),
      isSubmitted: true,
    };

    if (existingIndex >= 0) {
      this.state.round4JudgeScores[input.teamId][existingIndex] = record;
    } else {
      this.state.round4JudgeScores[input.teamId].push(record);
    }

    if (isLiveMode()) {
      try {
        await backendApiService.submitRound4JudgeScore({
          judgeId: input.judgeId,
          judgeName: input.judgeName,
          teamId: input.teamId,
          scores: input.scores,
          comments: input.comments,
        });
      } catch (err) {
        console.warn('Failed to sync judge score with backend:', err);
      }
    }

    const team = this.state.teams.find((t) => t.id === input.teamId);
    this.logActivity({
      category: 'system',
      title: `[SCORECARD SUBMITTED] Judge Scorecard for ${team?.name || 'Squad'}`,
      description: `${input.judgeName} awarded ${total}/100 marks across 6 rubric dimensions.`,
      badgeType: 'info',
    });

    this.notifyChange();
  }

  async recordAgentGuessing(input: {
    teamId: string;
    outcome: AgentGuessingOutcome;
    pointsAwarded: number | null;
    isVerified: boolean;
    organizerRef?: string;
    notes?: string;
  }): Promise<void> {
    if (this.state.round4Config.isFinalized) {
      throw new Error('Round 4 is officially finalized.');
    }

    this.state.round4AgentGuesses[input.teamId] = {
      teamId: input.teamId,
      outcome: input.outcome,
      pointsAwarded: input.pointsAwarded,
      isVerified: input.isVerified,
      verifiedBy: input.isVerified ? (input.organizerRef || 'Organizer Signed Off') : null,
      verifiedAt: input.isVerified ? new Date().toISOString() : null,
      notes: input.notes,
    };

    if (isLiveMode()) {
      try {
        const backendOutcome: 'correct' | 'incorrect' | 'pending' =
          input.outcome === 'none' ? 'pending' : input.outcome;
        await backendApiService.submitRound4AgentGuess({
          teamId: input.teamId,
          outcome: backendOutcome,
          pointsAwarded: input.pointsAwarded ?? undefined,
          notes: input.notes,
        });
      } catch (err) {
        console.warn('Failed to sync agent guess with backend:', err);
      }
    }

    const team = this.state.teams.find((t) => t.id === input.teamId);
    this.logActivity({
      category: 'system',
      title: `[AGENT GUESS RECORDED] Secret Agent Entry for ${team?.name || 'Squad'}`,
      description: `Outcome: ${input.outcome.toUpperCase()}. Points: ${input.pointsAwarded !== null ? input.pointsAwarded : 'Unassigned'}. Verification: ${input.isVerified ? 'VERIFIED' : 'PENDING'}.`,
      badgeType: input.isVerified ? 'success' : 'warning',
    });

    this.notifyChange();
  }

  async updateRound4Config(patch: Partial<Round4Config>): Promise<void> {
    if (this.state.round4Config.isFinalized) {
      throw new Error('Round 4 is officially finalized. Configuration is sealed.');
    }

    Object.assign(this.state.round4Config, patch);

    this.logActivity({
      category: 'system',
      title: '[LEGAL BATTLE CONFIG] Round 4 Rules Updated',
      description: 'Organizers updated rubric, judge aggregation, or final-score weighting parameters.',
      badgeType: 'warning',
    });

    this.notifyChange();
  }

  async finalizeRound4(): Promise<{ success: boolean; advancingTeamsCount: number }> {
    const data = await this.getRound4Data();
    if (!data.engine.canFinalize) {
      throw new Error(`Cannot finalize Round 4: ${data.engine.blockReason || 'Safeguard requirements not satisfied.'}`);
    }

    if (isLiveMode()) {
      const resp = await backendApiService.finalizeRound(4, {
        finalizedBy: 'Chief Arbiter',
      });
      if (!resp.success) {
        throw new Error(resp.message || 'Failed to finalize Round 4 on backend');
      }
    }

    this.state.round4Config.isFinalized = true;
    this.state.round4Config.finalizedAt = new Date().toISOString();

    const advancingCount = this.state.round4Config.advancingTeamsCount || 3;

    // Update reviewStatus on teams
    data.engine.records.forEach((rec) => {
      const team = this.state.teams.find((t) => t.id === rec.teamId);
      if (team && rec.rank !== null && rec.rank !== undefined) {
        if (rec.rank <= advancingCount) {
          rec.reviewStatus = 'Finalized Qualified';
        } else {
          rec.reviewStatus = 'Finalized Eliminated';
        }
      }
    });

    this.logActivity({
      category: 'qualification',
      title: '[FINALIZED] Round 4: The Legal Battle Concluded',
      description: `Official courtroom results sealed. Top ${advancingCount} finalist squads advanced to the Grand Finale.`,
      badgeType: 'success',
    });

    this.notifyChange();
    return { success: true, advancingTeamsCount: advancingCount };
  }

  async resetRound4Data(): Promise<void> {
    if (this.state.round4Config.isFinalized) {
      throw new Error('Round 4 is officially finalized. Data cannot be reset.');
    }

    const eligible = this.getEligibleRound4Teams();
    this.state.round4Pairs = generateInitialRound4Pairs(eligible).map((p) => ({
      ...p,
      isConfirmed: false,
      confirmedAt: null,
      confirmedBy: null,
      stages: createInitialPairStages(),
      teamAAssignment: { ...p.teamAAssignment, hasReceivedCaseFile: false, hasReceivedOpposingFile: false },
      teamBAssignment: { ...p.teamBAssignment, hasReceivedCaseFile: false, hasReceivedOpposingFile: false },
    }));
    this.state.round4ResourcePersons = generateInitialRound4ResourcePersons(this.state.round4Pairs);
    this.state.round4JudgeScores = {};
    this.state.round4AgentGuesses = {};
    this.state.round4Config.pairingsConfirmed = false;
    this.state.round4Config.pairingsConfirmedAt = undefined;
    this.state.round4Config.pairingsConfirmedBy = undefined;
    this.state.round4Config.finalScoreFormula.isFormulaConfirmed = false;
    this.state.round4Config.finalScoreFormula.confirmedAt = null;
    this.state.round4Config.finalScoreFormula.confirmedBy = null;

    this.logActivity({
      category: 'system',
      title: '[RESET] Legal Battle Courtroom Data Reset',
      description: 'Court hearings, scorecards, and secret agent submissions cleared. Ready for fresh oral argument sessions.',
      badgeType: 'warning',
    });

    this.notifyChange();
  }

  async simulateRound4Field(): Promise<void> {
    if (this.state.round4Config.isFinalized) {
      throw new Error('Round 4 is officially finalized.');
    }

    const eligible = this.getEligibleRound4Teams();
    this.state.round4Pairs = generateInitialRound4Pairs(eligible);
    // In demo simulation, mark all pairs confirmed and all stages completed
    const baseTime = new Date('2026-09-19T16:00:00Z').getTime();
    this.state.round4Pairs.forEach((p) => {
      p.isConfirmed = true;
      p.confirmedAt = new Date(baseTime).toISOString();
      p.confirmedBy = 'Tech Head / Chief Marshal';
      p.teamAAssignment.hasReceivedCaseFile = true;
      p.teamAAssignment.hasReceivedOpposingFile = true;
      p.teamBAssignment.hasReceivedCaseFile = true;
      p.teamBAssignment.hasReceivedOpposingFile = true;

      // Make all 5 stages completed for clean simulation
      p.stages.prep_1.status = 'completed';
      p.stages.prep_1.startedAt = new Date(baseTime).toISOString();
      p.stages.prep_1.endedAt = new Date(baseTime + 40 * 60000).toISOString();
      p.stages.prep_1.actualDurationSeconds = 2400;

      p.stages.hearing_1.status = 'completed';
      p.stages.hearing_1.startedAt = new Date(baseTime + 45 * 60000).toISOString();
      p.stages.hearing_1.endedAt = new Date(baseTime + 65 * 60000).toISOString();
      p.stages.hearing_1.actualDurationSeconds = 1200;

      p.stages.file_exchange.status = 'completed';
      p.stages.file_exchange.startedAt = new Date(baseTime + 66 * 60000).toISOString();
      p.stages.file_exchange.endedAt = new Date(baseTime + 76 * 60000).toISOString();
      p.stages.file_exchange.actualDurationSeconds = 600;

      p.stages.prep_2.status = 'completed';
      p.stages.prep_2.startedAt = new Date(baseTime + 80 * 60000).toISOString();
      p.stages.prep_2.endedAt = new Date(baseTime + 105 * 60000).toISOString();
      p.stages.prep_2.actualDurationSeconds = 1500;

      p.stages.hearing_2.status = 'completed';
      p.stages.hearing_2.startedAt = new Date(baseTime + 110 * 60000).toISOString();
      p.stages.hearing_2.endedAt = new Date(baseTime + 130 * 60000).toISOString();
      p.stages.hearing_2.actualDurationSeconds = 1200;
    });

    this.state.round4ResourcePersons = generateInitialRound4ResourcePersons(this.state.round4Pairs);
    this.state.round4JudgeScores = generateInitialRound4JudgeScores(eligible);
    this.state.round4AgentGuesses = generateInitialRound4AgentGuesses(eligible);

    // Confirm official parameters so organizers can test clean finalization
    this.state.round4Config.pairingsConfirmed = true;
    this.state.round4Config.pairingsConfirmedAt = new Date().toISOString();
    this.state.round4Config.pairingsConfirmedBy = 'Tech Head / Chief Marshal';
    this.state.round4Config.isRubricConfirmed = true;
    this.state.round4Config.finalScoreFormula.isFormulaConfirmed = true;
    this.state.round4Config.finalScoreFormula.confirmedAt = new Date().toISOString();
    this.state.round4Config.finalScoreFormula.confirmedBy = 'Tech Head / Chief Marshal';
    this.state.round4Config.advancingTeamsCount = 3; // Top 3 Grand Finale podium

    this.logActivity({
      category: 'system',
      title: '[SIMULATION] Complete Legal Battle Data Applied',
      description: 'Generated courtroom hearings, opposing file handoffs, resource person queries, faculty scorecards, and verified secret agent points for all 8 finalist squads.',
      badgeType: 'info',
    });

    this.notifyChange();
  }

  // ==========================================
  // Grand Finale: Championship
  // ==========================================

  private getRound4RecordsInternal(): TeamRound4Record[] {
    const eligibleTeams = this.getEligibleRound4Teams();
    const round3Finalized = this.state.round3Config.isFinalized;
    const config = this.state.round4Config || DEFAULT_ROUND4_CONFIG;
    const pairs = this.state.round4Pairs || [];
    const judgeScoresMap = this.state.round4JudgeScores || {};
    const agentGuessesMap = this.state.round4AgentGuesses || {};

    const rawRecords: TeamRound4Record[] = eligibleTeams.map((team) => {
      const pair = pairs.find((p) => p.teamAId === team.id || p.teamBId === team.id);
      const isTeamA = pair ? pair.teamAId === team.id : false;
      const assignment = pair ? (isTeamA ? pair.teamAAssignment : pair.teamBAssignment) : null;
      const side: LegalSide = assignment ? assignment.side : 'Unassigned';
      const caseName = pair ? pair.caseName : null;
      const hasReceivedCaseFile = assignment ? assignment.hasReceivedCaseFile : false;
      const hasReceivedOpposingFile = assignment ? assignment.hasReceivedOpposingFile : false;
      const opponentTeamId = pair ? (isTeamA ? pair.teamBId : pair.teamAId) : null;
      const opponentTeam = opponentTeamId ? this.state.teams.find((t) => t.id === opponentTeamId) : null;

      let stagesCompletedCount = 0;
      if (pair) {
        Object.values(pair.stages).forEach((st) => {
          if (st.status === 'completed') stagesCompletedCount++;
        });
      }

      const teamJudgeScores = judgeScoresMap[team.id] || [];
      const { panelScore, isComplete: isJudgePanelComplete } = calculatePanelScore(
        teamJudgeScores,
        config.judgeAggregation
      );

      const agentRecord = agentGuessesMap[team.id];
      const bmCurrentBalance = computeTeamLedger(
        team.id,
        this.state.round3Transactions,
        this.state.round3Config.startingBalance
      ).currentBalance;

      const finalScoreBreakdown = calculateFinalScoreBreakdown(
        team.id,
        panelScore,
        agentRecord,
        bmCurrentBalance,
        config.finalScoreFormula,
        config.isGuessingRulesConfigured
      );

      return {
        teamId: team.id,
        teamNumber: team.teamNumber,
        teamName: team.name,
        pairId: pair ? pair.pairId : null,
        pairNumber: pair ? pair.pairNumber : null,
        opponentTeamId,
        opponentTeamName: opponentTeam ? opponentTeam.name : null,
        side,
        caseName,
        hasReceivedCaseFile,
        hasReceivedOpposingFile,
        stagesCompletedCount,
        judgeScores: teamJudgeScores,
        panelScore,
        isJudgePanelComplete,
        agentGuessingRecord: agentRecord,
        blackMarketBalance: bmCurrentBalance,
        finalScoreBreakdown,
        rank: null,
        tieRequiresReview: false,
        reviewStatus: round3Finalized ? 'Pending Pairing' : 'Round 3 Pending',
      };
    });

    const engine = processRound4Standings(rawRecords, pairs, config, round3Finalized);
    return engine.records;
  }

  getEligibleFinaleTeams(): Team[] {
    const r4Config = this.state.round4Config || DEFAULT_ROUND4_CONFIG;
    const advancingTarget = r4Config.advancingTeamsCount || 3;
    const r4Records = this.getRound4RecordsInternal();

    const qualifyingRecords = r4Records.filter(
      (r) => r.rank !== null && r.rank !== undefined && r.rank <= advancingTarget
    );

    const finalistTeams = qualifyingRecords
      .map((r) => this.state.teams.find((t) => t.id === r.teamId)!)
      .filter(Boolean);

    if (finalistTeams.length === 0) {
      const eligibleR4 = this.getEligibleRound4Teams();
      return eligibleR4.slice(0, advancingTarget);
    }

    return finalistTeams;
  }

  async getFinaleData(): Promise<FinaleData> {
    const eligibleTeams = this.getEligibleFinaleTeams();
    const round4Finalized = this.state.round4Config.isFinalized;
    const config = this.state.finaleConfig || DEFAULT_FINALE_CONFIG;

    if (!this.state.finaleScorecards || Object.keys(this.state.finaleScorecards).length === 0) {
      this.state.finaleScorecards = generateInitialFinaleScorecards(eligibleTeams, config.criteria);
    }
    if (!this.state.finaleAgentVerdicts || Object.keys(this.state.finaleAgentVerdicts).length === 0) {
      this.state.finaleAgentVerdicts = generateInitialFinaleAgentVerdicts(eligibleTeams);
    }

    if (isLiveMode()) {
      try {
        const rResp = await backendApiService.getRound(5);
        if (rResp.success && rResp.data) {
          this.state.finaleConfig.isFinalized = !!rResp.data.isFinalized;
          if (rResp.data.finalizedAt) {
            this.state.finaleConfig.finalizedAt = rResp.data.finalizedAt;
          }
        }
      } catch (err) {
        console.warn('Failed to sync Grand Finale status from backend in Live Mode:', err);
      }
    }

    const scorecardsMap = this.state.finaleScorecards;
    const agentVerdictsMap = this.state.finaleAgentVerdicts;

    const r4Records = this.getRound4RecordsInternal();
    const r4DataByTeamId = new Map<string, { finalScore: number | null; rank: number }>();
    r4Records.forEach((rec) => {
      r4DataByTeamId.set(rec.teamId, {
        finalScore: rec.finalScoreBreakdown.finalScore,
        rank: rec.rank ?? 0,
      });
    });

    const rawRecords: TeamFinaleRecord[] = eligibleTeams.map((team) => {
      const scorecard = scorecardsMap[team.id] || {
        teamId: team.id,
        judgeName: 'Grand Jury Panel',
        scores: {},
        totalScore: null,
        isComplete: false,
        submittedAt: null,
        comments: '',
      };

      const agentVerdict = agentVerdictsMap[team.id];

      const r4Data = r4DataByTeamId.get(team.id);
      const carriedOverR4Score = r4Data?.finalScore ?? null;
      const round4Rank = r4Data?.rank ?? 0;

      const scoreBreakdown = calculateFinaleScoreBreakdown(
        team.id,
        carriedOverR4Score,
        scorecard,
        agentVerdict,
        config
      );

      const status: FinaleStatus = !round4Finalized
        ? 'not_started'
        : config.isFinalized
        ? 'finalized'
        : scorecard.isComplete
        ? 'completed'
        : 'in_progress';

      const reviewStatus: FinaleReviewStatus = !round4Finalized
        ? 'Round 4 Pending'
        : config.isFinalized
        ? 'Finalized'
        : !config.isScoringRulesConfirmed
        ? 'Rules Unconfirmed'
        : !scorecard.isComplete
        ? 'Scores Incomplete'
        : 'Ready for Finalization';

      return {
        teamId: team.id,
        teamNumber: team.teamNumber,
        teamName: team.name,
        round4Rank,
        round4Score: carriedOverR4Score,
        round4QualificationStatus: round4Finalized ? 'Finalized Qualified' : 'Provisional Qualified',
        status,
        reviewStatus,
        scorecard,
        agentVerdict,
        scoreBreakdown,
        placement: null,
        placementTitle: null,
        tieRequiresReview: false,
      };
    });

    const engine = processFinaleStandings(rawRecords, config, round4Finalized);
    const stats = computeFinaleSummaryStats(
      engine.records,
      config,
      round4Finalized,
      eligibleTeams.length,
      engine
    );

    return {
      config,
      records: engine.records,
      stats,
      engine,
      round4Finalized,
      round4QualifiedTeamsCount: eligibleTeams.length,
    };
  }

  async recordFinaleScorecard(input: {
    teamId: string;
    judgeName?: string;
    scores: Record<string, number | null>;
    comments?: string;
    lastEditedBy?: string;
  }): Promise<void> {
    if (this.state.finaleConfig.isFinalized) {
      throw new Error('Grand Finale is officially finalized. Scorecards are sealed.');
    }

    const config = this.state.finaleConfig;
    // Validate bounds
    for (const criterion of config.criteria) {
      const val = input.scores[criterion.id];
      if (val !== undefined && val !== null) {
        if (val < 0) {
          throw new Error(`Score for "${criterion.name}" cannot be negative.`);
        }
        if (val > criterion.maxMarks) {
          throw new Error(`Score for "${criterion.name}" (${val}) exceeds maximum allowed marks (${criterion.maxMarks}).`);
        }
      }
    }

    const { totalScore, isComplete } = calculateScorecardTotal(input.scores, config.criteria);

    this.state.finaleScorecards[input.teamId] = {
      teamId: input.teamId,
      judgeName: input.judgeName || 'Grand Jury Panel Member',
      scores: input.scores,
      totalScore,
      isComplete,
      submittedAt: new Date().toISOString(),
      comments: input.comments || '',
      lastEditedBy: input.lastEditedBy || 'Arbiter',
      lastEditedAt: new Date().toISOString(),
    };

    if (isLiveMode()) {
      try {
        const scoresToSubmit: Record<string, number> = {};
        Object.entries(input.scores).forEach(([k, v]) => {
          if (v !== null && v !== undefined) scoresToSubmit[k] = v;
        });
        await backendApiService.submitFinaleScorecard({
          teamId: input.teamId,
          judgeName: input.judgeName || 'Grand Jury Panel',
          scores: scoresToSubmit,
          comments: input.comments,
        });
      } catch (err) {
        console.warn('Failed to sync finale scorecard with backend:', err);
      }
    }

    const team = this.state.teams.find((t) => t.id === input.teamId);
    this.logActivity({
      category: 'system',
      title: `[FINALE SCORECARD] Scorecard Updated for ${team?.name || 'Finalist Squad'}`,
      description: `Activity Total: ${totalScore !== null ? totalScore : 'Incomplete'}. Recorded by: ${input.lastEditedBy || 'Jury Panel'}. Status: ${isComplete ? 'Complete' : 'Pending Values'}.`,
      badgeType: isComplete ? 'success' : 'warning',
    });

    this.notifyChange();
  }

  async recordFinaleAgentVerdict(
    teamId: string,
    verdict: {
      suspectedAgentNameOrId?: string;
      actualAgentNameOrId?: string;
      isCorrect?: boolean | null;
      bonusPoints?: number | null;
      penaltyPoints?: number | null;
      isVerified?: boolean;
      notes?: string;
      organizerRef?: string;
    }
  ): Promise<void> {
    if (this.state.finaleConfig.isFinalized) {
      throw new Error('Grand Finale is officially finalized. Verdicts are sealed.');
    }

    const existing = this.state.finaleAgentVerdicts[teamId] || {
      teamId,
      suspectedAgentNameOrId: '',
      actualAgentNameOrId: '',
      isCorrect: null,
      bonusPoints: null,
      penaltyPoints: null,
      isVerified: false,
      verifiedBy: null,
      verifiedAt: null,
      notes: '',
    };

    const isVerified = verdict.isVerified ?? existing.isVerified;

    this.state.finaleAgentVerdicts[teamId] = {
      teamId,
      suspectedAgentNameOrId: verdict.suspectedAgentNameOrId !== undefined ? verdict.suspectedAgentNameOrId : existing.suspectedAgentNameOrId,
      actualAgentNameOrId: verdict.actualAgentNameOrId !== undefined ? verdict.actualAgentNameOrId : existing.actualAgentNameOrId,
      isCorrect: verdict.isCorrect !== undefined ? verdict.isCorrect : existing.isCorrect,
      bonusPoints: verdict.bonusPoints !== undefined ? verdict.bonusPoints : existing.bonusPoints,
      penaltyPoints: verdict.penaltyPoints !== undefined ? verdict.penaltyPoints : existing.penaltyPoints,
      isVerified,
      verifiedBy: isVerified ? (verdict.organizerRef || existing.verifiedBy || 'Chief Arbiter') : null,
      verifiedAt: isVerified ? (existing.verifiedAt || new Date().toISOString()) : null,
      notes: verdict.notes !== undefined ? verdict.notes : existing.notes,
    };

    if (isLiveMode()) {
      try {
        await backendApiService.submitFinaleAgentVerdict({
          teamId,
          suspectedAgent: verdict.suspectedAgentNameOrId,
          actualAgent: verdict.actualAgentNameOrId,
          isCorrect: verdict.isCorrect ?? undefined,
          bonusPoints: verdict.bonusPoints ?? undefined,
          penaltyPoints: verdict.penaltyPoints ?? undefined,
          notes: verdict.notes,
        });
      } catch (err) {
        console.warn('Failed to sync finale agent verdict with backend:', err);
      }
    }

    const team = this.state.teams.find((t) => t.id === teamId);
    this.logActivity({
      category: 'system',
      title: `[FINALE AGENT VERDICT] Secret Agent Resolution for ${team?.name || 'Finalist Squad'}`,
      description: `Suspected: ${this.state.finaleAgentVerdicts[teamId].suspectedAgentNameOrId || 'None'}. Correct: ${this.state.finaleAgentVerdicts[teamId].isCorrect === null ? 'Pending' : this.state.finaleAgentVerdicts[teamId].isCorrect ? 'YES' : 'NO'}. Bonus: ${this.state.finaleAgentVerdicts[teamId].bonusPoints ?? 'None'}. Verified: ${isVerified ? 'VERIFIED' : 'PENDING'}.`,
      badgeType: isVerified ? 'success' : 'warning',
    });

    this.notifyChange();
  }

  async updateFinaleConfig(patch: Partial<FinaleConfig>): Promise<void> {
    if (this.state.finaleConfig.isFinalized) {
      throw new Error('Grand Finale is officially finalized. Configuration is sealed.');
    }

    Object.assign(this.state.finaleConfig, patch);

    // If criteria were patched, re-evaluate existing scorecard totals
    if (patch.criteria) {
      const criteria = this.state.finaleConfig.criteria;
      Object.entries(this.state.finaleScorecards).forEach(([teamId, sc]) => {
        const { totalScore, isComplete } = calculateScorecardTotal(sc.scores, criteria);
        this.state.finaleScorecards[teamId] = {
          ...sc,
          totalScore,
          isComplete,
        };
      });
    }

    this.logActivity({
      category: 'system',
      title: '[FINALE CONFIG] Grand Finale Settings Updated',
      description: 'Organizer adjusted championship criteria, weights, confirmation status, or ranking direction.',
      badgeType: 'warning',
    });

    this.notifyChange();
  }

  async finalizeFinale(operatorRef?: string): Promise<{ success: boolean; champion: TeamFinaleRecord }> {
    const data = await this.getFinaleData();
    if (!data.engine.canFinalize) {
      throw new Error(`Cannot finalize Grand Finale: ${data.engine.blockReason || 'Championship safeguards not satisfied.'}`);
    }

    if (isLiveMode()) {
      const resp = await backendApiService.finalizeRound(5, {
        finalizedBy: operatorRef || 'Chief Arbiter & Tech Head',
      });
      if (!resp.success) {
        throw new Error(resp.message || 'Failed to finalize Grand Finale on backend');
      }
    }

    this.state.finaleConfig.isFinalized = true;
    this.state.finaleConfig.finalizedAt = new Date().toISOString();
    this.state.finaleConfig.finalizedBy = operatorRef || 'Chief Arbiter & Tech Head';

    // Update review status on records
    data.engine.records.forEach((rec) => {
      rec.status = 'finalized';
      if (rec.placement === 1) rec.reviewStatus = 'Finalized Champion';
      else if (rec.placement === 2) rec.reviewStatus = 'Finalized 1st Runner Up';
      else if (rec.placement === 3) rec.reviewStatus = 'Finalized 2nd Runner Up';
      else rec.reviewStatus = 'Finalized';
    });

    const champion = data.engine.records.find((r) => r.placement === 1) || data.engine.records[0];

    this.logActivity({
      category: 'qualification',
      title: '[GRAND FINALE CONCLUDED] Tournament Grand Champion Crowned!',
      description: `Official championship results sealed. ${champion ? champion.teamName : 'Podium 1st'} crowned Grand Champion of EVENT HQ 2026.`,
      badgeType: 'success',
    });

    this.notifyChange();
    return { success: true, champion };
  }

  async resetFinaleData(): Promise<void> {
    if (this.state.finaleConfig.isFinalized) {
      throw new Error('Grand Finale is officially finalized. Sealed championship records cannot be reset.');
    }

    const eligible = this.getEligibleFinaleTeams();
    this.state.finaleScorecards = generateInitialFinaleScorecards(eligible, this.state.finaleConfig.criteria);
    // Reset all scores to null
    Object.keys(this.state.finaleScorecards).forEach((teamId) => {
      this.state.finaleScorecards[teamId] = {
        teamId,
        judgeName: 'Grand Jury Panel',
        scores: {},
        totalScore: null,
        isComplete: false,
        submittedAt: null,
        comments: '',
        lastEditedBy: null,
        lastEditedAt: null,
      };
    });

    this.state.finaleAgentVerdicts = generateInitialFinaleAgentVerdicts(eligible);
    Object.keys(this.state.finaleAgentVerdicts).forEach((teamId) => {
      this.state.finaleAgentVerdicts[teamId] = {
        teamId,
        suspectedAgentNameOrId: '',
        actualAgentNameOrId: '',
        isCorrect: null,
        bonusPoints: null,
        penaltyPoints: null,
        isVerified: false,
        verifiedBy: null,
        verifiedAt: null,
        notes: '',
      };
    });

    this.state.finaleConfig.isScoringRulesConfirmed = false;
    this.state.finaleConfig.confirmedAt = null;
    this.state.finaleConfig.confirmedBy = null;

    this.logActivity({
      category: 'system',
      title: '[RESET] Grand Finale Scorecards & Verdicts Cleared',
      description: 'Scorecards, secret agent verdicts, and confirmed rules reset to unconfirmed blank state.',
      badgeType: 'warning',
    });

    this.notifyChange();
  }

  async simulateFinaleField(): Promise<void> {
    if (this.state.finaleConfig.isFinalized) {
      throw new Error('Grand Finale is officially finalized.');
    }

    const eligible = this.getEligibleFinaleTeams();
    const criteria = this.state.finaleConfig.criteria;

    const simScoreSets = [
      { climax_defense: 48, cross_examination: 28, synergy_decorum: 19 },
      { climax_defense: 45, cross_examination: 26, synergy_decorum: 18 },
      { climax_defense: 42, cross_examination: 24, synergy_decorum: 16 },
    ];

    const simAgentVerdicts = [
      { suspectedAgentNameOrId: 'Agent Cipher', actualAgentNameOrId: 'Agent Cipher', isCorrect: true, bonusPoints: 10, penaltyPoints: 0, isVerified: true, verifiedBy: 'Chief Arbiter' },
      { suspectedAgentNameOrId: 'Agent Phantom', actualAgentNameOrId: 'Agent Phantom', isCorrect: true, bonusPoints: 10, penaltyPoints: 0, isVerified: true, verifiedBy: 'Chief Arbiter' },
      { suspectedAgentNameOrId: 'Agent Shadow', actualAgentNameOrId: 'Agent Specter', isCorrect: false, bonusPoints: 0, penaltyPoints: 5, isVerified: true, verifiedBy: 'Chief Arbiter' },
    ];

    eligible.forEach((team, idx) => {
      const scoreSet = simScoreSets[idx % simScoreSets.length];
      const { totalScore, isComplete } = calculateScorecardTotal(scoreSet, criteria);
      this.state.finaleScorecards[team.id] = {
        teamId: team.id,
        judgeName: 'Grand Jury Panel (Faculty Dean)',
        scores: scoreSet,
        totalScore,
        isComplete,
        submittedAt: new Date().toISOString(),
        comments: `Simulated complete scorecard for ${team.name}. Outstanding defense demonstrated.`,
        lastEditedBy: 'Chief Arbiter (Simulation Engine)',
        lastEditedAt: new Date().toISOString(),
      };

      const verdict = simAgentVerdicts[idx % simAgentVerdicts.length];
      this.state.finaleAgentVerdicts[team.id] = {
        teamId: team.id,
        suspectedAgentNameOrId: verdict.suspectedAgentNameOrId,
        actualAgentNameOrId: verdict.actualAgentNameOrId,
        isCorrect: verdict.isCorrect,
        bonusPoints: verdict.bonusPoints,
        penaltyPoints: verdict.penaltyPoints,
        isVerified: verdict.isVerified,
        verifiedBy: verdict.verifiedBy,
        verifiedAt: new Date().toISOString(),
        notes: 'Simulated confidential agent deduction verified against master registry.',
      };
    });

    // Confirm official championship rules for simulation
    this.state.finaleConfig.isScoringRulesConfirmed = true;
    this.state.finaleConfig.confirmedAt = new Date().toISOString();
    this.state.finaleConfig.confirmedBy = 'Chief Arbiter & Tech Head';

    this.logActivity({
      category: 'system',
      title: '[SIMULATION] Complete Grand Finale Data Applied',
      description: 'Populated completed jury scorecards, agent verdicts, and confirmed official championship rubric for all 3 finalist squads.',
      badgeType: 'info',
    });

    this.notifyChange();
  }

  // ==========================================
  // Static Rounds & Helpers
  // ==========================================

  async getRounds(): Promise<ApiResponse<RoundInfo[]>> {
    if (API_CONFIG.isMockEnabled) {
      const rounds = MOCK_ROUNDS.map((r) => {
        if (r.roundNumber === 1 && this.state.round1Config.isFinalized) {
          return { ...r, status: 'Completed' as const };
        }
        if (r.roundNumber === 2) {
          if (this.state.round2Config?.isFinalized) {
            return { ...r, status: 'Completed' as const };
          }
          if (this.state.round1Config.isFinalized) {
            return { ...r, status: 'Live' as const };
          }
          return { ...r, status: 'Scheduled' as const };
        }
        if (r.roundNumber === 3) {
          if (this.state.round3Config?.isFinalized) {
            return { ...r, status: 'Completed' as const };
          }
          if (this.state.round2Config?.isFinalized) {
            return { ...r, status: 'Live' as const };
          }
          return { ...r, status: 'Scheduled' as const };
        }
        if (r.roundNumber === 4) {
          if (this.state.round4Config?.isFinalized) {
            return { ...r, status: 'Completed' as const };
          }
          if (this.state.round3Config?.isFinalized) {
            return { ...r, status: 'Live' as const };
          }
          return { ...r, status: 'Scheduled' as const };
        }
        if (r.roundNumber === 5) {
          if (this.state.finaleConfig?.isFinalized) {
            return { ...r, status: 'Completed' as const };
          }
          if (this.state.round4Config?.isFinalized) {
            return { ...r, status: 'Live' as const };
          }
          return { ...r, status: 'Scheduled' as const };
        }
        return r;
      });

      return {
        success: true,
        data: rounds,
        isMockData: true,
        timestamp: new Date().toISOString(),
      };
    }
    return apiClient.get<RoundInfo[]>('/rounds');
  }

  async getRecentActivities(): Promise<ApiResponse<ActivityLogItem[]>> {
    if (API_CONFIG.isMockEnabled) {
      return {
        success: true,
        data: this.state.activities,
        isMockData: true,
        timestamp: new Date().toISOString(),
      };
    }
    return apiClient.get<ActivityLogItem[]>('/activities');
  }
}

export const eventService = new EventService();
