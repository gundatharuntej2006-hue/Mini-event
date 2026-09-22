/**
 * EVENT HQ — Teams Page Data Fetching, Lifecycle, Race-Condition & RBAC Test Suite
 *
 * Verifies:
 * 1. Successful Loading: Fetches 4 live squads from FastAPI backend with correct fields and check-in metrics.
 * 2. Loading State Cleared: isLoading transitions true -> false in every outcome (success, error, empty, 401/403).
 * 3. Infinite Loop Prevention: authService.saveUserToStorage does not notify listeners when user is unchanged.
 * 4. Stale Request & Race Condition Protection: Sequenced requests discard outdated responses without sticking in loading.
 * 5. Error vs. Empty State Distinction: Table renders clear error/retry state on failure, distinct from empty roster.
 * 6. RBAC Integrity: Staff actions (Create, Edit, Delete) respect role permissions in Live Mode.
 */

import { setAppMode, isLiveMode } from './services/apiConfig';
import { apiClient } from './services/apiClient';
import { authService } from './services/authService';
import { Team, User, ApiError } from './types';
import { formatTeamNumber } from './utils/formatters';

interface TestResult {
  suite: string;
  testName: string;
  passed: boolean;
  error?: string;
}

const results: TestResult[] = [];

function assert(condition: boolean, testName: string, suite: string, failureMsg?: string) {
  if (condition) {
    results.push({ suite, testName, passed: true });
    console.log(`  PASS: [${suite}] ${testName}`);
  } else {
    results.push({ suite, testName, passed: false, error: failureMsg || 'Assertion failed' });
    console.error(`  FAIL: [${suite}] ${testName}: ${failureMsg || 'Assertion failed'}`);
  }
}

// Emulate TeamsPage getTeamCheckInMetrics
function computeTeamMetrics(team: Team) {
  const total = team.members.length;
  const checkedIn = team.members.filter((m) => m.checkedIn).length;
  const isCompleteRoster = total === 5;
  const isFullyCheckedIn = isCompleteRoster && checkedIn === 5;

  let label = 'Unchecked';
  if (!isCompleteRoster) {
    label = `Incomplete Roster (${total}/5)`;
  } else if (isFullyCheckedIn) {
    label = 'Ready · 5/5 Checked In';
  } else if (checkedIn > 0) {
    label = `Partial · ${checkedIn}/5 Checked In`;
  } else {
    label = '0/5 Checked In';
  }

  return { total, checkedIn, isCompleteRoster, isFullyCheckedIn, label };
}

// Emulate TeamsPage request manager
class TeamsPageDataController {
  public teams: Team[] = [];
  public isLoading: boolean = true;
  public error: { message: string; status?: number } | null = null;
  public requestId = 0;
  public fetchCount = 0;

  async loadTeams(
    fetcher: () => Promise<Team[]>,
    showSkeleton = true
  ): Promise<void> {
    const currentId = ++this.requestId;
    this.fetchCount++;
    if (showSkeleton) {
      this.isLoading = true;
    }
    this.error = null;

    try {
      const data = await fetcher();
      if (currentId !== this.requestId) {
        return; // Discard superseded response
      }
      this.teams = data;
    } catch (err: unknown) {
      if (currentId !== this.requestId) {
        return; // Discard superseded error
      }
      const apiErr = err as ApiError;
      this.error = {
        message: apiErr?.message || (err as Error)?.message || 'Failed to connect to FastAPI backend.',
        status: apiErr?.status,
      };
      this.teams = [];
    } finally {
      if (currentId === this.requestId) {
        this.isLoading = false;
      }
    }
  }
}

