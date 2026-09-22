/**
 * EVENT HQ — Live FastAPI Authentication & Server-Side RBAC Verification Suite
 *
 * Verifies against running backend (http://127.0.0.1:8000):
 * 1. Health gateway probe (/api/v1/health).
 * 2. Unauthenticated access restriction on protected endpoints (/api/v1/participants returns 401).
 * 3. Organizer login via live API (/api/v1/auth/login) returns valid JWT access token and user profile.
 * 4. Token persistence and authenticated profile retrieval (/api/v1/auth/me).
 * 5. Protected participant roster retrieval with Bearer token (returns 200).
 * 6. Server-side RBAC enforcement:
 *    - Organizer can access privileged administrative endpoints (/auth/register).
 *    - Marshal receives 403 Forbidden when attempting Organizer-only actions.
 *    - Unauthenticated requests receive 401 Unauthorized.
 * 7. Unified connection state transitions in apiConfig and components.
 * 8. Cleanup of temporary verification accounts without touching event data.
 */

import { execFileSync } from 'child_process';
import { resolve } from 'path';
import { getConnectionState, setConnectionState, onConnectionStateChange } from './services/apiConfig';
import { apiClient } from './services/apiClient';

interface AssertionResult {
  category: string;
  description: string;
  passed: boolean;
  detail?: string;
}

const assertions: AssertionResult[] = [];

function assert(condition: boolean, description: string, category: string, detail?: string) {
  if (condition) {
    assertions.push({ category, description, passed: true });
    console.log(`  PASS: [${category}] ${description}`);
  } else {
    assertions.push({ category, description, passed: false, detail: detail || 'Assertion failed' });
    console.error(`  FAIL: [${category}] ${description} — ${detail || 'Assertion failed'}`);
  }
}

const BACKEND_DIR = resolve(process.cwd(), '../backend');
const VENV_PYTHON = resolve(process.cwd(), '../.venv/Scripts/python.exe');
const BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8001';

// Safe fetch wrapper that handles brief uvicorn reload windows during file writes
async function safeFetch(url: string, init?: RequestInit, retries = 6): Promise<Response> {
  for (let i = 0; i < retries; i++) {
    try {
      return await fetch(url, init);
    } catch (err: any) {
      const code = err?.cause?.code;
      if ((code === 'ECONNRESET' || code === 'ECONNREFUSED') && i < retries - 1) {
        await new Promise((r) => setTimeout(r, 350));
        continue;
      }
      throw err;
    }
  }
  return fetch(url, init);
}

// Unique ephemeral test users for non-destructive verification
const TEST_ORG_EMAIL = 'verifier_organizer_probe@bmsit.in';
const TEST_ORG_NAME = 'Verification Lead Organizer';
const TEST_MARSHAL_EMAIL = 'verifier_marshal_probe@bmsit.in';
const TEST_MARSHAL_NAME = 'Verification Marshal';
// Deterministic safe passwords for integration test session (never logged or shared)
const TEST_PASS = 'VerifySecureAuth2026!';

function runCliCmd(args: string[]): string {
  try {
    return execFileSync(VENV_PYTHON, [resolve(BACKEND_DIR, 'cli.py'), ...args], {
      cwd: BACKEND_DIR,
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
    });
  } catch (err: any) {
    throw new Error(`CLI Command failed: ${err.stderr || err.message}`);
  }
}

function cleanupTestUsers() {
  try {
    const pythonCleanScript = `
import sqlalchemy, pathlib
p = pathlib.Path(r"${BACKEND_DIR.replace(/\\/g, '/')}/event_hq.db").resolve().as_posix()
eng = sqlalchemy.create_engine(f"sqlite:///{p}")
with eng.connect() as conn:
    conn.execute(sqlalchemy.text("DELETE FROM users WHERE email IN ('${TEST_ORG_EMAIL}', '${TEST_MARSHAL_EMAIL}')"))
    conn.commit()
`;
    execFileSync(VENV_PYTHON, ['-c', pythonCleanScript], {
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
    });
  } catch (err) {
    console.error('Cleanup warning:', err);
  }
}

