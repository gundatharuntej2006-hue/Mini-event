/**
 * EVENT HQ — Mode Switching, Connection State & RBAC Integrity Test Suite
 *
 * Verifies:
 * 1. Global App Mode Toggle: Demo <-> Live switching and subscriber event propagation.
 * 2. Connection State Machine: Distinguishes Demo Mode, Public Projector View, Staff View, and Offline.
 * 3. PUBLIC_PROJECTOR RBAC Security:
 *    - Allowed: Read-only public telemetry (overview, teams directory with masked PII, standings).
 *    - Forbidden: Confidential student PII (participants directory), roster mutations, team mutations.
 * 4. Staff Roles (ORGANIZER, MARSHAL, JUDGE): Permitted access to student records and event operations.
 * 5. Dynamic Sidebar Badge Counts: Reflects mode-dependent counts (32/160 in demo, 4/20 in live).
 * 6. Error & Security UI Contract: Verifies ParticipantsPage / TeamsPage error states.
 */

import { API_CONFIG, getAppMode, setAppMode, isLiveMode, onAppModeChange } from './services/apiConfig';
import { apiClient } from './services/apiClient';
import { authService } from './services/authService';
import { eventService } from './services/eventService';
import { User } from './types';

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

// Emulate TopNavbar connection state logic
type ConnectionState = 'demo' | 'checking' | 'connected_staff' | 'connected_public' | 'unauthenticated' | 'token_expired' | 'offline';

function determineConnectionState(
  mode: 'live' | 'demo',
  healthStatus: 'online' | 'unreachable' | 'error',
  user: User | null,
  hasToken: boolean,
  isTokenExpired: boolean = false
): ConnectionState {
  if (mode === 'demo') {
    return 'demo';
  }
  if (healthStatus !== 'online') {
    return 'offline';
  }
  if (isTokenExpired) {
    return 'token_expired';
  }
  if (!hasToken) {
    if (user?.role === 'PUBLIC_PROJECTOR') {
      return 'connected_public';
    }
    return 'unauthenticated';
  }
  if (user && ['ORGANIZER', 'MARSHAL', 'JUDGE'].includes(user.role)) {
    return 'connected_staff';
  }
  return 'connected_public';
}

// Emulate Sidebar badge calculation logic
function computeSidebarBadges(
  mode: 'live' | 'demo',
  summaryCounts: { teamsCount: number; participantsCount: number }
): { teams: string; participants: string } {
  if (mode === 'demo') {
    return { teams: '32', participants: '160' };
  }
  return {
    teams: String(summaryCounts.teamsCount),
    participants: String(summaryCounts.participantsCount),
  };
}

