import { Team, Participant, RoundInfo, RoundProgressionStep, DashboardStats, ActivityLogItem } from '../types';

/**
 * 32 Representative Demo Teams for BMSIT Multi-Round Event
 * Each team has 5 participants (Total: 160 participants).
 * Strictly marked as DEMO / PLACEHOLDER data.
 */
const TEAM_NAMES = [
  'Apex Predators', 'Binary Bandits', 'Cyber Sentinels', 'Data Dynamos',
  'Echo Enigma', 'Frost Byte', 'Giga Guardians', 'Hyperion Hub',
  'Infinite Iterators', 'Java Juggernauts', 'Kernel Knights', 'Logic Lords',
  'Matrix Mavericks', 'Nexus Navigators', 'Omega Overlords', 'Pixel Pioneers',
  'Quantum Quarks', 'Rogue Raiders', 'Silicon Syndicate', 'Titan Tech',
  'Ultra Umbra', 'Vortex Vipers', 'Warp Warriors', 'Xenon Xiphos',
  'Yield Yottas', 'Zenith Zephyrs', 'Aegis Armada', 'Blaze Battalion',
  'Cipher Syndicate', 'Delta Division', 'Eclipse Elite', 'Flux Phantom'
];

function generateDemoParticipants(teamIndex: number, teamName: string): Participant[] {
  const participants: Participant[] = [];
  const teamId = `team-${teamIndex + 1}`;
  const baseNum = (teamIndex * 5) + 1;
  
  // 1 Leader + 4 Members
  participants.push({
    id: `part-${teamIndex + 1}-1`,
    name: `Team ${teamIndex + 1} Captain`,
    email: `leader.t${teamIndex + 1}@bmsit.in`,
    usn: `1BY23CS${String(baseNum).padStart(3, '0')}`,
    role: 'Leader',
    phone: `+91 98765 ${String(10000 + teamIndex).padStart(5, '0')}`,
    checkedIn: teamIndex < 28, // Demo: most checked in
    teamId: teamId,
    teamName: teamName,
  });

  for (let i = 2; i <= 5; i++) {
    const pNum = baseNum + i - 1;
    participants.push({
      id: `part-${teamIndex + 1}-${i}`,
      name: `Member ${i} (${teamName.split(' ')[0]})`,
      email: `member${i}.t${teamIndex + 1}@bmsit.in`,
      usn: `1BY23CS${String(pNum).padStart(3, '0')}`,
      role: 'Member',
      phone: `+91 98765 ${String(20000 + pNum).padStart(5, '0')}`,
      checkedIn: teamIndex < 26,
      teamId: teamId,
      teamName: teamName,
    });
  }

  return participants;
}

export const MOCK_TEAMS: Team[] = TEAM_NAMES.map((name, index) => {
  const teamNum = index + 1;
  const members = generateDemoParticipants(index, name);
  const isCheckedIn = index < 28;

  return {
    id: `team-${teamNum}`,
    teamNumber: teamNum,
    name: name,
    leaderName: members[0].name,
    membersCount: 5,
    members: members,
    status: isCheckedIn ? 'Checked In' : 'Registered',
    currentRound: 1,
    isQualifiedForNextRound: false, // Not yet finalized in Round 1
    totalScore: 0, // Placeholder
    assignedTable: `Table ${String.fromCharCode(65 + Math.floor(index / 4))}-${(index % 4) + 1}`,
    createdAt: '2026-09-19T08:00:00Z',
  };
});

