const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const sessionKey = 'asymptotes_live_session';

const retryDelaysMs = [0, 1000, 2000, 4000, 6000];

function delay(ms: number) {
  return new Promise(resolve => window.setTimeout(resolve, ms));
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
export type Session = { token: string; role: Role; displayName: string };
export type LoginResult = Session | { redirect: 'instagram'; message: string };

export function getSession(): Session | null {
  try {
    const raw = localStorage.getItem(sessionKey);
    return raw ? JSON.parse(raw) as Session : null;
  } catch { return null; }
}

export function clearSession() { localStorage.removeItem(sessionKey); }

export async function request<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const session = getSession();
  // Round 1 calls use short paths such as /control/overview. Round 2 calls
  // already include their /r2 namespace and must not be nested below /r1.
  const apiPath = path.startsWith('/r2/') || path.startsWith('/r3-live/') ? `/api/v1${path}` : `/api/v1/r1${path}`;
  const response = await fetchWithRecovery(`${apiBase}${apiPath}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(session ? { Authorization: `Bearer ${session.token}` } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  }, method === 'GET');
  const json = await response.json().catch(() => null);
  if (!response.ok || !json?.success) throw new Error(json?.message || 'Something went wrong.');
  return json.data as T;
}

export async function signIn(loginId: string, password: string): Promise<LoginResult> {
  const response = await fetchWithRecovery(`${apiBase}/api/v1/r1/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ login_id: loginId, password }),
  // Never automatically replay a password POST. During a venue-wide login
  // burst the first request can still be completing after the browser aborts;
  // retries amplify CPU load and can consume duplicate team-device sessions.
  // A longer single attempt gives the server's bounded verifier time to finish.
  }, false, 90_000);
  const json = await response.json().catch(() => null);
  if (!response.ok || !json?.success) throw new Error(json?.message || 'Incorrect ID or password.');
  if (json.data.redirect === 'instagram') return { redirect: 'instagram', message: json.message || 'Round 1 has ended for this team.' };
  const session: Session = { token: json.data.token, role: json.data.role, displayName: json.data.display_name };
  localStorage.setItem(sessionKey, JSON.stringify(session));
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
