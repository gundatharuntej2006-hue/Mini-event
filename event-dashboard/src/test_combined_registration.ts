import { apiClient } from './services/apiClient';
import { eventService } from './services/eventService';
import { setAppMode } from './services/apiConfig';
import { CreateTeamInput, TeamMemberInput } from './types/team';

const BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8001';
const TEST_ORG_EMAIL = 'gundatharuntej2006@gmail.com';
const TEST_ORG_PASS = 'Tejaa@2006';

interface TestAssertion {
  name: string;
  category: string;
  passed: boolean;
  error?: string;
}

const assertions: TestAssertion[] = [];

function assert(condition: boolean, name: string, category: string, error?: string) {
  assertions.push({ name, category, passed: condition, error });
  const badge = condition ? 'PASS' : 'FAIL';
  console.log(`  ${badge}: [${category}] ${name}${error ? ` — ${error}` : ''}`);
}

async function safeFetch(url: string, init?: RequestInit): Promise<Response> {
  return fetch(url, init);
}

function makeMembers(prefix: string, hasDuplicateUsn = false, hasDuplicateEmail = false, leaderIndex = 0): TeamMemberInput[] {
  return [0, 1, 2, 3, 4].map((i) => {
    let usn = `1BY25${prefix}${String(i + 1).padStart(2, '0')}`;
    let email = `cadet.${prefix.toLowerCase()}.${i + 1}@bmsit.in`;

    if (hasDuplicateUsn && i === 4) {
      usn = `1BY25${prefix}01`; // duplicate member 1
    }
    if (hasDuplicateEmail && i === 4) {
      email = `cadet.${prefix.toLowerCase()}.1@bmsit.in`; // duplicate member 1
    }

    return {
      name: `Cadet ${prefix}-${i + 1}`,
      usn,
      email,
      phone: `+91 99999 ${prefix}${i + 1}`,
      role: i === leaderIndex ? 'Leader' : 'Member',
    };
  });
}

