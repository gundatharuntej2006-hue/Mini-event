import { AlertCircle, ShieldAlert, X, Radio, WifiOff, Loader2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import { cn } from '../../utils/cn';
import {
  isLiveMode,
  onAppModeChange,
  API_CONFIG,
  getConnectionState,
  getBackendHealth,
  onConnectionStateChange,
  ConnectionState,
  BackendHealthInfo,
} from '../../services/apiConfig';
import { authService } from '../../services/authService';
import { User } from '../../types';

interface DemoBannerProps {
  className?: string;
}

export function DemoModeBanner({ className }: DemoBannerProps) {
  const [dismissed, setDismissed] = useState(false);
  const [liveMode, setLiveMode] = useState(isLiveMode());
  const [currentUser, setCurrentUser] = useState<User | null>(authService.getCurrentUser());
  const [connectionState, setConnectionState] = useState<ConnectionState>(getConnectionState());
  const [serverHealth, setServerHealth] = useState<BackendHealthInfo>(getBackendHealth());

  useEffect(() => {
    const unsubAuth = authService.subscribe((u) => setCurrentUser(u));
    const unsubMode = onAppModeChange((m) => {
      setLiveMode(m === 'live');
      setDismissed(false); // reset dismissal when mode explicitly toggles
    });
    const unsubConn = onConnectionStateChange((state, health) => {
      setConnectionState(state);
      setServerHealth(health);
      if (state === 'offline') {
        setDismissed(false); // never hide offline critical status
      }
    });

    return () => {
      unsubAuth();
      unsubMode();
      unsubConn();
    };
  }, []);

  if (dismissed) return null;

  // 1. In Demo Mode: Show amber simulation notice
  if (!liveMode) {
    return (
      <div
        className={cn(
          'bg-amber-950/40 border border-amber-500/40 text-amber-200 px-4 py-2.5 rounded-xl flex items-center justify-between text-xs backdrop-blur-md transition-all shadow-[0_0_15px_rgba(245,158,11,0.15)]',
          className
        )}
      >
        <div className="flex items-center gap-2.5">
          <div className="p-1 rounded-md bg-amber-500/20 text-amber-400 flex-shrink-0">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold font-mono tracking-wide uppercase text-[11px] bg-amber-500/30 text-amber-200 px-1.5 py-0.5 rounded mr-2 border border-amber-500/40">
              Demo Mode Active
            </span>
            <span className="text-amber-300">
              Simulated demonstration dataset active. Operations and mutations are stored in local browser state and will not affect the production database.
            </span>
          </div>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-amber-400 hover:text-amber-200 p-1 rounded-md hover:bg-amber-500/20 transition-colors ml-3 cursor-pointer"
          title="Dismiss banner"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  // 2. In Live Mode - FastAPI Service Offline: Show prominent Rose Warning
  if (connectionState === 'offline' || (!serverHealth.online && connectionState !== 'checking')) {
    return (
      <div
        className={cn(
          'bg-rose-950/40 border border-rose-500/50 text-rose-200 px-4 py-2.5 rounded-xl flex items-center justify-between text-xs backdrop-blur-md transition-all shadow-[0_0_15px_rgba(244,63,94,0.15)]',
          className
        )}
      >
        <div className="flex items-center gap-2.5">
          <div className="p-1 rounded-md bg-rose-500/20 text-rose-400 flex-shrink-0">
            <WifiOff className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold font-mono tracking-wide uppercase text-[11px] bg-rose-500/30 text-rose-200 px-1.5 py-0.5 rounded mr-2 border border-rose-500/40">
              FastAPI Offline
            </span>
            <span className="text-rose-300">
              Unable to connect to backend service at {API_CONFIG.baseUrl}. Live database operations and scoring updates are suspended until the API gateway is online.
            </span>
          </div>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-rose-400 hover:text-rose-200 p-1 rounded-md hover:bg-rose-500/20 transition-colors ml-3 cursor-pointer"
          title="Dismiss banner"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  // 3. In Live Mode - Probing / Connecting: Show Connecting Status
  if (connectionState === 'checking') {
    return (
      <div
        className={cn(
          'bg-cyan-950/30 border border-cyan-500/30 text-cyan-200 px-4 py-2 rounded-xl flex items-center justify-between text-xs backdrop-blur-md transition-all',
          className
        )}
      >
        <div className="flex items-center gap-2.5">
          <div className="p-1 rounded-md bg-cyan-500/20 text-cyan-400 flex-shrink-0">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          </div>
          <div>
            <span className="font-bold font-mono tracking-wide uppercase text-[11px] bg-cyan-500/20 text-cyan-300 px-1.5 py-0.5 rounded mr-2 border border-cyan-500/30">
              Connecting
            </span>
            <span className="text-cyan-300/90 font-mono text-[11px]">
              Probing FastAPI gateway at {API_CONFIG.baseUrl}...
            </span>
          </div>
        </div>
      </div>
    );
  }

  // 4. In Live Mode - Session Expired: Show Notice to re-authenticate
  if (connectionState === 'token_expired') {
    return (
      <div
        className={cn(
          'bg-amber-950/40 border border-amber-500/50 text-amber-200 px-4 py-2.5 rounded-xl flex items-center justify-between text-xs backdrop-blur-md transition-all shadow-[0_0_15px_rgba(245,158,11,0.15)]',
          className
        )}
      >
        <div className="flex items-center gap-2.5">
          <div className="p-1 rounded-md bg-amber-500/20 text-amber-400 flex-shrink-0">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold font-mono tracking-wide uppercase text-[11px] bg-amber-500/30 text-amber-200 px-1.5 py-0.5 rounded mr-2 border border-amber-500/40">
              Session Expired
            </span>
            <span className="text-amber-300">
              Your staff authorization token has expired. Please sign in again from the profile menu to record live scores.
            </span>
          </div>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-amber-400 hover:text-amber-200 p-1 rounded-md hover:bg-amber-500/20 transition-colors ml-3 cursor-pointer"
          title="Dismiss banner"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  // 5. In Live Mode - Public Projector / Viewer: Show informative cyan banner
  if (currentUser?.role === 'PUBLIC_PROJECTOR' || !currentUser || connectionState === 'connected_public' || connectionState === 'unauthenticated') {
    return (
      <div
        className={cn(
          'bg-cyan-950/40 border border-cyan-500/40 text-cyan-100 px-4 py-2.5 rounded-xl flex items-center justify-between text-xs backdrop-blur-md transition-all shadow-[0_0_15px_rgba(6,182,212,0.15)]',
          className
        )}
      >
        <div className="flex items-center gap-2.5">
          <div className="p-1 rounded-md bg-cyan-500/20 text-cyan-400 flex-shrink-0">
            <Radio className="w-4 h-4 text-cyan-400 animate-pulse" />
          </div>
          <div>
            <span className="font-bold font-mono tracking-wide uppercase text-[11px] bg-cyan-500/30 text-cyan-200 px-1.5 py-0.5 rounded mr-2 border border-cyan-400/40">
              Live API · Public Projector
            </span>
            <span className="text-cyan-200/90">
              Connected to live FastAPI backend at {API_CONFIG.baseUrl}. Read-only spectator telemetry active.
            </span>
          </div>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-cyan-400 hover:text-cyan-200 p-1 rounded-md hover:bg-cyan-500/20 transition-colors ml-3 cursor-pointer"
          title="Dismiss banner"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  // 6. If Authenticated Staff (Organizer, Marshal, Judge): Keep layout clean without warning banners
  return null;
}

interface AlertBoxProps {
  title: string;
  message: string;
  variant?: 'info' | 'warning' | 'danger';
}

export function AlertBox({ title, message, variant = 'info' }: AlertBoxProps) {
  const styles = {
    info: 'bg-blue-50 border-blue-200 text-blue-900',
    warning: 'bg-amber-50 border-amber-200 text-amber-900',
    danger: 'bg-rose-50 border-rose-200 text-rose-900',
  };

  return (
    <div className={cn('p-4 rounded-xl border flex items-start gap-3 text-xs', styles[variant])}>
      <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
      <div>
        <div className="font-semibold">{title}</div>
        <div className="mt-0.5 opacity-90">{message}</div>
      </div>
    </div>
  );
}
