const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const sessionKey = 'asymptotes_live_session';
const sessionChangedEvent = 'asymptotes_session_changed';

const retryDelaysMs = [0, 1000, 2000, 4000, 6000];
let backendWarmup: Promise<void> | null = null;

function delay(ms: number) {
  return new Promise(resolve => window.setTimeout(resolve, ms));
}

/**
 * Wake Render and open the database connection while the visitor is reading
 * the landing/login screen. This removes the cold-start wait from the moment
 * they press Continue without weakening password hashing or authentication.
 */
export function warmBackend(): Promise<void> {
  if (backendWarmup) return backendWarmup;
  backendWarmup = waitForBackendReady().catch(() => {
    // Warm-up is an optimization. Keep the landing page usable if a probe
    // fails; the sign-in flow will run its own confirmed preflight below.
    backendWarmup = null;
  });
  return backendWarmup;
}

async function waitForBackendReady(): Promise<void> {
  const response = await fetchWithRecovery(`${apiBase}/api/v1/health`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
  }, true, 60_000);
  if (!response.ok) throw new Error(`Warm-up returned ${response.status}.`);
}

/**
 * Render can briefly return a gateway/network error while a new deploy is
 * becoming healthy. Recover transparently for safe requests instead of
 * exposing the browser's unhelpful "Failed to fetch" message to the event.
 */
async function fetchWithRecovery(url: string, init: RequestInit, canRetry: boolean, timeoutMs = 20_000): Promise<Response> {
  const attempts = canRetry ? retryDelaysMs.length : 1;
  let lastError: unknown;

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (retryDelaysMs[attempt]) await delay(retryDelaysMs[attempt]);

    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, { ...init, signal: controller.signal });
      window.clearTimeout(timeoutId);
      if (!canRetry || response.status < 500 || attempt === attempts - 1) return response;
      lastError = new Error(`Event server returned ${response.status}.`);
    } catch (error) {
      window.clearTimeout(timeoutId);
      lastError = error;
      if (!canRetry || attempt === attempts - 1) break;
    }
  }

  throw new Error(
    lastError instanceof DOMException && lastError.name === 'AbortError'
      ? 'The event server took too long to respond. Please tap Enter event again.'
      : 'The event server is reconnecting. Please wait a few seconds and try again.',
  );
}

export type Role = 'SUPER_ADMIN' | 'ADMIN' | 'PARTICIPANT';
export type Session = { token: string; role: Role; displayName: string; experience?: 'axiom' | 'event' };
export type LoginResult = Session | { redirect: 'instagram'; message: string };
type CurrentAccount = { role: Role; display_name: string; experience: 'axiom' | 'event' };
let sessionValidation: { token: string; promise: Promise<Session | null> } | null = null;

export class ApiRequestError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
  }
}

function tokenExpiresAt(token: string): number | null {
  try {
    const payload = token.split('.')[1];
    if (!payload) return null;
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))) as { exp?: unknown };
    return typeof decoded.exp === 'number' && Number.isFinite(decoded.exp) ? decoded.exp * 1000 : null;
  } catch { return null; }
}

export function getSession(): Session | null {
  try {
    const raw = localStorage.getItem(sessionKey);
    if (!raw) return null;
    const session = JSON.parse(raw) as Session;
    const expiresAt = typeof session.token === 'string' ? tokenExpiresAt(session.token) : null;
    // The server decides whether exp has passed. Trusting the device clock
    // here can sign a member out early, and leaves an open page unaware when
    // an expired token is omitted from a later request.
    if (!expiresAt || !['SUPER_ADMIN', 'ADMIN', 'PARTICIPANT'].includes(session.role)) return null;
    return session;
  } catch { return null; }
}

export function getSessionToken(): string | null { return getSession()?.token ?? null; }

export function subscribeSession(listener: () => void): () => void {
  window.addEventListener(sessionChangedEvent, listener);
  window.addEventListener('storage', listener);
  return () => {
    window.removeEventListener(sessionChangedEvent, listener);
    window.removeEventListener('storage', listener);
  };
}