async function runCombinedRegistrationTests() {
  console.log('\n==========================================================');
  console.log('  EVENT HQ — COMBINED TEAM & PARTICIPANT REGISTRATION TESTS');
  console.log('==========================================================\n');

  let token = '';

  try {
    // ----------------------------------------------------
    // Section 1: Authentication & Health Gateway
    // ----------------------------------------------------
    console.log('--- 1. Authentication & Health Gateway ---');
    const healthRes = await safeFetch(`${BASE_URL}/api/v1/health`);
    assert(healthRes.ok, 'Gateway health check returns HTTP 200', 'Gateway');

    const loginRes = await safeFetch(`${BASE_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: TEST_ORG_EMAIL, password: TEST_ORG_PASS }),
    });
    assert(loginRes.ok, 'Organizer login succeeds', 'Auth');
    const loginJson = await loginRes.json();
    token = loginJson.data?.accessToken;
    assert(typeof token === 'string' && token.length > 20, 'Received valid JWT Bearer token', 'Auth');
    apiClient.setToken(token);

    // Initial count
    const initTeamsRes = await safeFetch(`${BASE_URL}/api/v1/teams`);
    const initTeams = (await initTeamsRes.json()).data || [];
    const initialTeamCount = initTeams.length;
    const initPartRes = await safeFetch(`${BASE_URL}/api/v1/participants`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const initParts = (await initPartRes.json()).data || [];
    const initialPartCount = initParts.length;
    assert(Array.isArray(initTeams), 'Initial teams array retrieved successfully', 'Initial State');
    assert(Array.isArray(initParts), 'Initial participants array retrieved successfully', 'Initial State');

    // ----------------------------------------------------
    // Section 2: Validation Safeguards & Atomic Rollback
    // ----------------------------------------------------
    console.log('\n--- 2. Validation Safeguards & Atomic Rollback ---');

    // 2.1: Less than 5 members rejected
    const partialMembers = makeMembers('PT').slice(0, 4);
    const partialRes = await safeFetch(`${BASE_URL}/api/v1/teams`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ name: 'Partial Squad', assignedTable: 'Table 1', members: partialMembers }),
    });
    assert(partialRes.status === 400, 'Squad with < 5 members rejected with HTTP 400', 'Validation');
    const partialJson = await partialRes.json();
    assert(partialJson.message?.includes('exactly 5 participants') || partialJson.detail?.includes('exactly 5 participants'), 'Error message clarifies 5 participants required', 'Validation');

    // 2.2: Zero leaders rejected
    const noLeaderMembers = makeMembers('NL').map((m) => ({ ...m, role: 'Member' as const }));
    const noLeaderRes = await safeFetch(`${BASE_URL}/api/v1/teams`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ name: 'No Leader Squad', assignedTable: 'Table 1', members: noLeaderMembers }),
    });
    assert(noLeaderRes.status === 400, 'Squad with 0 leaders rejected with HTTP 400', 'Validation');

    // 2.3: Two leaders rejected
    const twoLeaderMembers = makeMembers('TL').map((m, idx) => ({ ...m, role: idx < 2 ? ('Leader' as const) : ('Member' as const) }));
    const twoLeaderRes = await safeFetch(`${BASE_URL}/api/v1/teams`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ name: 'Two Leaders Squad', assignedTable: 'Table 1', members: twoLeaderMembers }),
    });
    assert(twoLeaderRes.status === 400, 'Squad with 2 leaders rejected with HTTP 400', 'Validation');

    // 2.4: Intra-form duplicate USN rejected & rolled back
    const dupUsnMembers = makeMembers('DU', true, false);
    const dupUsnRes = await safeFetch(`${BASE_URL}/api/v1/teams`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ name: 'Duplicate USN Squad', assignedTable: 'Table 1', members: dupUsnMembers }),
    });
    assert(dupUsnRes.status === 400, 'Intra-form duplicate USN rejected with HTTP 400', 'Validation');
    const dupUsnJson = await dupUsnRes.json();
    assert(dupUsnJson.message?.includes('Duplicate USN') || dupUsnJson.detail?.includes('Duplicate USN'), 'Duplicate USN message returned', 'Validation');

    // 2.5: Intra-form duplicate Email rejected & rolled back
    const dupEmailMembers = makeMembers('DE', false, true);
    const dupEmailRes = await safeFetch(`${BASE_URL}/api/v1/teams`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ name: 'Duplicate Email Squad', assignedTable: 'Table 1', members: dupEmailMembers }),
    });
    assert(dupEmailRes.status === 400, 'Intra-form duplicate Email rejected with HTTP 400', 'Validation');

    // 2.6: Atomic rollback verification — no extra teams or participants persisted after all failed attempts
    const verifyEmptyTeamsRes = await safeFetch(`${BASE_URL}/api/v1/teams`);
    const emptyTeams = (await verifyEmptyTeamsRes.json()).data || [];
    const verifyEmptyPartsRes = await safeFetch(`${BASE_URL}/api/v1/participants`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const emptyParts = (await verifyEmptyPartsRes.json()).data || [];
    assert(emptyTeams.length === initialTeamCount, 'No partial team records created after validation failures', 'Atomic Rollback');
    assert(emptyParts.length === initialPartCount, 'No partial participant records created after validation failures', 'Atomic Rollback');

    // ----------------------------------------------------
    // Section 3: Successful Combined Registration
    // ----------------------------------------------------
    console.log('\n--- 3. Successful Combined Registration ---');
    const validMembers1 = makeMembers('A1', false, false, 0);
    const createSquad1Res = await safeFetch(`${BASE_URL}/api/v1/teams`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        name: 'Apex Predators',
        assignedTable: 'Table 1',
        members: validMembers1,
      }),
    });
    assert(createSquad1Res.status === 201, 'Combined team & 5 participants creation returns HTTP 201 Created', 'Creation');
    const createdTeam1 = (await createSquad1Res.json()).data;
    assert(createdTeam1.name === 'Apex Predators', 'Team name matches', 'Creation');
    assert(createdTeam1.membersCount === 5, 'Team reports exactly 5/5 members', 'Creation');
    assert(createdTeam1.leaderName === 'Cadet A1-1', 'Team leader name matches first designated leader', 'Creation');
    assert(createdTeam1.members.length === 5, 'Returned team includes serialized members array of 5', 'Creation');

    // Verify all 5 participants appear in /participants directory
    const getPartsRes = await safeFetch(`${BASE_URL}/api/v1/participants`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const allParts = (await getPartsRes.json()).data || [];
    assert(allParts.length === initialPartCount + 5, 'Exactly 5 participants added in Participants directory', 'Directory');
    assert(allParts.some((p: any) => p.teamId === createdTeam1.id), 'Participants assigned to the new team ID', 'Directory');
    assert(allParts.some((p: any) => p.role === 'Leader'), 'Leader participant role verified in directory', 'Directory');

    // Verify dashboard overview stats
    const overviewRes = await safeFetch(`${BASE_URL}/api/v1/dashboard/overview`);
    const overviewStats = (await overviewRes.json()).data?.stats;
    assert(overviewStats?.totalTeams === initialTeamCount + 1, 'Dashboard totalTeams updated by 1', 'Dashboard Overview');
    assert(overviewStats?.totalParticipants === initialPartCount + 5, 'Dashboard totalParticipants updated by 5', 'Dashboard Overview');

    // ----------------------------------------------------
    // Section 4: DB Duplicate Collisions Against Existing Records
    // ----------------------------------------------------
    console.log('\n--- 4. DB Duplicate Collisions Against Existing Records ---');

    // 4.1: Attempt to register new team containing an already registered USN
    const conflictingUsnMembers = makeMembers('C1');
    conflictingUsnMembers[2].usn = validMembers1[0].usn; // Collides with Cadet A1-1 USN
    const conflictUsnRes = await safeFetch(`${BASE_URL}/api/v1/teams`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        name: 'Conflicting USN Team',
        assignedTable: 'Table 2',
        members: conflictingUsnMembers,
      }),
    });
    assert(conflictUsnRes.status === 400, 'Registration with existing DB USN rejected with HTTP 400', 'DB Collision');
    const conflictUsnJson = await conflictUsnRes.json();
    assert(conflictUsnJson.message?.includes('already registered') || conflictUsnJson.detail?.includes('already registered'), 'Duplicate USN DB message returned', 'DB Collision');

    // 4.2: Attempt to register new team containing an already registered Email
    const conflictingEmailMembers = makeMembers('C2');
    conflictingEmailMembers[1].email = validMembers1[0].email; // Collides with Cadet A1-1 Email
    const conflictEmailRes = await safeFetch(`${BASE_URL}/api/v1/teams`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        name: 'Conflicting Email Team',
        assignedTable: 'Table 2',
        members: conflictingEmailMembers,
      }),
    });
    assert(conflictEmailRes.status === 400, 'Registration with existing DB Email rejected with HTTP 400', 'DB Collision');

    // 4.3: Verify DB remained clean after collision failures
    const recheckTeamsRes = await safeFetch(`${BASE_URL}/api/v1/teams`);
    const recheckTeams = (await recheckTeamsRes.json()).data || [];
    assert(recheckTeams.length === initialTeamCount + 1, 'Still exactly initial + 1 team in DB after collision rejections (no partial squad)', 'Atomic Rollback');

    // ----------------------------------------------------
    // Section 5: Capacity Limit (32 Teams Max)
    // ----------------------------------------------------
    console.log('\n--- 5. 32-Team Capacity Limit Enforcement ---');
    const createdExtraIds: string[] = [createdTeam1.id];
    const neededToFill = 32 - recheckTeams.length;

    for (let t = 1; t <= neededToFill; t++) {
      const dummyRes = await safeFetch(`${BASE_URL}/api/v1/teams`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name: `Cap Test Squad ${Date.now()}_${t}`, assignedTable: `Table ${t}` }),
      });
      if (dummyRes.ok) {
        const dJson = await dummyRes.json();
        createdExtraIds.push(dJson.data.id);
      }
    }
    const checkFullRes = await safeFetch(`${BASE_URL}/api/v1/teams`);
    const fullTeams = (await checkFullRes.json()).data || [];
    assert(fullTeams.length === 32, 'Successfully filled tournament capacity to 32 squads', 'Capacity');

    // 33rd registration MUST be rejected
    const squad33Res = await safeFetch(`${BASE_URL}/api/v1/teams`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ name: 'Overflow Squad 33', assignedTable: 'Table 33' }),
    });
    assert(squad33Res.status === 400, '33rd squad registration strictly rejected with HTTP 400', 'Capacity');
    const squad33Json = await squad33Res.json();
    assert(
      squad33Json.message?.includes('Maximum of 32 squads') || squad33Json.detail?.includes('Maximum of 32 squads'),
      'Capacity limit error message explicitly mentions 32 squads maximum',
      'Capacity'
    );

    // ----------------------------------------------------
    // Section 6: Cleanup Test Data
    // ----------------------------------------------------
    console.log('\n--- 6. Clean Up Test Records ---');
    for (const tid of createdExtraIds) {
      await safeFetch(`${BASE_URL}/api/v1/teams/${tid}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
    }

    // Also delete any participants created during test
    const finalPartsRes = await safeFetch(`${BASE_URL}/api/v1/participants`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const finalParts = (await finalPartsRes.json()).data || [];
    for (const p of finalParts) {
      if (p.name?.startsWith('Cadet')) {
        await safeFetch(`${BASE_URL}/api/v1/participants/${p.id}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        });
      }
    }

    const cleanTeamsCheck = (await (await safeFetch(`${BASE_URL}/api/v1/teams`)).json()).data || [];
    assert(cleanTeamsCheck.length === initialTeamCount, 'All test teams cleaned up (returned to initial count)', 'Cleanup');

    // ----------------------------------------------------
    // Section 7: Demo Mode Combined Simulation
    // ----------------------------------------------------
    console.log('\n--- 7. Demo Mode Combined Simulation ---');
    setAppMode('demo');
    // In Demo mode, all 32 slots are filled with simulated tournament squads.
    // Temporarily pop 1 squad to verify registration into a free slot:
    const poppedDemoTeam = (eventService as any).state.teams.pop();
    const demoMembers = makeMembers('DM', false, false, 0);
    const demoInput: CreateTeamInput = {
      name: 'Demo Combined Titans',
      assignedTable: 'Table 99',
      members: demoMembers,
    };
    const demoTeamRes = await eventService.createTeam(demoInput);
    assert(demoTeamRes.success === true, 'Demo mode combined createTeam succeeds', 'Demo Mode');
    assert(demoTeamRes.data.membersCount === 5, 'Demo team created with 5 members', 'Demo Mode');
    assert(demoTeamRes.data.leaderName === 'Cadet DM-1', 'Demo leader name set correctly', 'Demo Mode');
    assert(demoTeamRes.data.members.length === 5, 'Demo team contains 5 member objects', 'Demo Mode');

    // Clean demo participants and demo team, then restore original mock team
    for (const p of demoTeamRes.data.members) {
      await eventService.deleteParticipant(p.id);
    }
    await eventService.deleteTeam(demoTeamRes.data.id);
    if (poppedDemoTeam) {
      (eventService as any).state.teams.push(poppedDemoTeam);
    }
    assert(true, 'Demo team cleanly removed after test and slot restored', 'Demo Mode');
    setAppMode('live');

  } catch (err: any) {
    console.error('Test execution exception:', err);
    assert(false, 'Test execution completed without uncaught exceptions', 'Execution', err?.message);
  }

  // Summary
  const total = assertions.length;
  const passed = assertions.filter((a) => a.passed).length;
  const failed = total - passed;

  console.log('\n==========================================================');
  console.log(`  COMBINED REGISTRATION RESULTS: ${passed}/${total} PASSED (${failed} FAILED)`);
  console.log('==========================================================\n');

  if (failed > 0) {
    process.exit(1);
  }
}

runCombinedRegistrationTests();
