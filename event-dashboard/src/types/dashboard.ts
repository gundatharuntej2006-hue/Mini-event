import { RoundProgressionStep } from './round';

export interface DashboardStats {
  totalTeams: number;
  totalParticipants: number;
  currentRoundName: string;
  currentRoundNumber: number;
  currentRoundStatus: string;
  qualifiedTeamsTarget: number;
  activeTeamsRemaining: number;
  eventProgressPercentage: number;
  checkedInTeams: number; // teams with complete roster and 100% checkin
  checkedInParticipants: number; // total individuals checked in
  completeRosterTeams: number; // teams with exactly 5 assigned participants
  incompleteRosterTeams: number; // teams with < 5 assigned participants
  agentsAssigned: number;
  fragmentsDiscovered: number;
  totalFragments: number;
}

export type ActivityCategory = 'checkin' | 'qualification' | 'score' | 'clue' | 'agent' | 'system' | 'team';

export interface ActivityLogItem {
  id: string;
  timestamp: string;
  category: ActivityCategory;
  title: string;
  description: string;
  teamTag?: string;
  badgeType: 'default' | 'success' | 'warning' | 'info' | 'danger';
}

export interface DashboardOverviewData {
  stats: DashboardStats;
  progression: RoundProgressionStep[];
  recentActivities: ActivityLogItem[];
}