function saveSession(session: Session): void {
  localStorage.setItem(sessionKey, JSON.stringify(session));
  window.dispatchEvent(new Event(sessionChangedEvent));
}

export function clearSession(): void {
  localStorage.removeItem(sessionKey);
  window.dispatchEvent(new Event(sessionChangedEvent));
}

export async function request<T>(path: string, method = 'GET', body?: unknown, options?: { retry?: boolean; timeoutMs?: number }): Promise<T> {
  const session = getSession();
  // Round 1 calls use short paths such as /control/overview. Round 2 calls
  // already include their /r2 namespace and must not be nested below /r1.
  const apiPath = path.startsWith('/r2/') || path.startsWith('/r3-live/') || path.startsWith('/axiom/') ? `/api/v1${path}` : `/api/v1/r1${path}`;
  const response = await fetchWithRecovery(`${apiBase}${apiPath}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(session ? { Authorization: `Bearer ${session.token}` } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  }, options?.retry ?? method === 'GET', options?.timeoutMs ?? 20_000);
  const json = await response.json().catch(() => null);
  // A feature can reject its own device session with 401 while the bearer is
  // still valid. Verify the bearer with /me before ending the global session.
  if (response.status === 401 && session && getSessionToken() === session.token) {
    if (path === '/me') clearSession();
    else void validateSession().catch(() => {});
  }
  if (!response.ok || !json?.success) throw new ApiRequestError(json?.message || 'Something went wrong.', response.status);
  return json.data as T;
}

export function validateSession(): Promise<Session | null> {
  const session = getSession();
  if (!session) return Promise.resolve(null);
  if (sessionValidation?.token === session.token) return sessionValidation.promise;
  const token = session.token;
  const promise = request<CurrentAccount>('/me').then(account => {
    if (getSessionToken() !== token) return getSession();
    const updated: Session = { token, role: account.role, displayName: account.display_name, experience: account.experience };
    saveSession(updated);
    return updated;
  }).catch(error => {
    if (error instanceof ApiRequestError && error.status === 401) return null;
    throw error;
  }).finally(() => {
    if (sessionValidation?.token === token) sessionValidation = null;
  });
  sessionValidation = { token, promise };
  return promise;
}

export async function signIn(loginId: string, password: string): Promise<LoginResult> {
  // Do not race the password request against Render waking or recovering.
  // A health-confirmed API lets the non-replayable login POST stay safe while
  // preventing the user from seeing a timeout during a deployment/cold start.
  if (backendWarmup) await backendWarmup;
  try {
    await waitForBackendReady();
  } catch {
    throw new Error('The workspace server is still starting. Please wait a moment and try again.');
  }
  const response = await fetchWithRecovery(`${apiBase}/api/v1/r1/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ login_id: loginId, password }),
  // Never automatically replay a password POST. During a venue-wide login
  // burst the first request can still be completing after the browser aborts;
  // retries amplify CPU load and can consume duplicate team-device sessions.
  // A longer single attempt gives the server's bounded verifier time to finish.
  }, false, 120_000);
  const json = await response.json().catch(() => null);
  if (!response.ok || !json?.success) throw new Error(json?.message || 'Incorrect ID or password.');
  if (json.data.redirect === 'instagram') return { redirect: 'instagram', message: json.message || 'Round 1 has ended for this team.' };
  const session: Session = { token: json.data.token, role: json.data.role, displayName: json.data.display_name, experience: json.data.experience };
  saveSession(session);
  return session;
}

export async function downloadReportPdf(): Promise<void> {
  const session = getSession();
  const response = await fetch(`${apiBase}/api/v1/r1/control/report.pdf`, {
    headers: session ? { Authorization: `Bearer ${session.token}` } : {},
  });
  if (!response.ok) {
    const json = await response.json().catch(() => null);
    throw new Error(json?.message || 'Could not create the verification PDF.');
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'asymptotes-round1-verification.pdf';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
