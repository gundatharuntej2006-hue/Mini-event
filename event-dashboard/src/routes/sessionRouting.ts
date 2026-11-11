import type { Role, Session } from '../live/eventApi';

type Access = { experience: 'axiom' | 'event'; roles: Role[] };

export function accessForPath(path: string): Access | null {
  if (path === '/axiom') return { experience: 'axiom', roles: ['PARTICIPANT'] };
  if (path === '/axiom/control') return { experience: 'axiom', roles: ['SUPER_ADMIN'] };
  if (path === '/play' || /^\/scan\/[^/]+$/.test(path) || path === '/round3/play')
    return { experience: 'event', roles: ['PARTICIPANT'] };
  if (path === '/station' || path === '/round2/station' || path === '/round3/station')
    return { experience: 'event', roles: ['ADMIN'] };
  if (path === '/control' || path === '/accounts' || path === '/round2/control' || path === '/round3/control' || path === '/round3/demo')
    return { experience: 'event', roles: ['SUPER_ADMIN'] };
  return null;
}

export function homeForSession(session: Session): string {
  if (session.experience === 'axiom') return session.role === 'SUPER_ADMIN' ? '/axiom/control' : '/axiom';
  return session.role === 'PARTICIPANT' ? '/play' : session.role === 'ADMIN' ? '/station' : '/control';
}

export function canAccess(session: Session, path: string): boolean {
  const access = accessForPath(path);
  return Boolean(access && access.experience === session.experience && access.roles.includes(session.role));
}

export function destinationForSession(session: Session, requested: string | null): string {
  if (requested && requested.startsWith('/') && !requested.startsWith('//') && !requested.includes('\\')) {
    try {
      const url = new URL(requested, window.location.origin);
      if (url.origin === window.location.origin && canAccess(session, url.pathname))
        return `${url.pathname}${url.search}${url.hash}`;
    } catch { /* Ignore malformed callback URLs. */ }
  }
  return homeForSession(session);
}
