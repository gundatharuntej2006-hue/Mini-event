const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const vm = require('node:vm');
const esbuild = require('esbuild');
const fs = require('node:fs');

function loadModule(file, globals) {
  const code = esbuild.buildSync({
    entryPoints: [path.join(__dirname, '..', 'src', file)],
    bundle: true,
    platform: 'node',
    format: 'cjs',
    write: false,
    define: { 'import.meta.env.VITE_API_BASE_URL': '"http://localhost:8000"' },
  }).outputFiles[0].text;
  const module = { exports: {} };
  vm.runInNewContext(code, { ...globals, module, exports: module.exports, URL, atob, Event, DOMException, AbortController, setTimeout, clearTimeout });
  return module.exports;
}

function token(exp) {
  return `${Buffer.from('{}').toString('base64url')}.${Buffer.from(JSON.stringify({ exp })).toString('base64url')}.signature`;
}

function harness(fetch) {
  const values = new Map();
  const listeners = new Map();
  const localStorage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: key => values.delete(key),
  };
  const window = {
    location: { origin: 'http://localhost:5173' },
    setTimeout, clearTimeout,
    addEventListener: (name, listener) => (listeners.get(name) ?? listeners.set(name, new Set()).get(name)).add(listener),
    removeEventListener: (name, listener) => listeners.get(name)?.delete(listener),
    dispatchEvent: event => listeners.get(event.type)?.forEach(listener => listener()),
  };
  const globals = { window, localStorage, fetch };
  return { api: loadModule('live/eventApi.ts', globals), routing: loadModule('routes/sessionRouting.ts', globals), values };
}

function storedSession(h, exp, experience = 'axiom') {
  const session = { token: token(exp), role: 'PARTICIPANT', displayName: 'Local Test', experience };
  h.values.set('asymptotes_live_session', JSON.stringify(session));
  return session;
}

function response(status, data = null) {
  return { status, ok: status >= 200 && status < 300, json: async () => ({ success: status === 200, data, message: status === 401 ? 'Session expired' : 'Forbidden' }) };
}

test('stored sessions survive navigation until the server confirms expiry', async () => {
  const h = harness(async () => response(401));
  const valid = storedSession(h, Math.floor(Date.now() / 1000) + 60);
  assert.equal(h.api.getSession().token, valid.token);
  assert.equal(h.api.getSessionToken(), valid.token);
  const expired = storedSession(h, Math.floor(Date.now() / 1000) - 1);
  assert.equal(h.api.getSession().token, expired.token);
  assert.equal(await h.api.validateSession(), null);
  assert.equal(h.api.getSession(), null);
  h.values.set('asymptotes_live_session', '{bad json');
  assert.equal(h.api.getSession(), null);
});

test('server verification restores authoritative role and experience', async () => {
  let calls = 0;
  const h = harness(async () => {
    calls += 1;
    return response(200, { role: 'PARTICIPANT', display_name: 'Verified Member', experience: 'axiom' });
  });
  storedSession(h, Math.floor(Date.now() / 1000) + 60, 'event');
  const [one, two] = await Promise.all([h.api.validateSession(), h.api.validateSession()]);
  assert.equal(calls, 1);
  assert.equal(one.experience, 'axiom');
  assert.equal(two.displayName, 'Verified Member');
  assert.equal(h.api.getSession().experience, 'axiom');
});

test('only a rejected bearer clears the session; feature 401, 403, and network errors preserve it', async () => {
  let status = 403;
  let bearerStatus = 200;
  const h = harness(async url => status === 0 ? Promise.reject(new Error('offline')) :
    url.endsWith('/r1/me') ? response(bearerStatus, { role: 'PARTICIPANT', display_name: 'Local Test', experience: 'axiom' }) : response(status));
  storedSession(h, Math.floor(Date.now() / 1000) + 60);
  await assert.rejects(h.api.request('/axiom/me', 'POST'));
  assert.ok(h.api.getSession());
  status = 0;
  await assert.rejects(h.api.request('/axiom/me', 'POST'));
  assert.ok(h.api.getSession());
  status = 401;
  await assert.rejects(h.api.request('/axiom/me', 'POST'));
  await h.api.validateSession();
  assert.ok(h.api.getSession());
  bearerStatus = 401;
  await assert.rejects(h.api.request('/axiom/me', 'POST'));
  await h.api.validateSession();
  assert.equal(h.api.getSession(), null);
});

test('an old request cannot clear a newer login session', async () => {
  let finish;
  const h = harness(() => new Promise(resolve => { finish = resolve; }));
  storedSession(h, Math.floor(Date.now() / 1000) + 60);
  const oldRequest = h.api.request('/axiom/me', 'POST');
  const newer = storedSession(h, Math.floor(Date.now() / 1000) + 120);
  finish(response(401));
  await assert.rejects(oldRequest);
  assert.equal(h.api.getSession().token, newer.token);
});

test('callbacks preserve permitted local destinations and reject external or wrong-role URLs', () => {
  const h = harness(async () => response(200));
  const session = storedSession(h, Math.floor(Date.now() / 1000) + 60);
  assert.equal(h.routing.destinationForSession(session, '/axiom?pane=projects#stage1'), '/axiom?pane=projects#stage1');
  assert.equal(h.routing.destinationForSession(session, 'https://example.com'), '/axiom');
  assert.equal(h.routing.destinationForSession(session, '//example.com'), '/axiom');
  assert.equal(h.routing.destinationForSession(session, '/control'), '/axiom');
  assert.equal(h.routing.destinationForSession(session, '/login'), '/axiom');
});

test('every protected screen has a policy and role or experience mismatches cannot enter it', () => {
  const h = harness(async () => response(200));
  const routes = fs.readFileSync(path.join(__dirname, '..', 'src', 'routes', 'index.tsx'), 'utf8');
  const protectedRoutes = routes.split('<Route element={<ProtectedRoute />}>')[1].split('</Route>')[0];
  const paths = [...protectedRoutes.matchAll(/<Route path="([^"]+)"/g)].map(match => match[1].replace(':location', '1'));
  assert.ok(paths.length >= 13);
  for (const route of paths) assert.ok(h.routing.accessForPath(route), `Missing policy for ${route}`);
  const axiom = { token: 'test', role: 'PARTICIPANT', experience: 'axiom' };
  const event = { token: 'test', role: 'PARTICIPANT', experience: 'event' };
  assert.equal(h.routing.canAccess(axiom, '/axiom'), true);
  assert.equal(h.routing.canAccess(axiom, '/play'), false);
  assert.equal(h.routing.canAccess(event, '/play'), true);
  assert.equal(h.routing.canAccess(event, '/axiom'), false);
  assert.equal(h.routing.canAccess({ ...event, role: 'ADMIN' }, '/round2/station'), true);
  assert.equal(h.routing.canAccess({ ...event, role: 'ADMIN' }, '/round2/control'), false);
  assert.equal(h.routing.canAccess({ ...event, role: 'SUPER_ADMIN' }, '/round3/control'), true);
});
