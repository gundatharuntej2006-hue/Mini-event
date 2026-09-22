export type ParticipantRole = 'Leader' | 'Member';

export interface Participant {
  id: string;
  name: string;
  email: string;
  usn: string; // BMSIT University Seat Number
  role: ParticipantRole;
  phone?: string;
  checkedIn: boolean;
  teamId?: string | null;
  teamName?: string;
}

export type TeamStatus = 'Registered' | 'Checked In' | 'Active' | 'Eliminated' | 'Disqualified';

export interface Team {
  id: string;
  teamNumber: number;
  name: string;
  leaderName: string;
  membersCount: number;
  members: Participant[];
  status: TeamStatus;
  currentRound: number; // 1 to 5
  isQualifiedForNextRound: boolean;
  totalScore: number;
  assignedTable?: string;
  createdAt: string;
}

export type TeamCheckInState = 'Ready' | 'Partial' | 'Incomplete Roster' | 'Unchecked';

export interface TeamMemberInput {
  name: string;
  email: string;
  usn: string;
  phone?: string;
  role: ParticipantRole;
}

export interface CreateTeamInput {
  name: string;
  assignedTable?: string;
  members?: TeamMemberInput[];
}

export interface UpdateTeamInput {
  name?: string;
  assignedTable?: string;
  status?: TeamStatus;
}

export interface CreateParticipantInput {
  name: string;
  email: string;
  usn: string;
  phone?: string;
  role?: ParticipantRole;
  teamId?: string | null;
  checkedIn?: boolean;
}

export interface UpdateParticipantInput {
  name?: string;
  email?: string;
  usn?: string;
  phone?: string;
  role?: ParticipantRole;
  teamId?: string | null;
  checkedIn?: boolean;
}