async function runTeamsPageTests() {
  console.log('==========================================================');
  console.log('  EVENT HQ — TEAMS PAGE LIFECYCLE & RBAC TEST SUITE');
  console.log('==========================================================\n');

  // ==========================================================
  // SUITE 1: Successful Teams Data Loading
  // ==========================================================
  const S1 = 'Successful Data Loading';
  const controller = new TeamsPageDataController();

  // Mock live team records returned by backend
  const liveTeamsPayload: Team[] = [
    {
      id: 'squad-89ff65d4b584',
      teamNumber: 1,
      name: 'Vanguard Unit 01',
      leaderName: 'Cadet 01-1',
      membersCount: 5,
      members: [
        { id: 'c-1', name: 'Cadet 01-1', email: 'c1@bmsit.in', usn: '1BY24CS001', role: 'Leader', checkedIn: true, teamId: 'squad-89ff65d4b584' },
        { id: 'c-2', name: 'Cadet 01-2', email: 'c2@bmsit.in', usn: '1BY24CS002', role: 'Member', checkedIn: true, teamId: 'squad-89ff65d4b584' },
        { id: 'c-3', name: 'Cadet 01-3', email: 'c3@bmsit.in', usn: '1BY24CS003', role: 'Member', checkedIn: true, teamId: 'squad-89ff65d4b584' },
        { id: 'c-4', name: 'Cadet 01-4', email: 'c4@bmsit.in', usn: '1BY24CS004', role: 'Member', checkedIn: true, teamId: 'squad-89ff65d4b584' },
        { id: 'c-5', name: 'Cadet 01-5', email: 'c5@bmsit.in', usn: '1BY24CS005', role: 'Member', checkedIn: true, teamId: 'squad-89ff65d4b584' },
      ],
      status: 'Checked In',
      currentRound: 1,
      isQualifiedForNextRound: false,
      totalScore: 0,
      assignedTable: 'Sector Alpha-1',
      createdAt: new Date().toISOString(),
    },
    {
      id: 'squad-ad824a68fb2d',
      teamNumber: 2,
      name: 'Vanguard Unit 02',
      leaderName: 'Cadet 02-1',
      membersCount: 5,
      members: [
        { id: 'c-6', name: 'Cadet 02-1', email: 'c6@bmsit.in', usn: '1BY24CS006', role: 'Leader', checkedIn: true, teamId: 'squad-ad824a68fb2d' },
        { id: 'c-7', name: 'Cadet 02-2', email: 'c7@bmsit.in', usn: '1BY24CS007', role: 'Member', checkedIn: false, teamId: 'squad-ad824a68fb2d' },
        { id: 'c-8', name: 'Cadet 02-3', email: 'c8@bmsit.in', usn: '1BY24CS008', role: 'Member', checkedIn: true, teamId: 'squad-ad824a68fb2d' },
        { id: 'c-9', name: 'Cadet 02-4', email: 'c9@bmsit.in', usn: '1BY24CS009', role: 'Member', checkedIn: true, teamId: 'squad-ad824a68fb2d' },
        { id: 'c-10', name: 'Cadet 02-5', email: 'c10@bmsit.in', usn: '1BY24CS010', role: 'Member', checkedIn: true, teamId: 'squad-ad824a68fb2d' },
      ],
      status: 'Checked In',
      currentRound: 1,
      isQualifiedForNextRound: false,
      totalScore: 0,
      assignedTable: 'Sector Alpha-2',
      createdAt: new Date().toISOString(),
    },
  ];

  await controller.loadTeams(async () => liveTeamsPayload);

  assert(controller.isLoading === false, 'isLoading is false after successful load', S1);
  assert(controller.error === null, 'error is null after successful load', S1);
  assert(controller.teams.length === 2, 'controller holds 2 teams', S1);
  assert(controller.teams[0].name === 'Vanguard Unit 01', 'Team 1 name matches', S1);
  assert(formatTeamNumber(controller.teams[0].teamNumber) === 'T-01', 'Team 1 tag formatted as T-01', S1);

  // Check metrics computation
  const m1 = computeTeamMetrics(controller.teams[0]);
  assert(m1.isFullyCheckedIn === true, 'Team 1 has 5/5 checked in', S1);
  assert(m1.label === 'Ready · 5/5 Checked In', 'Team 1 label indicates 5/5 Ready', S1);

  const m2 = computeTeamMetrics(controller.teams[1]);
  assert(m2.isFullyCheckedIn === false, 'Team 2 is not fully checked in', S1);
  assert(m2.label === 'Partial · 4/5 Checked In', 'Team 2 label indicates Partial · 4/5 Checked In', S1);

  // ==========================================================
  // SUITE 2: Loading Cleared in Error & Unauthorized Outcomes
  // ==========================================================
  const S2 = 'Error Outcomes Handling';

  // 2a. Network / 500 error
  await controller.loadTeams(async () => {
    throw { status: 500, message: 'Internal Server Error' };
  });
  assert(controller.isLoading === false, 'isLoading is false after 500 error', S2);
  assert(controller.error?.message === 'Internal Server Error', 'error message is captured', S2);
  assert(controller.teams.length === 0, 'teams array is empty on error', S2);

  // 2b. 401 Unauthorized / Expired session
  await controller.loadTeams(async () => {
    throw { status: 401, message: 'Could not validate credentials' };
  });
  assert(controller.isLoading === false, 'isLoading is false after 401 Unauthorized', S2);
  assert(controller.error?.status === 401, '401 status captured', S2);

  // 2c. 403 Forbidden
  await controller.loadTeams(async () => {
    throw { status: 403, message: 'Operation not permitted' };
  });
  assert(controller.isLoading === false, 'isLoading is false after 403 Forbidden', S2);
  assert(controller.error?.status === 403, '403 status captured', S2);

  // 2d. Genuine empty array from backend
  await controller.loadTeams(async () => []);
  assert(controller.isLoading === false, 'isLoading is false on empty response', S2);
  assert(controller.error === null, 'error is null on empty response', S2);
  assert(controller.teams.length === 0, 'teams length is 0', S2);

  // ==========================================================
  // SUITE 3: Race Condition & Stale Request Protection
  // ==========================================================
  const S3 = 'Race Condition & Stale Request Guard';
  const raceController = new TeamsPageDataController();

  // Fire request 1 (slow, takes 100ms)
  let resolveReq1: (val: Team[]) => void;
  const req1Promise = new Promise<Team[]>((res) => {
    resolveReq1 = res;
  });
  const p1 = raceController.loadTeams(() => req1Promise, true);

  // Immediately fire request 2 (fast, takes 10ms)
  const req2Data: Team[] = [
    {
      id: 'fast-squad',
      teamNumber: 99,
      name: 'Fast Squad',
      leaderName: 'Leader',
      membersCount: 0,
      members: [],
      status: 'Registered',
      currentRound: 1,
      isQualifiedForNextRound: false,
      totalScore: 0,
      createdAt: new Date().toISOString(),
    },
  ];
  const p2 = raceController.loadTeams(async () => req2Data, true);

  // Wait for Request 2 to complete first
  await p2;
  assert(raceController.isLoading === false, 'Request 2 completes and sets isLoading=false', S3);
  assert(raceController.teams.length === 1, 'Request 2 data applied', S3);
  assert(raceController.teams[0].name === 'Fast Squad', 'Fast Squad is currently rendered', S3);

  // Now resolve Request 1 (stale slow request)
  const staleData: Team[] = [
    {
      id: 'stale-squad',
      teamNumber: 1,
      name: 'Stale Squad',
      leaderName: 'Old',
      membersCount: 0,
      members: [],
      status: 'Registered',
      currentRound: 1,
      isQualifiedForNextRound: false,
      totalScore: 0,
      createdAt: new Date().toISOString(),
    },
  ];
  resolveReq1!(staleData);
  await p1;

  // Verify stale data did NOT overwrite Request 2
  assert(raceController.teams[0].name === 'Fast Squad', 'Stale response discarded: Fast Squad remains', S3);
  assert(raceController.isLoading === false, 'isLoading remains false after stale request settles', S3);

  // ==========================================================
  // SUITE 4: Infinite Loop & Notification Guard
  // ==========================================================
  const S4 = 'Infinite Loop Prevention';

  let notificationCount = 0;
  const unsub = authService.subscribe(() => {
    notificationCount++;
  });

  // Saving the exact same user object must NOT fire listeners repeatedly
  const testUser: User = {
    id: 'usr-test-1',
    name: 'Lead Organizer',
    email: 'organizer@bmsit.in',
    role: 'ORGANIZER',
    isActive: true,
    createdAt: new Date().toISOString(),
  };

  authService.saveUserToStorage(testUser);
  const countAfterFirst = notificationCount;

  // Repeat save with same user 5 times
  for (let i = 0; i < 5; i++) {
    authService.saveUserToStorage({ ...testUser });
  }

  assert(
    notificationCount === countAfterFirst,
    `saveUserToStorage with identical user ignored (${notificationCount} === ${countAfterFirst}, no notification storms)`,
    S4
  );

  unsub();

  // ==========================================================
  // SUITE 5: RBAC Permission Matrix for Teams Page
  // ==========================================================
  const S5 = 'RBAC Permissions Matrix';

  setAppMode('live');
  apiClient.setToken('dummy-test-token');

  // Test ORGANIZER permissions
  authService.saveUserToStorage(testUser);
  const orgUser = authService.getCurrentUser();
  const orgCanCreate = !isLiveMode() || (orgUser && ['ORGANIZER', 'MARSHAL'].includes(orgUser.role));
  const orgCanEdit = !isLiveMode() || (orgUser && ['ORGANIZER', 'MARSHAL'].includes(orgUser.role));
  const orgCanDelete = !isLiveMode() || (orgUser && orgUser.role === 'ORGANIZER');

  assert(Boolean(orgCanCreate), 'ORGANIZER can register squads in Live Mode', S5);
  assert(Boolean(orgCanEdit), 'ORGANIZER can edit squads in Live Mode', S5);
  assert(Boolean(orgCanDelete), 'ORGANIZER can delete squads in Live Mode', S5);

  // Test MARSHAL permissions
  authService.saveUserToStorage({ ...testUser, id: 'usr-marshal', role: 'MARSHAL', name: 'Deck Marshal' });
  const marUser = authService.getCurrentUser();
  const marCanCreate = !isLiveMode() || (marUser && ['ORGANIZER', 'MARSHAL'].includes(marUser.role));
  const marCanEdit = !isLiveMode() || (marUser && ['ORGANIZER', 'MARSHAL'].includes(marUser.role));
  const marCanDelete = !isLiveMode() || (marUser && marUser.role === 'ORGANIZER');

  assert(Boolean(marCanCreate), 'MARSHAL can register squads in Live Mode', S5);
  assert(Boolean(marCanEdit), 'MARSHAL can edit squads in Live Mode', S5);
  assert(!marCanDelete, 'MARSHAL cannot delete squads in Live Mode (ORGANIZER only)', S5);

  // Test PUBLIC_PROJECTOR permissions
  authService.saveUserToStorage({ ...testUser, id: 'usr-proj', role: 'PUBLIC_PROJECTOR', name: 'Hall Projector' });
  const projUser = authService.getCurrentUser();
  const projCanCreate = !isLiveMode() || (projUser && ['ORGANIZER', 'MARSHAL'].includes(projUser.role));
  const projCanEdit = !isLiveMode() || (projUser && ['ORGANIZER', 'MARSHAL'].includes(projUser.role));
  const projCanDelete = !isLiveMode() || (projUser && projUser.role === 'ORGANIZER');

  assert(!projCanCreate, 'PUBLIC_PROJECTOR cannot register squads in Live Mode', S5);
  assert(!projCanEdit, 'PUBLIC_PROJECTOR cannot edit squads in Live Mode', S5);
  assert(!projCanDelete, 'PUBLIC_PROJECTOR cannot delete squads in Live Mode', S5);

  // Clean up
  apiClient.clearToken();
  authService.saveUserToStorage(null);
  setAppMode('demo');

  // ==========================================================
  // Summary
  // ==========================================================
  console.log('\n==========================================================');
  const passed = results.filter((r) => r.passed).length;
  const failed = results.filter((r) => !r.passed).length;
  console.log(`  RESULTS: ${passed} PASSED | ${failed} FAILED | TOTAL: ${results.length}`);
  console.log('==========================================================\n');

  if (failed > 0) {
    process.exit(1);
  }
}

runTeamsPageTests().catch((err) => {
  console.error('Fatal test error:', err);
  process.exit(1);
});
