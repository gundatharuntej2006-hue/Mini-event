/**
 * Centralized API and environment configuration.
 * Connects the frontend to the FastAPI backend while preserving local demo capabilities.
 */

const env = (typeof import.meta !== 'undefined' && import.meta.env) 
  ? import.meta.env 
  : (typeof process !== 'undefined' ? process.env : {}) as Record<string, string | undefined>;

const APP_MODE_KEY = 'event_hq_app_mode';
let inMemoryAppMode: 'live' | 'demo' | null = null;
const modeListeners = new Set<(mode: 'live' | 'demo') => void>();

function getInitialAppMode(): 'live' | 'demo' {
  if (inMemoryAppMode) {
    return inMemoryAppMode;
  }
  if (typeof window !== 'undefined' && window.localStorage) {
    const stored = window.localStorage.getItem(APP_MODE_KEY);
    if (stored === 'live' || stored === 'demo') {
      return stored;
    }
  }
  // If explicitly configured via env
  if (env.VITE_ENABLE_MOCK_DATA === 'true' || env.VITE_APP_MODE === 'demo') {
    return 'demo';
  }
  if (env.VITE_ENABLE_MOCK_DATA === 'false' || env.VITE_APP_MODE === 'live') {
    return 'live';
  }
  return 'live'; // Default to live API mode for seamless backend connection
}

export const API_CONFIG = {
  baseUrl: env.VITE_API_BASE_URL || 'http://127.0.0.1:8001',
  apiPrefix: '/api/v1',
  eventName: env.VITE_EVENT_NAME || 'EVENT HQ · BMSIT 2026',
  get isMockEnabled(): boolean {
    return getInitialAppMode() === 'demo';
  },
  timeoutMs: 15000,
};

export function getAppMode(): 'live' | 'demo' {
  return getInitialAppMode();
}

export type ConnectionState =
  | 'demo'
  | 'checking'
  | 'unauthenticated'
  | 'connected_staff'
  | 'connected_public'
  | 'token_expired'
  | 'offline';

export interface BackendHealthInfo {
  online: boolean;
  database: string;
  message: string;
}

let currentConnectionState: ConnectionState = getInitialAppMode() === 'demo' ? 'demo' : 'checking';
let currentBackendHealth: BackendHealthInfo = {
  online: false,
  database: 'unknown',
  message: getInitialAppMode() === 'demo' ? 'Local browser demo simulation active' : 'Probing FastAPI gateway...',
};

const connectionListeners = new Set<(state: ConnectionState, health: BackendHealthInfo) => void>();

export function getConnectionState(): ConnectionState {
  return currentConnectionState;
}

export function getBackendHealth(): BackendHealthInfo {
  return currentBackendHealth;
}

export function setConnectionState(state: ConnectionState, health?: Partial<BackendHealthInfo>): void {
  currentConnectionState = state;
  if (health) {
    currentBackendHealth = { ...currentBackendHealth, ...health };
  }
  if (typeof window !== 'undefined') {
    window.dispatchEvent(
      new CustomEvent('connection_state_change', {
        detail: { state: currentConnectionState, health: currentBackendHealth },
      })
    );
  }
  connectionListeners.forEach((listener) => {
    try {
      listener(currentConnectionState, currentBackendHealth);
    } catch (e) {
      console.error('Error in connection listener:', e);
    }
  });
}

export function onConnectionStateChange(
  listener: (state: ConnectionState, health: BackendHealthInfo) => void
): () => void {
  connectionListeners.add(listener);
  try {
    listener(currentConnectionState, currentBackendHealth);
  } catch (e) {
    console.error('Error in initial connection listener:', e);
  }

  let removeBrowserHandler: (() => void) | null = null;
  if (typeof window !== 'undefined') {
    const handler = (e: Event) => {
      const customEvt = e as CustomEvent<{ state: ConnectionState; health: BackendHealthInfo }>;
      if (customEvt.detail) {
        listener(customEvt.detail.state, customEvt.detail.health);
      }
    };
    window.addEventListener('connection_state_change', handler);
    removeBrowserHandler = () => window.removeEventListener('connection_state_change', handler);
  }

  return () => {
    connectionListeners.delete(listener);
    if (removeBrowserHandler) removeBrowserHandler();
  };
}

export function setAppMode(mode: 'live' | 'demo'): void {
  inMemoryAppMode = mode;
  if (typeof window !== 'undefined' && window.localStorage) {
    window.localStorage.setItem(APP_MODE_KEY, mode);
    window.dispatchEvent(new CustomEvent('app_mode_change', { detail: mode }));
  }
  if (mode === 'demo') {
    setConnectionState('demo', {
      online: false,
      database: 'demo-local-storage',
      message: 'Local browser demo simulation active. No live API connection.',
    });
  } else {
    setConnectionState('checking', {
      online: false,
      database: 'unknown',
      message: 'Probing FastAPI gateway...',
    });
  }
  modeListeners.forEach((listener) => {
    try {
      listener(mode);
    } catch (e) {
      console.error('Error in mode listener:', e);
    }
  });
}

export function onAppModeChange(listener: (mode: 'live' | 'demo') => void): () => void {
  modeListeners.add(listener);
  let removeBrowserHandler: (() => void) | null = null;
  if (typeof window !== 'undefined') {
    const handler = (e: Event) => {
      const customEvt = e as CustomEvent<'live' | 'demo'>;
      listener(customEvt.detail || getAppMode());
    };
    window.addEventListener('app_mode_change', handler);
    removeBrowserHandler = () => window.removeEventListener('app_mode_change', handler);
  }
  return () => {
    modeListeners.delete(listener);
    if (removeBrowserHandler) removeBrowserHandler();
  };
}

export function isLiveMode(): boolean {
  return getAppMode() === 'live';
}

export function getEndpointUrl(path: string): string {
  const cleanBase = API_CONFIG.baseUrl.replace(/\/+$/, '');
  const cleanPrefix = API_CONFIG.apiPrefix.replace(/\/+$/, '');
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${cleanBase}${cleanPrefix}${cleanPath}`;
}