export const MOCK_ROUNDS: RoundInfo[] = [
  {
    roundNumber: 1,
    name: 'The Great Expedition',
    codename: 'EXPEDITION-R1',
    description: 'Campus-wide physical clue navigation and checkpoint problem-solving. 32 teams compete; top 24 qualify.',
    initialTeamsCount: 32,
    qualifyingTeamsCount: 24,
    status: 'Live',
    startedAt: '2026-09-19T10:00:00Z',
    location: 'BMSIT Main Campus Lawn & Quadrangle',
  },
  {
    roundNumber: 2,
    name: 'Cabo',
    codename: 'CABO-R2',
    description: 'High-stakes tactical card-memory and deduction mechanics. 24 teams compete; top 12 qualify.',
    initialTeamsCount: 24,
    qualifyingTeamsCount: 12,
    status: 'Scheduled',
    location: 'Auditorium Seminar Hall 1',
  },
  {
    roundNumber: 3,
    name: 'The Black Market',
    codename: 'BLACKMARKET-R3',
    description: 'Dynamic resource trading, fluctuating pricing economics, and asset acquisition. 12 teams compete; top 8 qualify.',
    initialTeamsCount: 12,
    qualifyingTeamsCount: 8,
    status: 'Scheduled',
    location: 'Innovation & Incubation Hub',
  },
  {
    roundNumber: 4,
    name: 'The Legal Battle',
    codename: 'LEGALBATTLE-R4',
    description: 'Adversarial moot-court debates, cross-examinations, and judges panel scoring for 8 finalist teams.',
    initialTeamsCount: 8,
    qualifyingTeamsCount: 3,
    status: 'Scheduled',
    location: 'Moot Court / Conference Hall A',
  },
  {
    roundNumber: 5,
    name: 'Finale & Secret Agent Unmasking',
    codename: 'FINALE-R5',
    description: 'Secret Agent deductions, hidden code revelations, final score tabulations, and Top 3 podium ceremony.',
    initialTeamsCount: 3,
    qualifyingTeamsCount: 3,
    status: 'Scheduled',
    location: 'Main Amphitheatre',
  },
];

export const MOCK_PROGRESSION_STEPS: RoundProgressionStep[] = [
  { roundNumber: 1, name: 'The Great Expedition', totalPool: 32, qualifyingCount: 24, status: 'Live' },
  { roundNumber: 2, name: 'Cabo', totalPool: 24, qualifyingCount: 12, status: 'Scheduled' },
  { roundNumber: 3, name: 'The Black Market', totalPool: 12, qualifyingCount: 8, status: 'Scheduled' },
  { roundNumber: 4, name: 'The Legal Battle', totalPool: 8, qualifyingCount: 3, status: 'Scheduled' },
  { roundNumber: 5, name: 'Finale', totalPool: 3, qualifyingCount: 3, status: 'Scheduled' },
];

export const MOCK_DASHBOARD_STATS: DashboardStats = {
  totalTeams: 32,
  totalParticipants: 160,
  currentRoundName: 'Round 1: The Great Expedition',
  currentRoundNumber: 1,
  currentRoundStatus: 'Live',
  qualifiedTeamsTarget: 24,
  activeTeamsRemaining: 32,
  eventProgressPercentage: 20, // Round 1 in progress
  checkedInTeams: 28,
  checkedInParticipants: 140,
  completeRosterTeams: 32,
  incompleteRosterTeams: 0,
  agentsAssigned: 32, // 1 per team, confidential
  fragmentsDiscovered: 6,
  totalFragments: 32,
};

export const MOCK_RECENT_ACTIVITIES: ActivityLogItem[] = [
  {
    id: 'act-1',
    timestamp: new Date(Date.now() - 3 * 60 * 1000).toISOString(),
    category: 'clue',
    title: '[DEMO] Code Fragment Found',
    description: 'Team T-04 (Data Dynamos) scanned campus checkpoint QR #06 at Library Courtyard.',
    teamTag: 'T-04',
    badgeType: 'info',
  },
  {
    id: 'act-2',
    timestamp: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
    category: 'checkin',
    title: '[DEMO] Team Check-in Completed',
    description: 'Team T-28 (Blaze Battalion) verified 5/5 participants with Tech Desk.',
    teamTag: 'T-28',
    badgeType: 'success',
  },
  {
    id: 'act-3',
    timestamp: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
    category: 'system',
    title: '[DEMO] Round 1 Station Opened',
    description: 'Organizer Marshall 2 opened Station 3 (Navigation Riddle) for general solving.',
    badgeType: 'default',
  },
  {
    id: 'act-4',
    timestamp: new Date(Date.now() - 42 * 60 * 1000).toISOString(),
    category: 'score',
    title: '[DEMO] Checkpoint Point Logged',
    description: 'Team T-12 (Logic Lords) submitted verified riddle solution at Checkpoint B.',
    teamTag: 'T-12',
    badgeType: 'success',
  },
  {
    id: 'act-5',
    timestamp: new Date(Date.now() - 65 * 60 * 1000).toISOString(),
    category: 'agent',
    title: '[DEMO] Agent Briefing Broadcasted',
    description: 'Encrypted transmission sent to 32 designated devices. Status: Confirmed read.',
    badgeType: 'warning',
  },
];
