import { useState, useEffect, useRef } from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  Menu,
  Search,
  Bell,
  User,
  ChevronDown,
  LogIn,
  LogOut,
  Server,
  Eye,
  EyeOff,
  AlertCircle,
  ShieldCheck,
  UserPlus,
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { authService } from '../../services/authService';
import {
  API_CONFIG,
  isLiveMode,
  setAppMode,
  onAppModeChange,
  ConnectionState,
  BackendHealthInfo,
  setConnectionState as setGlobalConnectionState,
  getConnectionState,
  getBackendHealth,
  onConnectionStateChange,
} from '../../services/apiConfig';
import { apiClient } from '../../services/apiClient';
import { User as UserType, UserRole } from '../../types';

interface TopNavbarProps {
  onOpenMobileMenu?: () => void;
  onToggleSidebar?: () => void;
  isSidebarCollapsed?: boolean;
  isMobileSidebarOpen?: boolean;
}

const PAGE_TITLES: Record<string, { title: string; subtitle: string }> = {
  '/': { title: 'Operations Overview', subtitle: 'Live event monitoring & command center' },
  '/teams': { title: 'Registered Teams', subtitle: '32 Teams roster & qualification tracking' },
  '/participants': { title: 'Participants Directory', subtitle: '160 college participants directory' },
  '/round-1': { title: 'Round 1: The Great Expedition', subtitle: '3 Timed Mini-Rounds · 32 squads compete for 24 spots' },
  '/round-2': { title: 'Round 2: Cabo', subtitle: '3 Cabo card games · 24 squads compete for 12 spots' },
  '/round-3': { title: 'Round 3: The Black Market', subtitle: 'Points-based economy & hidden code verification · 12 squads compete for 8 spots' },
  '/black-market': { title: 'Round 3: The Black Market', subtitle: 'Points-based economy & hidden code verification · 12 squads compete for 8 spots' },
  '/round-4': { title: 'Round 4: The Legal Battle', subtitle: '4 Fictional Courtroom Trials · 8 finalist squads compete for Grand Finale' },
  '/legal-battle': { title: 'Round 4: The Legal Battle', subtitle: '4 Fictional Courtroom Trials · 8 finalist squads compete for Grand Finale' },
  '/rounds': { title: 'Round Progression', subtitle: '5-Stage elimination and qualification structure' },
  '/scoreboard': { title: 'Live Scoreboard', subtitle: 'Official multi-round cumulative leaderboard' },
  '/secret-agents': { title: 'Secret Agent Programme', subtitle: 'Confidential agent operations & sabotage audit' },
  '/code-fragments': { title: 'Hidden Code Hunt', subtitle: 'Campus QR clues & code discovery tracker' },
  '/judges': { title: 'Judges Panel (Round 4)', subtitle: 'Moot court debate scorecards & criteria' },
  '/finale': { title: 'Grand Finale & Awards', subtitle: 'Top 3 podium calculation & agent deductions' },
  '/settings': { title: 'Event Settings', subtitle: 'Configuration, timers & system diagnostics' },
};