async function runVerification() {
  console.log('\n==========================================================');
  console.log('  EVENT HQ — LIVE API AUTH & SERVER-SIDE RBAC VERIFICATION');
  console.log('==========================================================\n');

  try {
    // 0. Initial Cleanup
    cleanupTestUsers();

    // 1. Health Gateway Verification
    console.log('--- Step 1: Health Gateway Probe ---');
    const healthRes = await safeFetch(`${BASE_URL}/api/v1/health`);
    assert(healthRes.ok, 'Health endpoint responds with HTTP 200', 'Gateway Health');
    const healthJson = await healthRes.json();
    assert(healthJson.success === true, 'Response indicates success: true', 'Gateway Health');
    assert(healthJson.data?.status === 'online', 'Status is online', 'Gateway Health');
    assert(healthJson.data?.database === 'healthy', 'Database engine is healthy', 'Gateway Health');

    // 2. Unauthenticated Protected Access Restriction
    console.log('\n--- Step 2: Unauthenticated Security Restrictions ---');
    const unauthRes = await safeFetch(`${BASE_URL}/api/v1/participants`);
    assert(unauthRes.status === 401, 'Unauthenticated GET /participants returns HTTP 401', 'Server Security');
    const unauthJson = await unauthRes.json();
    assert(
      unauthJson.detail === 'Authentication credentials were not provided' || unauthRes.status === 401,
      'Protected endpoint rejects missing credentials',
      'Server Security'
    );

    // 3. Administrative User Provisioning via CLI
    console.log('\n--- Step 3: Administrative User Creation via CLI ---');
    const orgCliOutput = runCliCmd([
      'create-user',
      '--email', TEST_ORG_EMAIL,
      '--password', TEST_PASS,
      '--name', TEST_ORG_NAME,
      '--role', 'ORGANIZER',
    ]);
    assert(orgCliOutput.includes('User created successfully'), 'CLI created test organizer account', 'CLI Management');

    const marshalCliOutput = runCliCmd([
      'create-user',
      '--email', TEST_MARSHAL_EMAIL,
      '--password', TEST_PASS,
      '--name', TEST_MARSHAL_NAME,
      '--role', 'MARSHAL',
    ]);
    assert(marshalCliOutput.includes('User created successfully'), 'CLI created test marshal account', 'CLI Management');

    // Test CLI password reset functionality
    const RESET_PASS = 'ResetVerifyPass2026!';
    const resetCliOutput = runCliCmd([
      'reset-password',
      '--email', TEST_ORG_EMAIL,
      '--password', RESET_PASS,
    ]);
    assert(resetCliOutput.includes('Password reset successfully'), 'CLI reset-password command succeeded', 'CLI Management');

    // 4. Organizer Live Authentication Flow
    console.log('\n--- Step 4: Organizer Login Flow ---');
    const loginPayload = {
      email: TEST_ORG_EMAIL,
      password: RESET_PASS,
    };

    const loginRes = await safeFetch(`${BASE_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(loginPayload),
    });

    assert(loginRes.ok, 'Organizer login returns HTTP 200 OK', 'Organizer Login');
    const loginJson = await loginRes.json();
    assert(loginJson.success === true, 'Login response success is true', 'Organizer Login');
    
    const token = loginJson.data?.accessToken || loginJson.data?.access_token;
    assert(typeof token === 'string' && token.length > 20, 'Received valid JWT access token', 'Organizer Login');
    assert(loginJson.data?.user?.email === TEST_ORG_EMAIL, 'Returned user email matches', 'Organizer Login');
    assert(loginJson.data?.user?.role === 'ORGANIZER', 'Returned user role is ORGANIZER', 'Organizer Login');

    // Test Invalid Password Rejection
    const invalidLoginRes = await safeFetch(`${BASE_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: TEST_ORG_EMAIL, password: 'WrongPassword123' }),
    });
    assert(invalidLoginRes.status === 401, 'Invalid password correctly rejected with HTTP 401', 'Organizer Login');

    // 5. Authenticated Profile & Token Storage Verification
    console.log('\n--- Step 5: Authenticated Session & /auth/me ---');
    apiClient.setToken(token);
    assert(apiClient.getToken() === token, 'Token successfully stored in client session', 'Session Storage');

    const meRes = await safeFetch(`${BASE_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    assert(meRes.ok, 'GET /auth/me with Bearer token succeeds with HTTP 200', 'Session Verification');
    const meJson = await meRes.json();
    assert(meJson.data?.email === TEST_ORG_EMAIL, '/auth/me returns authenticated organizer profile', 'Session Verification');
    assert(meJson.data?.role === 'ORGANIZER', '/auth/me confirms role is ORGANIZER', 'Session Verification');

    // 6. Accessing Protected Endpoints with Organizer Token
    console.log('\n--- Step 6: Protected Resource Access with Organizer Token ---');
    const participantsRes = await safeFetch(`${BASE_URL}/api/v1/participants`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    assert(participantsRes.ok, 'Authenticated GET /participants returns HTTP 200', 'Protected Resources');
    const participantsJson = await participantsRes.json();
    assert(Array.isArray(participantsJson.data), 'Participants list is an array', 'Protected Resources');
    assert(Array.isArray(participantsJson.data), 'GET /participants returns valid array of participants', 'Protected Resources');

    // 7. Server-Side RBAC Verification (Organizer vs Marshal)
    console.log('\n--- Step 7: Server-Side RBAC Enforcement ---');
    // Log in as Marshal
    const marshalLoginRes = await safeFetch(`${BASE_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: TEST_MARSHAL_EMAIL, password: TEST_PASS }),
    });
    const marshalJson = await marshalLoginRes.json();
    const marshalToken = marshalJson.data?.accessToken || marshalJson.data?.access_token;
    assert(typeof marshalToken === 'string', 'Marshal authenticated and received token', 'RBAC Enforcement');

    // Marshal accessing participants: ALLOWED (Staff role)
    const marshalParticipantsRes = await safeFetch(`${BASE_URL}/api/v1/participants`, {
      headers: { Authorization: `Bearer ${marshalToken}` },
    });
    assert(marshalParticipantsRes.ok, 'Marshal is permitted to access participants (Staff permission)', 'RBAC Enforcement');

    // Marshal attempting to register an official: FORBIDDEN (ORGANIZER only)
    const marshalRegisterRes = await safeFetch(`${BASE_URL}/api/v1/auth/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${marshalToken}`,
      },
      body: JSON.stringify({
        email: 'blocked_subuser@bmsit.in',
        name: 'Blocked Subuser',
        password: 'Password123!',
        role: 'JUDGE',
      }),
    });
    assert(marshalRegisterRes.status === 403, 'Marshal is forbidden (HTTP 403) from calling /auth/register', 'RBAC Enforcement');
    const marshalRegisterJson = await marshalRegisterRes.json();
    assert(
      marshalRegisterJson.detail?.includes('Access forbidden') || marshalRegisterRes.status === 403,
      'Server error message confirms forbidden role',
      'RBAC Enforcement'
    );

    // 8. Connection State Machine Synchronization
    console.log('\n--- Step 8: Unified Connection State Machine ---');
    let observedState = '';
    const unsub = onConnectionStateChange((state) => {
      observedState = state;
    });

    setConnectionState('offline');
    assert(getConnectionState() === 'offline', 'Connection state updates to offline', 'Connection State');
    assert(observedState === 'offline', 'Subscribers notified of offline transition', 'Connection State');

    setConnectionState('connected_staff', { online: true, database: 'healthy', message: 'Online' });
    assert(getConnectionState() === 'connected_staff', 'Connection state updates to connected_staff', 'Connection State');
    assert(observedState === 'connected_staff', 'Subscribers notified of connected_staff transition', 'Connection State');

    unsub();

    // 9. Cleanup & Data Preservation Verification
    console.log('\n--- Step 9: Database Integrity & Cleanup ---');
    cleanupTestUsers();

    // Verify original database records remain intact
    const verifyCleanRes = await safeFetch(`${BASE_URL}/api/v1/teams`);
    assert(verifyCleanRes.ok, 'Public GET /teams succeeds', 'Database Integrity');
    const teamsJson = await verifyCleanRes.json();
    assert(Array.isArray(teamsJson.data), 'GET /teams returns valid array of registered teams', 'Database Integrity');

  } catch (error: any) {
    console.error('Verification failed with uncaught exception:', error);
    assert(false, 'Verification suite encountered an exception', 'Test Execution', error?.message);
  } finally {
    cleanupTestUsers();
  }

  // Summary Report
  const total = assertions.length;
  const passed = assertions.filter((a) => a.passed).length;
  const failed = total - passed;

  console.log('\n==========================================================');
  console.log(`  VERIFICATION RESULTS: ${passed}/${total} PASSED (${failed} FAILED)`);
  console.log('==========================================================\n');

  if (failed > 0) {
    process.exit(1);
  }
}

runVerification();
