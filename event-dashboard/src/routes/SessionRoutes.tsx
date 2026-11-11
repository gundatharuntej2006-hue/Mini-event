import { useEffect, useState, useSyncExternalStore } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { ApiRequestError, getSessionToken, subscribeSession, validateSession, type Session } from '../live/eventApi';
import { canAccess, destinationForSession } from './sessionRouting';

type Check =
  | { token: string; status: 'ready'; session: Session | null }
  | { token: string; status: 'error' }
  | { token: string; status: 'event-ended' };

function useSessionCheck() {
  const token = useSyncExternalStore(subscribeSession, getSessionToken, () => null);
  const [check, setCheck] = useState<Check | null>(null);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    if (!token) return;
    let active = true;
    validateSession().then(
      session => { if (active) setCheck({ token, status: 'ready', session }); },
      error => { if (active) setCheck({ token, status: error instanceof ApiRequestError && error.status === 403 && error.message.includes('Round 1 has ended') ? 'event-ended' : 'error' }); },
    );
    return () => { active = false; };
  }, [token, retry]);

  return { token, check: check?.token === token ? check : null, retry: () => { setCheck(null); setRetry(value => value + 1); } };
}

function SessionStatus({ error, retry }: { error: boolean; retry: () => void }) {
  return <main className="route-loading" aria-live="polite">
    {error ? <><p>Could not verify your session. Your sign-in is still saved.</p><button type="button" onClick={retry}>Try again</button></> : <><span />Checking your session…</>}
  </main>;
}

export function ProtectedRoute() {
  const location = useLocation();
  const { token, check, retry } = useSessionCheck();
  const intended = `${location.pathname}${location.search}${location.hash}`;
  if (!token || (check?.status === 'ready' && !check.session))
    return <Navigate to={`/login?next=${encodeURIComponent(intended)}`} replace />;
  if (!check) return <SessionStatus error={false} retry={retry} />;
  if (check.status === 'event-ended') return <Navigate to="/results" replace />;
  if (check.status === 'error') return <SessionStatus error retry={retry} />;
  if (!canAccess(check.session!, location.pathname))
    return <Navigate to={destinationForSession(check.session!, null)} replace />;
  return <Outlet />;
}

export function GuestRoute() {
  const location = useLocation();
  const { token, check, retry } = useSessionCheck();
  if (!token || (check?.status === 'ready' && !check.session)) return <Outlet />;
  if (!check) return <SessionStatus error={false} retry={retry} />;
  if (check.status === 'event-ended') return <Outlet />;
  if (check.status === 'error') return <SessionStatus error retry={retry} />;
  const requested = new URLSearchParams(location.search).get('next');
  return <Navigate to={destinationForSession(check.session!, requested)} replace />;
}