export function TopNavbar({
  onOpenMobileMenu,
  onToggleSidebar,
  isSidebarCollapsed = false,
}: TopNavbarProps) {
  const location = useLocation();
  const current = PAGE_TITLES[location.pathname] || {
    title: 'Operations Dashboard',
    subtitle: 'BMSIT Event HQ Console',
  };

  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [currentUser, setCurrentUser] = useState<UserType | null>(authService.getCurrentUser());
  const [liveMode, setLiveModeState] = useState<boolean>(isLiveMode());
  const [showLoginModal, setShowLoginModal] = useState<boolean>(false);

  // Refs for closing popovers on outside click
  const profileMenuRef = useRef<HTMLDivElement>(null);
  const statusMenuRef = useRef<HTMLDivElement>(null);
  const notificationsMenuRef = useRef<HTMLDivElement>(null);

  // Form states for login modal
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  const [connectionState, setConnectionState] = useState<ConnectionState>(getConnectionState());
  const [serverHealth, setServerHealth] = useState<BackendHealthInfo>(getBackendHealth());

  const checkHealthAndConnection = async () => {
    if (!isLiveMode()) {
      const demoState: ConnectionState = 'demo';
      const demoHealth: BackendHealthInfo = {
        online: false,
        database: 'demo-local-storage',
        message: 'Local browser demo simulation active. No live API connection.',
      };
      setConnectionState(demoState);
      setServerHealth(demoHealth);
      setGlobalConnectionState(demoState, demoHealth);
      return;
    }

    try {
      const res = await apiClient.get<{ status: string; database: string }>('/health');
      if (res && res.success && res.data?.status === 'online') {
        const dbStatus = res.data.database || 'healthy';
        const onlineHealth: BackendHealthInfo = {
          online: true,
          database: dbStatus,
          message: 'FastAPI gateway and database are online',
        };
        setServerHealth(onlineHealth);

        const token = apiClient.getToken();
        if (!token) {
          const user = authService.getCurrentUser();
          const targetState: ConnectionState = (user?.role === 'PUBLIC_PROJECTOR')
            ? 'connected_public'
            : 'unauthenticated';
          setConnectionState(targetState);
          setGlobalConnectionState(targetState, onlineHealth);
          return;
        }

        // Validate token against /auth/me
        try {
          const meRes = await apiClient.get<UserType>('/auth/me');
          if (meRes.success && meRes.data) {
            authService.saveUserToStorage(meRes.data);
            const staffState: ConnectionState = ['ORGANIZER', 'MARSHAL', 'JUDGE'].includes(meRes.data.role)
              ? 'connected_staff'
              : 'connected_public';
            setConnectionState(staffState);
            setGlobalConnectionState(staffState, onlineHealth);
          } else {
            const expState: ConnectionState = 'token_expired';
            setConnectionState(expState);
            setGlobalConnectionState(expState, onlineHealth);
          }
        } catch (authErr: unknown) {
          const apiErr = authErr as { status?: number };
          if (apiErr?.status === 401 || apiErr?.status === 403) {
            authService.logout();
            const expState: ConnectionState = 'token_expired';
            setConnectionState(expState);
            setGlobalConnectionState(expState, onlineHealth);
          } else {
            const unauthState: ConnectionState = 'unauthenticated';
            setConnectionState(unauthState);
            setGlobalConnectionState(unauthState, onlineHealth);
          }
        }
      } else {
        const offlineState: ConnectionState = 'offline';
        const offlineHealth: BackendHealthInfo = {
          online: false,
          database: 'disconnected',
          message: 'FastAPI server responded with an error or unready state',
        };
        setConnectionState(offlineState);
        setServerHealth(offlineHealth);
        setGlobalConnectionState(offlineState, offlineHealth);
      }
    } catch {
      const offlineState: ConnectionState = 'offline';
      const offlineHealth: BackendHealthInfo = {
        online: false,
        database: 'unreachable',
        message: `Unable to connect to FastAPI service at ${API_CONFIG.baseUrl}`,
      };
      setConnectionState(offlineState);
      setServerHealth(offlineHealth);
      setGlobalConnectionState(offlineState, offlineHealth);
    }
  };

  useEffect(() => {
    const unsub = authService.subscribe((user) => {
      setCurrentUser(user);
    });

    const unsubMode = onAppModeChange((mode) => {
      setLiveModeState(mode === 'live');
      checkHealthAndConnection();
    });

    const unsubConn = onConnectionStateChange((state, health) => {
      setConnectionState(state);
      setServerHealth(health);
    });

    checkHealthAndConnection();
    const interval = setInterval(checkHealthAndConnection, 15000);

    return () => {
      unsub();
      unsubMode();
      unsubConn();
      clearInterval(interval);
    };
  }, []);

  // Close menus when clicking outside or pressing Escape
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent | TouchEvent) => {
      const target = e.target as Node;
      if (showProfile && profileMenuRef.current && !profileMenuRef.current.contains(target)) {
        setShowProfile(false);
      }
      if (showStatusModal && statusMenuRef.current && !statusMenuRef.current.contains(target)) {
        setShowStatusModal(false);
      }
      if (showNotifications && notificationsMenuRef.current && !notificationsMenuRef.current.contains(target)) {
        setShowNotifications(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowProfile(false);
        setShowStatusModal(false);
        setShowNotifications(false);
      }
    };

    document.addEventListener('mousedown', handleOutsideClick);
    document.addEventListener('touchstart', handleOutsideClick);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('touchstart', handleOutsideClick);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [showProfile, showStatusModal, showNotifications]);

  const toggleProfile = () => {
    setShowProfile((prev) => !prev);
    setShowNotifications(false);
    setShowStatusModal(false);
  };

  const toggleNotifications = () => {
    setShowNotifications((prev) => !prev);
    setShowProfile(false);
    setShowStatusModal(false);
  };

  const toggleStatusModal = () => {
    setShowStatusModal((prev) => !prev);
    setShowProfile(false);
    setShowNotifications(false);
  };

  const handleToggleMode = (mode: 'live' | 'demo') => {
    setAppMode(mode);
    setLiveModeState(mode === 'live');
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);
    setIsLoggingIn(true);
    try {
      const user = await authService.login({ email: loginEmail, password: loginPassword });
      setCurrentUser(user);
      setShowLoginModal(false);
      setLoginEmail('');
      setLoginPassword('');
      setShowPassword(false);
      await checkHealthAndConnection();
    } catch (err: unknown) {
      const eObj = err as { message?: string };
      setLoginError(eObj.message || 'Login failed. Please verify credentials.');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleLogout = () => {
    authService.logout();
    setCurrentUser(null);
    setShowProfile(false);
    checkHealthAndConnection();
  };

  // True staff status strictly requires valid token in Live mode
  const isStaffAuthenticated = Boolean(
    liveMode &&
    currentUser &&
    ['ORGANIZER', 'MARSHAL', 'JUDGE'].includes(currentUser.role) &&
    apiClient.getToken()
  );

  return (
    <header className="sticky top-0 z-40 h-16 bg-[#070b16]/85 backdrop-blur-2xl border-b border-cyan-500/20 px-4 lg:px-8 flex items-center justify-between shadow-[0_4px_24px_rgba(0,0,0,0.4)] transition-all">
      {/* Left: Universal Accessible Hamburger Toggle & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => {
            if (onToggleSidebar) {
              onToggleSidebar();
            } else if (onOpenMobileMenu) {
              onOpenMobileMenu();
            }
          }}
          aria-label={isSidebarCollapsed ? 'Expand navigation sidebar' : 'Collapse navigation sidebar'}
          aria-expanded={!isSidebarCollapsed}
          title={isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="p-2 rounded-xl text-slate-300 hover:text-cyan-300 hover:bg-cyan-500/10 border border-cyan-500/30 hover:border-cyan-400/70 transition-all shadow-[0_0_12px_rgba(6,182,212,0.15)] flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-cyan-400 cursor-pointer shrink-0"
        >
          <Menu className="w-5 h-5 text-cyan-400" />
        </button>

        <div className="hidden sm:block">
          <div className="flex items-center gap-2 text-xs">
            <span className="font-mono text-cyan-400/70 font-semibold uppercase tracking-wider text-[11px]">BMSIT // HQ</span>
            <span className="text-slate-600">/</span>
            <h1 className="font-orbitron font-bold text-sm tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 via-white to-violet-300">
              {current.title}
            </h1>
          </div>
          <p className="text-[11px] text-slate-400 font-mono hidden md:block">
            {current.subtitle}
          </p>
        </div>
      </div>

      {/* Center: Cyber Command Search */}
      <div className="hidden xl:flex items-center flex-1 max-w-xs mx-8">
        <div className="relative w-full">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-cyan-400/60" />
          <input
            type="text"
            placeholder="Search squads, cadets, agents... (Press /)"
            className="w-full bg-[#030712]/70 border border-cyan-500/20 rounded-xl pl-9 pr-8 py-1.5 text-xs text-slate-200 placeholder-slate-500 font-sans focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400/50 transition-all shadow-inner"
          />
          <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800/80 border border-slate-700 text-slate-400">
            /
          </kbd>
        </div>
      </div>

      {/* Right: Mode Toggle + Connection Indicator + Profile */}
      <div className="flex items-center gap-2.5 sm:gap-3">
        {/* Segmented Mode Switcher */}
        <div className="flex items-center bg-[#030712]/80 p-1 rounded-xl border border-cyan-500/25 shadow-inner">
          <button
            onClick={() => handleToggleMode('live')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono font-semibold transition-all cursor-pointer ${
              liveMode
                ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow-[0_0_12px_rgba(6,182,212,0.4)] border border-cyan-300/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${liveMode ? 'bg-white animate-pulse' : 'bg-slate-600'}`} />
            Live API
          </button>
          <button
            onClick={() => handleToggleMode('demo')}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono font-semibold transition-all cursor-pointer ${
              !liveMode
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-[0_0_10px_rgba(245,158,11,0.2)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${!liveMode ? 'bg-amber-400 animate-pulse' : 'bg-slate-600'}`} />
            Demo Mode
          </button>
        </div>

        {/* Connection Diagnostics Pill */}
        <div className="relative" ref={statusMenuRef}>
          <button
            type="button"
            onClick={toggleStatusModal}
            aria-haspopup="true"
            aria-expanded={showStatusModal}
            aria-label="System diagnostics status"
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-mono border transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-cyan-400 ${
              !liveMode
                ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                : connectionState === 'connected_staff'
                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.15)]'
                : connectionState === 'connected_public'
                ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'
                : connectionState === 'checking'
                ? 'bg-slate-800/60 text-slate-300 border-slate-700'
                : 'bg-rose-500/10 text-rose-300 border-rose-500/30'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                !liveMode
                  ? 'bg-amber-400 animate-pulse'
                  : connectionState === 'connected_staff'
                  ? 'bg-emerald-400 animate-pulse'
                  : connectionState === 'connected_public'
                  ? 'bg-cyan-400'
                  : connectionState === 'checking'
                  ? 'bg-blue-400 animate-ping'
                  : 'bg-rose-500'
              }`}
            />
            <span className="hidden sm:inline font-bold">
              {!liveMode
                ? 'Demo Active'
                : connectionState === 'connected_staff'
                ? `Live · ${currentUser?.role || 'STAFF'}`
                : connectionState === 'connected_public'
                ? 'Live · Public View'
                : connectionState === 'checking'
                ? 'Probing Gateway...'
                : 'API Offline'}
            </span>
          </button>

          {/* Diagnostics popover */}
          {showStatusModal && (
            <div className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] bg-[#090d1a]/98 backdrop-blur-2xl border border-cyan-500/30 rounded-2xl shadow-[0_12px_40px_rgba(0,0,0,0.85)] p-4 z-50 text-xs animate-in fade-in-50 zoom-in-95">
              <div className="flex items-center justify-between pb-3 border-b border-cyan-500/20">
                <div className="flex items-center gap-2">
                  <Server className="w-4 h-4 text-cyan-400" />
                  <span className="font-orbitron font-bold text-xs tracking-wide text-white">System Diagnostics</span>
                </div>
                <button
                  type="button"
                  onClick={checkHealthAndConnection}
                  className="text-[10px] font-mono font-semibold text-cyan-400 hover:text-cyan-300 transition-colors cursor-pointer"
                >
                  Refresh
                </button>
              </div>

              <div className="space-y-2.5 mt-3">
                <div className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="flex items-center justify-between text-[11px] font-mono">
                    <span className="text-slate-400">Gateway Status</span>
                    <span
                      className={`font-bold ${
                        !liveMode
                          ? 'text-amber-400'
                          : serverHealth.online
                          ? 'text-emerald-400'
                          : 'text-rose-400'
                      }`}
                    >
                      {!liveMode
                        ? 'DEMO SIMULATION'
                        : serverHealth.online
                        ? 'ONLINE'
                        : 'OFFLINE'}
                    </span>
                  </div>
                  <p className="text-[10px] font-mono text-slate-400 mt-1">
                    {!liveMode
                      ? 'Local browser mock simulation. Live network calls disabled.'
                      : serverHealth.message}
                  </p>
                </div>

                <div className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="flex items-center justify-between text-[11px] font-mono">
                    <span className="text-slate-400">Database Engine</span>
                    <span className="text-cyan-300 font-bold">{serverHealth.database}</span>
                  </div>
                </div>

                <div className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="flex items-center justify-between text-[11px] font-mono">
                    <span className="text-slate-400">Authorization</span>
                    <span className="text-violet-300 font-bold">{currentUser?.role || 'PUBLIC'}</span>
                  </div>
                  <p className="text-[10px] font-mono text-slate-400 mt-1">
                    {connectionState === 'connected_staff'
                      ? 'Authorized staff token active. Mutations enabled.'
                      : 'Public observer mode. Scorecards only.'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Notifications Button */}
        <div className="relative" ref={notificationsMenuRef}>
          <button
            type="button"
            onClick={toggleNotifications}
            aria-haspopup="true"
            aria-expanded={showNotifications}
            aria-label="Notifications"
            className="p-2 rounded-xl text-slate-400 hover:text-cyan-300 hover:bg-cyan-500/10 border border-slate-800 transition-colors relative cursor-pointer focus:outline-none focus:ring-2 focus:ring-cyan-400"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.8)]" />
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] bg-[#090d1a]/98 backdrop-blur-2xl border border-cyan-500/30 rounded-2xl shadow-[0_12px_40px_rgba(0,0,0,0.85)] p-3 z-50 animate-in fade-in-50 zoom-in-95">
              <div className="flex items-center justify-between px-2 py-1.5 border-b border-cyan-500/20">
                <span className="font-orbitron font-bold text-xs text-white">Event Broadcasts</span>
                <span className="text-[10px] font-mono text-cyan-400 font-semibold">3 New</span>
              </div>
              <div className="space-y-2 mt-2">
                <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800 text-xs">
                  <p className="font-bold text-slate-200">Vanguard Unit 04 Scored</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">Scored 75 pts in Round 1: Mini 1.</p>
                </div>
                <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800 text-xs">
                  <p className="font-bold text-slate-200">Agent Alpha Identified</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">Encrypted sabotage report uploaded.</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Public Squad Registration CTA */}
        <Link
          to="/register"
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 text-xs font-orbitron font-semibold border border-cyan-500/30 transition-all cursor-pointer shadow-sm"
          title="Open Public Squad Registration Portal"
        >
          <UserPlus className="w-3.5 h-3.5 text-cyan-400" />
          <span>Register Squad</span>
        </Link>

        {/* Direct Organizer Login CTA for fast access when unauthenticated in Live Mode */}
        {liveMode && !isStaffAuthenticated && (
          <button
            type="button"
            onClick={() => {
              setShowLoginModal(true);
              setShowProfile(false);
              setShowStatusModal(false);
              setShowNotifications(false);
            }}
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-violet-600 hover:from-cyan-400 hover:to-blue-500 text-white text-xs font-orbitron font-bold shadow-[0_0_16px_rgba(6,182,212,0.35)] border border-cyan-300/40 transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-cyan-400 focus:ring-offset-1 focus:ring-offset-[#070b16]"
            title="Authenticate as Organizer or Staff"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Organizer Login</span>
          </button>
        )}

        {/* User Profile & Access Control Dropdown */}
        <div className="relative" ref={profileMenuRef}>
          <button
            type="button"
            onClick={toggleProfile}
            aria-haspopup="true"
            aria-expanded={showProfile}
            aria-label="User account and role options"
            className="flex items-center gap-2 p-1.5 pl-2 pr-2.5 rounded-xl bg-[#030712]/60 hover:bg-cyan-500/10 border border-cyan-500/25 transition-all cursor-pointer shadow-sm focus:outline-none focus:ring-2 focus:ring-cyan-400"
          >
            <div
              className={`w-7 h-7 rounded-lg text-white flex items-center justify-center text-xs font-orbitron font-bold shadow-sm ${
                isStaffAuthenticated
                  ? 'bg-gradient-to-br from-emerald-500 to-cyan-600 shadow-[0_0_10px_rgba(16,185,129,0.4)]'
                  : !liveMode
                  ? 'bg-gradient-to-br from-amber-500 to-orange-600 shadow-[0_0_10px_rgba(245,158,11,0.4)]'
                  : 'bg-slate-800 border border-cyan-500/30 text-cyan-400'
              }`}
            >
              {isStaffAuthenticated && currentUser?.name
                ? currentUser.name.charAt(0).toUpperCase()
                : !liveMode && currentUser?.name
                ? currentUser.name.charAt(0).toUpperCase()
                : <User className="w-3.5 h-3.5" />}
            </div>
            <div className="text-left hidden md:block">
              <div className="text-xs font-semibold text-slate-200 leading-none">
                {isStaffAuthenticated
                  ? currentUser!.name
                  : !liveMode
                  ? (currentUser?.name || 'Demo Operator')
                  : 'Public Viewer'}
              </div>
              <div
                className={`text-[10px] font-mono leading-none mt-1 font-bold ${
                  isStaffAuthenticated
                    ? 'text-emerald-400'
                    : !liveMode
                    ? 'text-amber-400'
                    : 'text-cyan-400'
                }`}
              >
                {isStaffAuthenticated
                  ? currentUser!.role
                  : !liveMode
                  ? (currentUser?.role || 'DEMO')
                  : 'READ-ONLY'}
              </div>
            </div>
            <ChevronDown
              className={`w-3.5 h-3.5 text-slate-400 hidden md:block transition-transform duration-200 ${
                showProfile ? 'rotate-180 text-cyan-400' : ''
              }`}
            />
          </button>

          {showProfile && (
            <div className="absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] bg-[#090d1a]/98 backdrop-blur-2xl border border-cyan-500/35 rounded-2xl shadow-[0_16px_50px_rgba(0,0,0,0.9)] p-3.5 z-50 text-xs animate-in fade-in-50 zoom-in-95">
              {/* Case 1: Live Mode + Unauthenticated (Public Viewer) */}
              {liveMode && !isStaffAuthenticated && (
                <div className="space-y-3">
                  <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                    <div className="w-9 h-9 rounded-xl bg-slate-800 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-inner shrink-0">
                      <User className="w-4 h-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1">
                        <p className="font-orbitron font-bold text-slate-100 text-xs truncate">Public Viewer</p>
                        <span className="text-[9px] bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 px-2 py-0.5 rounded-full font-mono font-bold">
                          GUEST
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 font-mono mt-0.5 truncate">
                        Read-Only Spectator View
                      </p>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-xl bg-cyan-950/30 border border-cyan-500/20 text-slate-300 text-[11px] font-mono leading-relaxed">
                    <span className="text-cyan-400 font-bold block mb-0.5">Spectator Mode Active</span>
                    Viewing public scoreboard and live tournament rounds. Squad registration, editing, and participant contact details require staff authentication.
                  </div>

                  <button
                    type="button"
                    onClick={() => {
                      setShowProfile(false);
                      setShowLoginModal(true);
                    }}
                    className="w-full py-2.5 px-3 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-violet-600 hover:from-cyan-400 hover:to-blue-500 text-white flex items-center justify-center gap-2 text-xs font-orbitron font-bold shadow-[0_0_20px_rgba(6,182,212,0.4)] border border-cyan-300/40 transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-cyan-400"
                  >
                    <LogIn className="w-4 h-4" />
                    Sign In as Organizer
                  </button>
                </div>
              )}

              {/* Case 2: Live Mode + Authenticated Staff (ORGANIZER / MARSHAL / JUDGE) */}
              {isStaffAuthenticated && (
                <div className="space-y-3">
                  <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-900/80 border border-emerald-500/30">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-600 text-white flex items-center justify-center text-sm font-orbitron font-bold shadow-[0_0_12px_rgba(16,185,129,0.3)] shrink-0">
                      {currentUser!.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1">
                        <p className="font-orbitron font-bold text-slate-100 text-xs truncate">{currentUser!.name}</p>
                        <span className="text-[9px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded-full font-mono font-bold">
                          {currentUser!.role}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 font-mono mt-0.5 truncate">{currentUser!.email}</p>
                    </div>
                  </div>

                  <div className="p-2 rounded-xl bg-emerald-950/25 border border-emerald-500/25 text-emerald-300 text-[11px] font-mono flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>JWT Session Active &amp; Verified</span>
                  </div>

                  <button
                    type="button"
                    onClick={() => {
                      authService.setProjectorView();
                      setShowProfile(false);
                      checkHealthAndConnection();
                    }}
                    className="w-full py-2 px-3 rounded-xl bg-slate-900/70 hover:bg-slate-800 text-slate-300 hover:text-cyan-300 border border-slate-800 hover:border-cyan-500/30 flex items-center justify-between text-xs font-mono transition-all cursor-pointer"
                  >
                    <span>Preview Public View</span>
                    <span className="text-[10px] text-slate-500">Read-Only</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleLogout}
                    className="w-full py-2 px-3 rounded-xl text-rose-400 hover:bg-rose-500/10 border border-rose-500/30 flex items-center justify-center gap-1.5 text-xs font-mono font-bold transition-all cursor-pointer"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    Sign Out Session
                  </button>
                </div>
              )}

              {/* Case 3: Demo Mode (Local Simulation) */}
              {!liveMode && (
                <div className="space-y-3">
                  <div className="flex items-center gap-3 p-3 rounded-xl bg-amber-950/20 border border-amber-500/30">
                    <div className="w-9 h-9 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-300 flex items-center justify-center text-sm font-orbitron font-bold shrink-0">
                      {currentUser?.name?.charAt(0).toUpperCase() || 'D'}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-1">
                        <p className="font-orbitron font-bold text-amber-200 text-xs truncate">
                          {currentUser?.name || 'Demo Operator'}
                        </p>
                        <span className="text-[9px] bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded-full font-mono font-bold">
                          DEMO
                        </span>
                      </div>
                      <p className="text-[11px] text-amber-400/70 font-mono mt-0.5 truncate">
                        Local browser simulation
                      </p>
                    </div>
                  </div>

                  <div>
                    <p className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                      Simulate Role (Demo Only)
                    </p>
                    <div className="grid grid-cols-2 gap-1.5">
                      {(['ORGANIZER', 'MARSHAL', 'JUDGE', 'PUBLIC_PROJECTOR'] as UserRole[]).map((r) => (
                        <button
                          key={r}
                          type="button"
                          onClick={() => {
                            authService.setDemoUser(r);
                            setShowProfile(false);
                          }}
                          className={`text-[10px] py-1.5 px-2 rounded-xl border text-left font-mono font-semibold transition-all cursor-pointer ${
                            currentUser?.role === r
                              ? 'bg-amber-500/30 text-amber-200 border-amber-500/50 shadow-[0_0_10px_rgba(245,158,11,0.2)]'
                              : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:border-amber-500/40 hover:text-amber-300'
                          }`}
                        >
                          {r === 'PUBLIC_PROJECTOR' ? 'Public View' : r}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Organizer & Staff Login Modal */}
      {showLoginModal && (
        <Modal
          isOpen={showLoginModal}
          onClose={() => {
            setShowLoginModal(false);
            setShowPassword(false);
            setLoginError(null);
          }}
          title="Organizer & Staff Authentication"
          subtitle="FastAPI Gateway · Live Database Connection"
          maxWidth="md"
        >
          <form onSubmit={handleLoginSubmit} className="space-y-4 text-xs font-sans">
            <div className="p-3 bg-cyan-950/40 border border-cyan-500/30 rounded-xl text-cyan-200">
              <p className="font-orbitron font-bold text-xs mb-1 text-cyan-300">FastAPI Authorization Gateway</p>
              <p className="text-[11px] font-mono opacity-90 leading-relaxed text-slate-300">
                Log in as an authorized organizer, marshal, or judge to manage tournament registrations, enter scores, and view participant PII.
              </p>
              <div className="mt-2 flex items-center flex-wrap gap-2 pt-2 border-t border-cyan-500/20">
                <span className="text-[10px] font-mono text-slate-400">Quick Fill:</span>
                <button
                  type="button"
                  onClick={() => setLoginEmail('gundatharuntej2006@gmail.com')}
                  className="text-[10px] font-mono text-cyan-400 hover:text-cyan-300 underline cursor-pointer"
                >
                  gundatharuntej2006@gmail.com
                </button>
                <span className="text-slate-600">·</span>
                <button
                  type="button"
                  onClick={() => setLoginEmail('organizer@bmsit.in')}
                  className="text-[10px] font-mono text-slate-400 hover:text-cyan-300 underline cursor-pointer"
                >
                  organizer@bmsit.in
                </button>
              </div>
            </div>

            {loginError && (
              <div className="p-3 bg-rose-950/60 border border-rose-500/50 rounded-xl text-rose-200 text-xs font-mono space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-rose-300">
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span>Authentication Failed</span>
                </div>
                <p className="text-[11px] text-rose-300/90 leading-relaxed pl-5.5">
                  {loginError}
                </p>
                <p className="text-[10px] text-slate-400 pl-5.5 mt-1">
                  To reset password via CLI: <code className="text-cyan-300">python cli.py reset-password --email organizer@bmsit.in</code>
                </p>
              </div>
            )}

            <div>
              <label htmlFor="login-email" className="block font-mono text-slate-300 mb-1 font-medium">
                Email Address
              </label>
              <input
                id="login-email"
                type="email"
                required
                autoComplete="username"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                placeholder="organizer@bmsit.in"
                className="w-full px-3 py-2 bg-[#030712] border border-cyan-500/30 rounded-xl text-xs text-slate-100 placeholder-slate-600 focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400 focus:outline-none transition-all"
              />
            </div>

            <div>
              <label htmlFor="login-password" className="block font-mono text-slate-300 mb-1 font-medium">
                Security Key / Password
              </label>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="Enter your security password"
                  className="w-full px-3 py-2 pr-10 bg-[#030712] border border-cyan-500/30 rounded-xl text-xs text-slate-100 placeholder-slate-600 focus:ring-2 focus:ring-cyan-400 focus:border-cyan-400 focus:outline-none transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-cyan-300 transition-colors cursor-pointer p-1"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-cyan-500/20">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowLoginModal(false);
                  setShowPassword(false);
                  setLoginError(null);
                }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                isLoading={isLoggingIn}
                leftIcon={<LogIn className="w-3.5 h-3.5" />}
              >
                Authenticate &amp; Enter HQ
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </header>
  );
}
