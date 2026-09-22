/**
 * EVENT HQ — Google Forms & External Registration End-to-End Test Suite
 */

export {};

const BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8001';

interface TestAssertion {
  name: string;
  passed: boolean;
  error?: string;
  suite: string;
}

const assertions: TestAssertion[] = [];

function assert(condition: boolean, name: string, suite: string, error?: string) {
  assertions.push({ name, passed: condition, error, suite });
  if (condition) {
    console.log(`  PASS: [${suite}] ${name}`);
  } else {
    console.error(`  FAIL: [${suite}] ${name} — ${error || 'Assertion failed'}`);
  }
}

async function safeFetch(url: string, options: RequestInit = {}): Promise<Response> {
  return fetch(url, options);
}

async function runE2ETest() {
  console.log('==========================================================');
  console.log('  EVENT HQ — GOOGLE FORMS & EXTERNAL REGISTRATION E2E TEST');
  console.log('==========================================================\n');

  let organizerToken = '';
  let webhookSecret = '';
  let createdTestTeamIds: string[] = [];

  try {
    // 1. Authenticate as Organizer
    console.log('--- 1. Authenticating as Organizer ---');
    const loginRes = await safeFetch(`${BASE_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'gundatharuntej2006@gmail.com',
        password: 'Tejaa@2006',
      }),
    });
    assert(loginRes.ok, 'Organizer login succeeds', 'Auth');
    const loginJson = await loginRes.json();
    organizerToken = loginJson.data?.accessToken || loginJson.data?.access_token || loginJson.data?.token || '';
    assert(!!organizerToken, 'Received valid JWT Bearer token', 'Auth');

    // 2. Fetch Integration Settings & Webhook Secret
    console.log('\n--- 2. Integration Settings & Security ---');
    const settingsRes = await safeFetch(`${BASE_URL}/api/v1/integrations/settings`, {
      headers: { Authorization: `Bearer ${organizerToken}` },
    });
    assert(settingsRes.ok, 'GET /integrations/settings succeeds', 'Security');
    const settingsJson = await settingsRes.json();
    webhookSecret = settingsJson.data?.webhook_secret || '';
    assert(!!webhookSecret, 'Retrieved active webhook secret from settings', 'Security');
    assert(
      settingsJson.data?.registration_auto_approve === false,
      'Manual Review is active by default (registration_auto_approve is False)',
      'Security'
    );

    // 3. Webhook Security Verification
    console.log('\n--- 3. Webhook Secret Enforcement ---');
    const unauthRes = await safeFetch(`${BASE_URL}/api/v1/integrations/google-forms/webhook`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_name: 'Hacker Squad' }),
    });
    assert(unauthRes.status === 401, 'Request without X-Webhook-Secret returns HTTP 401', 'Webhook Security');

    const wrongSecretRes = await safeFetch(`${BASE_URL}/api/v1/integrations/google-forms/webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Webhook-Secret': 'invalid_secret_token_123',
      },
      body: JSON.stringify({ team_name: 'Hacker Squad' }),
    });
    assert(wrongSecretRes.status === 401, 'Request with incorrect secret returns HTTP 401', 'Webhook Security');

    // 4. Google Form Submission in Manual Review Mode
    console.log('\n--- 4. Google Form Submission & Manual Review Queue ---');
    const initialTeamsRes = await safeFetch(`${BASE_URL}/api/v1/teams`);
    const initialTeamsJson = await initialTeamsRes.json();
    const initialTeamCount = (initialTeamsJson.data || []).length;

    const testSubmissionPayload = {
      submission_id: 'gform_e2e_test_001',
      team_name: 'E2E Apex Cyber',
      leader: {
        name: 'Apex Leader',
        usn: '1BY23CS901',
        email: 'apex901@bmsit.in',
        phone: '9876543210',
      },
      members: [
        { name: 'Apex Cadet 2', usn: '1BY23CS902', email: 'apex902@bmsit.in', phone: '9876543211' },
        { name: 'Apex Cadet 3', usn: '1BY23CS903', email: 'apex903@bmsit.in', phone: '9876543212' },
        { name: 'Apex Cadet 4', usn: '1BY23CS904', email: 'apex904@bmsit.in', phone: '9876543213' },
        { name: 'Apex Cadet 5', usn: '1BY23CS905', email: 'apex905@bmsit.in', phone: '9876543214' },
      ],
      consent_given: true,
      source: 'google_forms',
    };

    const webhookRes = await safeFetch(`${BASE_URL}/api/v1/integrations/google-forms/webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Webhook-Secret': webhookSecret,
      },
      body: JSON.stringify(testSubmissionPayload),
    });
    assert(webhookRes.ok, 'Valid Google Form webhook submission succeeds', 'Submission');
    const webhookJson = await webhookRes.json();
    const submissionData = webhookJson.data;

    assert(submissionData.status === 'PENDING', 'Submission status is PENDING (not auto-approved)', 'Submission');
    assert(submissionData.created_team_id === null, 'No team ID assigned while PENDING', 'Submission');
    assert(submissionData.members_count === 5, 'Records exactly 5 squad members', 'Submission');

    // Confirm team count did NOT change
    const afterSubmitTeamsRes = await safeFetch(`${BASE_URL}/api/v1/teams`);
    const afterSubmitTeamsJson = await afterSubmitTeamsRes.json();
    assert(
      (afterSubmitTeamsJson.data || []).length === initialTeamCount,
      'Live tournament roster unchanged while submission is PENDING',
      'Submission'
    );

    // 5. Idempotency Test
    console.log('\n--- 5. Webhook Idempotency ---');
    const resubmitRes = await safeFetch(`${BASE_URL}/api/v1/integrations/google-forms/webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Webhook-Secret': webhookSecret,
      },
      body: JSON.stringify(testSubmissionPayload),
    });
    assert(resubmitRes.ok, 'Resubmitting same submission ID succeeds', 'Idempotency');
    const resubmitJson = await resubmitRes.json();
    assert(resubmitJson.data.id === submissionData.id, 'Returns existing submission record idempotently', 'Idempotency');

    // 6. Organizer Review & Explicit Approval
    console.log('\n--- 6. Organizer Explicit Approval ---');
    const approveRes = await safeFetch(
      `${BASE_URL}/api/v1/integrations/submissions/${submissionData.id}/action`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${organizerToken}`,
        },
        body: JSON.stringify({ action: 'approve' }),
      }
    );
    assert(approveRes.ok, 'Organizer approve action succeeds', 'Approval');
    const approveJson = await approveRes.json();
    assert(approveJson.data.status === 'ACCEPTED', 'Submission status transitions to ACCEPTED', 'Approval');
    assert(!!approveJson.data.created_team_id, 'Created team ID is assigned', 'Approval');

    const createdTeamId = approveJson.data.created_team_id;
    createdTestTeamIds.push(createdTeamId);

    // Verify team and participants exist in live roster
    const finalTeamsRes = await safeFetch(`${BASE_URL}/api/v1/teams`);
    const finalTeamsJson = await finalTeamsRes.json();
    assert(
      (finalTeamsJson.data || []).length === initialTeamCount + 1,
      'Live teams count increased by 1 after approval',
      'Approval'
    );

    const createdTeam = (finalTeamsJson.data || []).find((t: any) => t.id === createdTeamId);
    assert(createdTeam?.name === 'E2E Apex Cyber', 'Created team name matches submission', 'Approval');
    assert(createdTeam?.membersCount === 5, 'Created team reports 5/5 members', 'Approval');

    // 7. Public Web Registration Endpoint
    console.log('\n--- 7. Public Web Registration Portal ---');
    const publicPayload = {
      team_name: 'E2E Web Titans',
      leader: {
        name: 'Web Leader',
        usn: '1BY23CS911',
        email: 'weblead911@bmsit.in',
        phone: '9876543220',
      },
      members: [
        { name: 'Web Cadet 2', usn: '1BY23CS912', email: 'wcadet912@bmsit.in', phone: '9876543221' },
        { name: 'Web Cadet 3', usn: '1BY23CS913', email: 'wcadet913@bmsit.in', phone: '9876543222' },
        { name: 'Web Cadet 4', usn: '1BY23CS914', email: 'wcadet914@bmsit.in', phone: '9876543223' },
        { name: 'Web Cadet 5', usn: '1BY23CS915', email: 'wcadet915@bmsit.in', phone: '9876543224' },
      ],
      consent_given: true,
      source: 'public_web',
    };

    const publicRes = await safeFetch(`${BASE_URL}/api/v1/integrations/registration/public-submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(publicPayload),
    });
    assert(publicRes.ok, 'POST /integrations/registration/public-submit succeeds', 'Public Form');
    const publicJson = await publicRes.json();
    assert(publicJson.data.status === 'PENDING', 'Public web registration queued as PENDING', 'Public Form');
    assert(publicJson.data.source === 'public_web', 'Source recorded as public_web', 'Public Form');

    // 8. Rejection of Invalid Submissions
    console.log('\n--- 8. Validation Rejection Safeguards ---');
    const duplicateUsnPayload = {
      team_name: 'Conflict Squad',
      leader: {
        name: 'Conflict Lead',
        usn: '1BY23CS901', // Collides with already accepted squad!
        email: 'conflict@bmsit.in',
      },
      members: [
        { name: 'C2', usn: '1BY23CS922', email: 'c922@bmsit.in' },
        { name: 'C3', usn: '1BY23CS923', email: 'c923@bmsit.in' },
        { name: 'C4', usn: '1BY23CS924', email: 'c924@bmsit.in' },
        { name: 'C5', usn: '1BY23CS925', email: 'c925@bmsit.in' },
      ],
      consent_given: true,
    };

    const duplicateRes = await safeFetch(`${BASE_URL}/api/v1/integrations/google-forms/webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Webhook-Secret': webhookSecret,
      },
      body: JSON.stringify(duplicateUsnPayload),
    });
    const dupJson = await duplicateRes.json();
    assert(dupJson.data.status === 'REJECTED', 'Collision with existing USN is rejected', 'Validation');
    assert(
      dupJson.data.error_message?.includes('already registered'),
      'Recorded error clarifies duplicate USN registration',
      'Validation'
    );

    // 9. Clean Up Test Squads
    console.log('\n--- 9. Cleanup of Test Records ---');
    for (const tid of createdTestTeamIds) {
      await safeFetch(`${BASE_URL}/api/v1/teams/${tid}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${organizerToken}` },
      });
    }

    const verifyCleanRes = await safeFetch(`${BASE_URL}/api/v1/teams`);
    const verifyCleanJson = await verifyCleanRes.json();
    assert(
      (verifyCleanJson.data || []).length === initialTeamCount,
      'Test squad cleanly removed, database restored to initial state',
      'Cleanup'
    );

  } catch (err: any) {
    console.error('Test execution error:', err);
    assert(false, 'Test suite ran without uncaught exceptions', 'Execution', err?.message);
  }

  const passed = assertions.filter((a) => a.passed).length;
  const total = assertions.length;
  const failed = total - passed;

  console.log('\n==========================================================');
  console.log(`  E2E RESULTS: ${passed}/${total} PASSED (${failed} FAILED)`);
  console.log('==========================================================\n');

  if (failed > 0) {
    process.exit(1);
  }
}

runE2ETest();
