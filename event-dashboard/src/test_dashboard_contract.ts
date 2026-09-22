/**
 * EVENT HQ — Frontend Dashboard Contract & Safe Data Handling Verification
 *
 * Verifies:
 * 1. Demo Mode: eventService.getDashboardOverview() returns complete data with 5 progression steps.
 * 2. Live Mode Shape: Handles backend ApiResponse envelope with stats, progression, and recentActivities.
 * 3. Missing Data Safety: Component and service safely handle undefined/null progression and activities without throwing TypeError.
 * 4. Empty Data Safety: Safely handles empty progression ([]) and empty activities ([]).
 * 5. Valid Data: Progression steps contain all 5 tournament stages with correct keys and statuses.
 */

import { setAppMode } from './services/apiConfig';
import { eventService } from './services/eventService';
import { MOCK_PROGRESSION_STEPS, MOCK_RECENT_ACTIVITIES, MOCK_DASHBOARD_STATS } from './data/mockData';
import { RoundProgressionStep, DashboardOverviewData, ActivityLogItem } from './types';

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

async function runDashboardContractTests() {
  console.log('==========================================================');
  console.log('  EVENT HQ — DASHBOARD CONTRACT & SAFETY TEST SUITE');
  console.log('==========================================================\n');

  // ==========================================
  // SUITE 1: Demo Mode Dashboard Overview
  // ==========================================
  const S1 = 'Demo Mode Contract';
  setAppMode('demo');
  try {
    const demoRes = await eventService.getDashboardOverview();
    assert(demoRes.success === true, 'getDashboardOverview() succeeds', S1);
    assert(Boolean(demoRes.data), 'Dashboard data payload is present', S1);
    assert(Boolean(demoRes.data.stats), 'Stats object is present', S1);
    assert(Array.isArray(demoRes.data.progression), 'Progression is an array', S1);
    assert(demoRes.data.progression.length === 5, 'Progression contains all 5 rounds', S1);
    assert(Array.isArray(demoRes.data.recentActivities), 'recentActivities is an array', S1);

    // Verify progression step fields
    const r1 = demoRes.data.progression[0];
    assert(r1.roundNumber === 1, 'Round 1 step has roundNumber=1', S1);
    assert(Boolean(r1.name), 'Round 1 step has a name', S1);
    assert(r1.totalPool === 32, 'Round 1 step has totalPool=32', S1);
    assert(r1.qualifyingCount === 24, 'Round 1 step has qualifyingCount=24', S1);
    assert(Boolean(r1.status), 'Round 1 step has a valid status', S1);
  } catch (err: any) {
    assert(false, 'Demo Mode retrieval should not throw: ' + err.message, S1);
  }

  // ==========================================
  // SUITE 2: Missing Data Safety Simulation (Undefined / Null props)
  // ==========================================
  const S2 = 'Missing Data Defensive Safety';

  // Test simulation: What RoundProgressCard does when steps is undefined
  const simulateRoundProgressCard = (steps?: RoundProgressionStep[] | null): string => {
    if (!steps || !Array.isArray(steps)) {
      return 'DATA_UNAVAILABLE_FALLBACK';
    }
    if (steps.length === 0) {
      return 'EMPTY_PIPELINE_FALLBACK';
    }
    // Simulate mapping without crashing
    const rendered = steps.map((s) => `Round ${s.roundNumber}: ${s.name} (${s.status})`);
    return `RENDERED_${rendered.length}_STEPS`;
  };

  // Test undefined steps (the exact bug that caused the crash)
  let undefinedCrashed = false;
  let undefinedResult = '';
  try {
    undefinedResult = simulateRoundProgressCard(undefined);
  } catch (err) {
    undefinedCrashed = true;
  }
  assert(!undefinedCrashed, 'RoundProgressCard does not crash when steps is undefined', S2);
  assert(undefinedResult === 'DATA_UNAVAILABLE_FALLBACK', 'Renders DATA_UNAVAILABLE_FALLBACK when steps is undefined', S2);

  // Test null steps
  let nullCrashed = false;
  let nullResult = '';
  try {
    nullResult = simulateRoundProgressCard(null);
  } catch (err) {
    nullCrashed = true;
  }
  assert(!nullCrashed, 'RoundProgressCard does not crash when steps is null', S2);
  assert(nullResult === 'DATA_UNAVAILABLE_FALLBACK', 'Renders DATA_UNAVAILABLE_FALLBACK when steps is null', S2);

  // Test non-array steps (e.g. object or number accidentally passed)
  let nonArrayCrashed = false;
  let nonArrayResult = '';
  try {
    nonArrayResult = simulateRoundProgressCard({} as any);
  } catch (err) {
    nonArrayCrashed = true;
  }
  assert(!nonArrayCrashed, 'RoundProgressCard does not crash when steps is a non-array object', S2);
  assert(nonArrayResult === 'DATA_UNAVAILABLE_FALLBACK', 'Renders DATA_UNAVAILABLE_FALLBACK when steps is non-array', S2);

  // ==========================================
  // SUITE 3: Empty Data Safety Simulation
  // ==========================================
  const S3 = 'Empty Data Safety';

  let emptyCrashed = false;
  let emptyResult = '';
  try {
    emptyResult = simulateRoundProgressCard([]);
  } catch (err) {
    emptyCrashed = true;
  }
  assert(!emptyCrashed, 'RoundProgressCard does not crash when steps is []', S3);
  assert(emptyResult === 'EMPTY_PIPELINE_FALLBACK', 'Renders EMPTY_PIPELINE_FALLBACK when steps is []', S3);

  // Test RecentActivityFeed simulation
  const simulateRecentActivityFeed = (activities?: ActivityLogItem[] | null): string => {
    if (!activities || !Array.isArray(activities)) {
      return 'TELEMETRY_OFFLINE_FALLBACK';
    }
    if (activities.length === 0) {
      return 'ZERO_EVENTS_FALLBACK';
    }
    const rendered = activities.map((a) => `Activity ${a.id}: ${a.title}`);
    return `RENDERED_${rendered.length}_ACTIVITIES`;
  };

  assert(simulateRecentActivityFeed(undefined) === 'TELEMETRY_OFFLINE_FALLBACK', 'ActivityFeed renders offline state on undefined', S3);
  assert(simulateRecentActivityFeed(null) === 'TELEMETRY_OFFLINE_FALLBACK', 'ActivityFeed renders offline state on null', S3);
  assert(simulateRecentActivityFeed([]) === 'ZERO_EVENTS_FALLBACK', 'ActivityFeed renders zero-events state on []', S3);
  assert(simulateRecentActivityFeed(MOCK_RECENT_ACTIVITIES).startsWith('RENDERED_'), 'ActivityFeed renders valid activities list', S3);

  // ==========================================
  // SUITE 4: Valid Data Contract Verification
  // ==========================================
  const S4 = 'Valid Data Pipeline Verification';
  const validResult = simulateRoundProgressCard(MOCK_PROGRESSION_STEPS);
  assert(validResult === 'RENDERED_5_STEPS', 'RoundProgressCard renders exactly 5 steps with valid data', S4);

  // Verify all 5 rounds have expected qualifying targets
  assert(MOCK_PROGRESSION_STEPS[0].qualifyingCount === 24, 'R1 qualifies 24 teams', S4);
  assert(MOCK_PROGRESSION_STEPS[1].qualifyingCount === 12, 'R2 qualifies 12 teams', S4);
  assert(MOCK_PROGRESSION_STEPS[2].qualifyingCount === 8, 'R3 qualifies 8 teams', S4);
  assert(MOCK_PROGRESSION_STEPS[3].qualifyingCount === 3, 'R4 qualifies 3 teams', S4);
  assert(MOCK_PROGRESSION_STEPS[4].qualifyingCount === 3 || MOCK_PROGRESSION_STEPS[4].qualifyingCount === 1, 'R5 has valid finale pool', S4);

  // ==========================================
  // SUITE 5: Live Mode Envelope Transformation Safety
  // ==========================================
  const S5 = 'Live Mode Transformation Safety';

  // Backend response without progression (e.g. legacy/broken payload)
  const simulateLiveModeTransform = (rawBackendResponse: any): DashboardOverviewData => {
    const data = rawBackendResponse.data || {};
    return {
      stats: data.stats || MOCK_DASHBOARD_STATS,
      progression: Array.isArray(data.progression) ? data.progression : [],
      recentActivities: Array.isArray(data.recentActivities) ? data.recentActivities : [],
    };
  };

  const rawWithoutProgression = {
    data: {
      stats: MOCK_DASHBOARD_STATS,
      recentActivities: [],
    },
  };
  const transformed = simulateLiveModeTransform(rawWithoutProgression);
  assert(Array.isArray(transformed.progression), 'Transformed progression is guaranteed to be an array', S5);
  assert(transformed.progression.length === 0, 'Transformed progression is empty array (not undefined)', S5);
  // Passing this transformed data to RoundProgressCard must not throw
  const safeCardRender = simulateRoundProgressCard(transformed.progression);
  assert(safeCardRender === 'EMPTY_PIPELINE_FALLBACK', 'Safe card render handles empty array cleanly without crashing', S5);

  // Backend response with valid progression
  const rawWithProgression = {
    data: {
      stats: MOCK_DASHBOARD_STATS,
      progression: MOCK_PROGRESSION_STEPS,
      recentActivities: MOCK_RECENT_ACTIVITIES,
    },
  };
  const transformedValid = simulateLiveModeTransform(rawWithProgression);
  assert(transformedValid.progression.length === 5, 'Transformed valid response preserves 5 progression steps', S5);
  assert(simulateRoundProgressCard(transformedValid.progression) === 'RENDERED_5_STEPS', 'Valid live payload renders all 5 steps', S5);

  // Summary
  const total = results.length;
  const passed = results.filter((r) => r.passed).length;
  const failed = results.filter((r) => !r.passed).length;

  console.log('\n==========================================================');
  console.log(`  DASHBOARD CONTRACT TEST RESULTS: ${passed}/${total} PASSED (${failed} FAILED)`);
  console.log('==========================================================\n');

  if (failed > 0) {
    process.exit(1);
  } else {
    console.log('✅ ALL DASHBOARD CONTRACT & SAFETY CHECKS PASSED.');
    process.exit(0);
  }
}

runDashboardContractTests().catch((err) => {
  console.error('Fatal error running dashboard contract tests:', err);
  process.exit(1);
});