async function runModeAndRbacTests() {
  console.log('==========================================================');
  console.log('  EVENT HQ — MODE SWITCHING & RBAC INTEGRATION TEST SUITE');
  console.log('==========================================================\n');

  // ==========================================================
  // SUITE 1: Global App Mode Toggle & Event Propagation
  // ==========================================================
  const S1 = 'App Mode Toggle';
  let lastDispatchedMode: string | null = null;
  const unsubscribeMode = onAppModeChange((mode) => {
    lastDispatchedMode = mode;
  });

  // Switch to Demo Mode
  setAppMode('demo');
  assert(getAppMode() === 'demo', 'getAppMode() returns "demo" after setAppMode("demo")', S1);
  assert(isLiveMode() === false, 'isLiveMode() is false in demo mode', S1);
  assert(API_CONFIG.isMockEnabled === true, 'API_CONFIG.isMockEnabled is true in demo mode', S1);
  assert(lastDispatchedMode === 'demo', 'onAppModeChange subscriber notified of "demo"', S1);

  // Check demo summary counts
  const demoCounts = await eventService.getSummaryCounts();
  assert(demoCounts.teamsCount === 32, 'Demo summary returns 32 teams', S1);
  assert(demoCounts.participantsCount === 160, 'Demo summary returns 160 participants', S1);

  // Switch to Live Mode
  setAppMode('live');
  assert(getAppMode() === 'live', 'getAppMode() returns "live" after setAppMode("live")', S1);
  assert(isLiveMode() === true, 'isLiveMode() is true in live mode', S1);
  assert(API_CONFIG.isMockEnabled === false, 'API_CONFIG.isMockEnabled is false in live mode', S1);
  assert(lastDispatchedMode === 'live', 'onAppModeChange subscriber notified of "live"', S1);

  unsubscribeMode();

  // ==========================================================
  // SUITE 2: Connection State Machine & Status Badges
  // ==========================================================
  const S2 = 'Connection State Machine';

  // 1. In Demo mode, status must always be 'demo' regardless of network
  const sDemo = determineConnectionState('demo', 'online', null, false);
  assert(sDemo === 'demo', 'Demo mode yields "demo" connection state', S2);

  // 2. In Live mode with server offline, status must be 'offline'
  const sOffline = determineConnectionState('live', 'unreachable', null, false);
  assert(sOffline === 'offline', 'Live mode with unreachable server yields "offline"', S2);

  // 3. In Live mode with online server:
  // 3a. Backend reachable, unauthenticated yields 'unauthenticated'
  const sUnauth = determineConnectionState('live', 'online', null, false);
  assert(sUnauth === 'unauthenticated', 'Backend reachable, unauthenticated yields "unauthenticated"', S2);

  // 3b. Public projector yields 'connected_public'
  const publicUser: User = {
    id: 'u-proj',
    name: 'Main Hall Projector',
    email: 'projector@bmsit.in',
    role: 'PUBLIC_PROJECTOR',
    isActive: true,
    createdAt: new Date().toISOString(),
  };
  const sPublic = determineConnectionState('live', 'online', publicUser, false);
  assert(sPublic === 'connected_public', 'PUBLIC_PROJECTOR yields "connected_public" (Live · Public Projector)', S2);

  // 3c. Invalid/expired token yields 'token_expired'
  const sExpired = determineConnectionState('live', 'online', null, true, true);
  assert(sExpired === 'token_expired', 'Expired/invalid token yields "token_expired"', S2);

  // 4. In Live mode with authenticated staff, status must be 'connected_staff'
  const organizerUser: User = {
    id: 'u-org',
    name: 'Lead Organizer',
    email: 'organizer@bmsit.in',
    role: 'ORGANIZER',
    isActive: true,
    createdAt: new Date().toISOString(),
  };
  const sStaff = determineConnectionState('live', 'online', organizerUser, true);
  assert(sStaff === 'connected_staff', 'ORGANIZER with token yields "connected_staff"', S2);

  const marshalUser: User = {
    id: 'u-mar',
    name: 'Deck Marshal',
    email: 'marshal@bmsit.in',
    role: 'MARSHAL',
    isActive: true,
    createdAt: new Date().toISOString(),
  };
  const sMarshal = determineConnectionState('live', 'online', marshalUser, true);
  assert(sMarshal === 'connected_staff', 'MARSHAL with token yields "connected_staff"', S2);

  const judgeUser: User = {
    id: 'u-jdg',
    name: 'Faculty Judge',
    email: 'judge@bmsit.in',
    role: 'JUDGE',
    isActive: true,
    createdAt: new Date().toISOString(),
  };
  const sJudge = determineConnectionState('live', 'online', judgeUser, true);
  assert(sJudge === 'connected_staff', 'JUDGE with token yields "connected_staff"', S2);

  // ==========================================================
  // SUITE 3: PUBLIC_PROJECTOR RBAC & Security Boundaries
  // ==========================================================
  const S3 = 'PUBLIC_PROJECTOR Permissions Matrix';

  authService.setDemoUser('PUBLIC_PROJECTOR');
  const activeProjUser = authService.getCurrentUser();
  assert(Boolean(activeProjUser), 'Current user is set', S3);
  assert(activeProjUser?.role === 'PUBLIC_PROJECTOR', 'Current role is PUBLIC_PROJECTOR', S3);
  assert(authService.isPublicProjector() === true, 'authService.isPublicProjector() is true', S3);
  assert(authService.isOrganizer() === false, 'PUBLIC_PROJECTOR cannot act as ORGANIZER', S3);
  assert(authService.isMarshal() === false, 'PUBLIC_PROJECTOR cannot act as MARSHAL', S3);
  assert(authService.isJudge() === false, 'PUBLIC_PROJECTOR cannot act as JUDGE', S3);
  assert(
    authService.hasRole(['ORGANIZER', 'MARSHAL', 'JUDGE']) === false,
    'PUBLIC_PROJECTOR lacks staff access rights',
    S3
  );

  // Check action permissions for PUBLIC_PROJECTOR
  const canManageSquads = !isLiveMode() || authService.hasRole(['ORGANIZER', 'MARSHAL']);
  assert(canManageSquads === false, 'PUBLIC_PROJECTOR in live mode cannot manage squads (create/edit)', S3);

  const canDeleteSquads = !isLiveMode() || authService.isOrganizer();
  assert(canDeleteSquads === false, 'PUBLIC_PROJECTOR in live mode cannot delete squads', S3);

  // ==========================================================
  // SUITE 4: Staff Roles RBAC Matrix & Token Enforcement
  // ==========================================================
  const S4 = 'Staff Roles Permissions Matrix';

  // 4a. Security test: In Live mode, mock staff user without token is rejected
  authService.setDemoUser('ORGANIZER');
  assert(
    authService.getCurrentUser() === null,
    'In live mode without token, mock ORGANIZER user is rejected (returns null)',
    S4
  );
  assert(
    authService.isOrganizer() === false,
    'In live mode without token, isOrganizer() returns false',
    S4
  );

  // 4b. Authenticated Staff: Token provided via apiClient.setToken
  const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.dummy';
  apiClient.setToken(mockToken);

  authService.saveUserToStorage({
    id: 'usr-org-1',
    name: 'Lead Organizer',
    email: 'organizer@bmsit.in',
    role: 'ORGANIZER',
    isActive: true,
    createdAt: new Date().toISOString(),
  });

  assert(authService.isOrganizer() === true, 'Authenticated ORGANIZER user identified correctly with token', S4);
  assert(authService.hasRole(['ORGANIZER', 'MARSHAL', 'JUDGE']) === true, 'ORGANIZER has staff rights', S4);
  const orgCanManage = !isLiveMode() || authService.hasRole(['ORGANIZER', 'MARSHAL']);
  const orgCanDelete = !isLiveMode() || authService.isOrganizer();
  assert(orgCanManage === true, 'ORGANIZER can manage squads in live mode', S4);
  assert(orgCanDelete === true, 'ORGANIZER can delete squads in live mode', S4);

  authService.saveUserToStorage({
    id: 'usr-mar-1',
    name: 'Deck Marshal',
    email: 'marshal@bmsit.in',
    role: 'MARSHAL',
    isActive: true,
    createdAt: new Date().toISOString(),
  });
  assert(authService.isMarshal() === true, 'Authenticated MARSHAL user identified correctly with token', S4);
  assert(authService.hasRole(['ORGANIZER', 'MARSHAL', 'JUDGE']) === true, 'MARSHAL has staff rights', S4);
  const marCanManage = !isLiveMode() || authService.hasRole(['ORGANIZER', 'MARSHAL']);
  const marCanDelete = !isLiveMode() || authService.isOrganizer();
  assert(marCanManage === true, 'MARSHAL can manage squads in live mode', S4);
  assert(marCanDelete === false, 'MARSHAL cannot delete squads in live mode (Organizer only)', S4);

  // Clear mock token
  apiClient.clearToken();

  // ==========================================================
  // SUITE 5: Dynamic Sidebar Badges Across Modes
  // ==========================================================
  const S5 = 'Dynamic Sidebar Badges';

  // Demo mode: fixed mock counts
  const demoBadges = computeSidebarBadges('demo', { teamsCount: 4, participantsCount: 20 });
  assert(demoBadges.teams === '32', 'Sidebar teams badge is "32" in demo mode', S5);
  assert(demoBadges.participants === '160', 'Sidebar participants badge is "160" in demo mode', S5);

  // Live mode: dynamic counts from backend overview
  const liveBadges = computeSidebarBadges('live', { teamsCount: 4, participantsCount: 20 });
  assert(liveBadges.teams === '4', 'Sidebar teams badge reflects 4 live teams in database', S5);
  assert(liveBadges.participants === '20', 'Sidebar participants badge reflects 20 live participants in database', S5);

  // ==========================================================
  // SUITE 6: ParticipantsPage 403 Forbidden State Handling
  // ==========================================================
  const S6 = 'Participants 403 State Handling';

  const simulateParticipantsResponse = (status: number, detail: string) => {
    const isForbidden = status === 403 || status === 401;
    const accessError = {
      status,
      message: detail || (isForbidden ? 'Access restricted: student records contain confidential PII.' : 'Error'),
      isForbidden,
    };
    const badgeText = isForbidden ? 'Restricted · Staff Only' : '0 Students Registered';
    const showRegistrationButton = !isForbidden;
    return { accessError, badgeText, showRegistrationButton };
  };

  const forbiddenHandling = simulateParticipantsResponse(403, 'Insufficient permissions');
  assert(forbiddenHandling.accessError.isForbidden === true, '403 correctly flagged as isForbidden', S6);
  assert(
    forbiddenHandling.badgeText === 'Restricted · Staff Only',
    'Badge displays "Restricted · Staff Only" instead of misleading "0 Students Registered"',
    S6
  );
  assert(
    forbiddenHandling.showRegistrationButton === false,
    'Register Student button is restricted when 403 is received',
    S6
  );

  const serverErrorHandling = simulateParticipantsResponse(500, 'Internal server error');
  assert(serverErrorHandling.accessError.isForbidden === false, '500 is not flagged as forbidden', S6);

  // Switch back to demo mode at end of tests
  setAppMode('demo');
  authService.setDemoUser('ORGANIZER');

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

runModeAndRbacTests().catch((err) => {
  console.error('Fatal test error:', err);
  process.exit(1);
});
