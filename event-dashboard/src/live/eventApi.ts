const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const sessionKey = 'asymptotes_live_session';

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
  const response = await fetch(`${apiBase}/api/v1/r1${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(session ? { Authorization: `Bearer ${session.token}` } : {}),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const json = await response.json().catch(() => null);
  if (!response.ok || !json?.success) throw new Error(json?.message || 'Something went wrong.');
  return json.data as T;
}

export async function signIn(loginId: string, password: string): Promise<LoginResult> {
  const response = await fetch(`${apiBase}/api/v1/r1/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ login_id: loginId, password }),
  });
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
