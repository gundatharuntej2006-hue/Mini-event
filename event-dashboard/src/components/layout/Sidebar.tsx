import { useState, useEffect } from 'react';
import { NavLink, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  UserCheck,
  Compass,
  Layers,
  Trophy,
  Shield,
  QrCode,
  ArrowLeftRight,
  Gavel,
  Award,
  Settings,
  X,
  Radio,
  Sparkles,
} from 'lucide-react';
import { cn } from '../../utils/cn';
import { eventService } from '../../services/eventService';
import { authService } from '../../services/authService';
import { isLiveMode, onAppModeChange } from '../../services/apiConfig';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

interface NavItem {
  label: string;
  path: string;
  icon: typeof LayoutDashboard;
  badge?: string | number;
  badgeColor?: 'cyan' | 'emerald' | 'purple' | 'amber';
  isConfidential?: boolean;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

export function Sidebar({ isOpen, onClose, isCollapsed = false }: SidebarProps) {
  const [counts, setCounts] = useState<{ teams: number | string; participants: number | string }>({
    teams: isLiveMode() ? '...' : '32',
    participants: isLiveMode() ? '...' : '160',
  });

  // Close mobile drawer on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const refreshCounts = async () => {
    if (!isLiveMode()) {
      setCounts({ teams: '32', participants: '160' });
      return;
    }
    try {
      const summary = await eventService.getSummaryCounts();
      setCounts({
        teams: summary.teamsCount,
        participants: summary.participantsCount,
      });
    } catch {
      setCounts({ teams: 0, participants: 0 });
    }
  };

  useEffect(() => {
    refreshCounts();
    const unsubEvent = eventService.subscribe(() => {
      refreshCounts();
    });
    const unsubAuth = authService.subscribe(() => {
      refreshCounts();
    });
    const unsubMode = onAppModeChange(() => {
      refreshCounts();
    });
    return () => {
      unsubEvent();
      unsubAuth();
      unsubMode();
    };
  }, []);

  const navGroups: NavGroup[] = [
    {
      title: 'OPERATIONS',
      items: [
        { label: 'Overview', path: '/', icon: LayoutDashboard },
        { label: 'Teams', path: '/teams', icon: Users, badge: counts.teams, badgeColor: 'cyan' },
        { label: 'Participants', path: '/participants', icon: UserCheck, badge: counts.participants, badgeColor: 'cyan' },
      ],
    },
    {
      title: 'TOURNAMENT',
      items: [
        { label: 'Round 1 — Expedition', path: '/round-1', icon: Compass, badge: 'R1', badgeColor: 'emerald' },
        { label: 'Round 2 — Cabo', path: '/round-2', icon: Layers, badge: 'R2', badgeColor: 'emerald' },
        { label: 'Round 3 — Black Market', path: '/round-3', icon: ArrowLeftRight, badge: 'R3', badgeColor: 'emerald' },
        { label: 'Round 4 — Legal Battle', path: '/round-4', icon: Gavel, badge: 'R4', badgeColor: 'emerald' },
        { label: 'Finale — Championship', path: '/finale', icon: Award, badge: 'R5', badgeColor: 'purple' },
        { label: 'Progression Matrix', path: '/rounds', icon: Layers },
      ],
    },
    {
      title: 'INTELLIGENCE',
      items: [
        { label: 'Live Scoreboard', path: '/scoreboard', icon: Trophy, badge: 'LIVE', badgeColor: 'amber' },
        { label: 'Secret Agents', path: '/secret-agents', icon: Shield, isConfidential: true },
        { label: 'Code Fragments', path: '/code-fragments', icon: QrCode },
        { label: 'Judges Portal', path: '/judges', icon: Gavel },
      ],
    },
    {
      title: 'SYSTEM',
      items: [
        { label: 'Event Settings', path: '/settings', icon: Settings },
      ],
    },
  ];

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Cyber Glass Sidebar */}
      <aside
        aria-label="Sidebar Navigation"
        className={cn(
          'fixed top-0 left-0 bottom-0 z-50 bg-[#070b16]/95 backdrop-blur-2xl text-slate-300 flex flex-col border-r border-cyan-500/20 transition-all duration-300 ease-in-out',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
          isCollapsed ? 'lg:w-20 w-64' : 'w-64'
        )}
      >
        {/* Brand Header */}
        <div
          className={cn(
            'h-16 border-b border-cyan-500/20 flex items-center shrink-0 bg-[#040711]/80 backdrop-blur-md transition-all duration-300',
            isCollapsed ? 'px-3 justify-between lg:justify-center' : 'px-5 justify-between'
          )}
        >
          <div className={cn('flex items-center gap-3 min-w-0', isCollapsed && 'lg:justify-center')}>
            <Link
              to="/"
              className="w-9 h-9 rounded-xl bg-slate-900 border border-cyan-500/50 flex items-center justify-center text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.35)] relative overflow-hidden shrink-0 hover:border-cyan-400 transition-colors"
              title="EVENT HQ · BMSIT"
              onClick={() => {
                if (typeof window !== 'undefined' && window.innerWidth < 1024) onClose();
              }}
            >
              <div className="absolute inset-0 bg-gradient-to-tr from-cyan-500/20 to-transparent" />
              <Sparkles className="w-4 h-4 text-cyan-400 relative z-10" />
            </Link>
            <div className={cn('min-w-0 transition-opacity duration-200', isCollapsed && 'lg:hidden')}>
              <div className="font-orbitron font-extrabold text-sm tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 via-white to-violet-300 flex items-center gap-1.5 truncate">
                EVENT HQ
                <span className="text-[9px] font-mono px-1.5 py-0.2 rounded-full bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40 shrink-0">
                  BMSIT
                </span>
              </div>
              <p className="text-[10px] font-mono text-slate-500 tracking-wider truncate">COMMAND MATRIX</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Active Phase Banner */}
        <div className={cn('shrink-0 transition-all duration-300', isCollapsed ? 'p-2 lg:p-2' : 'p-3')}>
          {isCollapsed ? (
            /* Collapsed Phase Icon for Desktop Rail */
            <Link
              to="/round-1"
              onClick={() => {
                if (typeof window !== 'undefined' && window.innerWidth < 1024) onClose();
              }}
              title="Active Tournament Phase: Round 1 (Expedition)"
              className="hidden lg:flex w-12 h-12 mx-auto rounded-xl bg-slate-900/90 border border-cyan-500/40 hover:border-cyan-400/80 hover:shadow-[0_0_15px_rgba(6,182,212,0.3)] flex-col items-center justify-center text-center transition-all group relative"
            >
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_#22d3ee] mb-1" />
              <span className="text-[10px] font-mono font-bold text-emerald-300">R1</span>
            </Link>
          ) : null}

          <Link
            to="/round-1"
            onClick={() => {
              if (typeof window !== 'undefined' && window.innerWidth < 1024) onClose();
            }}
            className={cn(
              'p-2.5 rounded-xl bg-slate-900/90 border border-cyan-500/30 hover:border-cyan-400/70 hover:shadow-[0_0_15px_rgba(6,182,212,0.2)] transition-all flex items-center justify-between group relative overflow-hidden',
              isCollapsed && 'lg:hidden'
            )}
          >
            <div className="absolute top-0 right-0 w-16 h-16 bg-cyan-500/5 rounded-full blur-xl pointer-events-none" />
            <div className="flex items-center gap-2.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_#22d3ee]" />
              <div className="text-[11px] font-medium text-slate-200">
                <span className="text-slate-500 block text-[9px] font-mono uppercase tracking-widest group-hover:text-cyan-400 transition-colors">
                  LIVE TOURNAMENT PHASE
                </span>
                <span className="font-orbitron font-semibold text-xs text-white">Round 1: Expedition</span>
              </div>
            </div>
            <span className="text-[10px] font-mono bg-emerald-950/80 text-emerald-300 font-bold px-2 py-0.5 rounded-full border border-emerald-500/40 shadow-[0_0_8px_rgba(16,185,129,0.3)]">
              ACTIVE
            </span>
          </Link>
        </div>

        {/* Navigation Groups */}
        <div
          className={cn(
            'flex-1 overflow-y-auto custom-scrollbar transition-all duration-300',
            isCollapsed ? 'px-2 py-2 space-y-4 lg:px-2' : 'px-3 py-2 space-y-5'
          )}
        >
          {navGroups.map((group, gIdx) => (
            <div key={gIdx} className="space-y-1">
              {/* Subtle divider for collapsed rail */}
              {isCollapsed ? (
                <div className="hidden lg:block h-[1px] bg-cyan-500/15 my-2.5 mx-2" title={group.title} />
              ) : null}

              <div
                className={cn(
                  'px-3 pb-1 text-[10px] font-orbitron font-bold uppercase tracking-widest text-slate-500',
                  isCollapsed && 'lg:hidden'
                )}
              >
                {group.title}
              </div>

              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.path === '/'}
                    onClick={() => {
                      if (typeof window !== 'undefined' && window.innerWidth < 1024) onClose();
                    }}
                    title={isCollapsed ? `${item.label}${item.badge !== undefined ? ` (${item.badge})` : ''}` : undefined}
                    className={({ isActive }) =>
                      cn(
                        'rounded-xl text-xs font-medium transition-all group relative flex items-center',
                        isCollapsed
                          ? 'lg:justify-center lg:w-12 lg:h-12 lg:p-0 lg:mx-auto justify-between px-3 py-2'
                          : 'justify-between px-3 py-2',
                        isActive
                          ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/50 font-semibold shadow-[0_0_15px_rgba(6,182,212,0.25)]'
                          : 'text-slate-400 hover:text-slate-100 hover:bg-slate-900/60 hover:border hover:border-slate-800'
                      )
                    }
                  >
                    <div
                      className={cn(
                        'flex items-center gap-2.5 min-w-0',
                        isCollapsed && 'lg:justify-center lg:gap-0'
                      )}
                    >
                      <Icon className="w-4 h-4 sm:w-[18px] sm:h-[18px] shrink-0 transition-colors group-hover:text-cyan-400" />
                      <span className={cn('truncate', isCollapsed && 'lg:hidden')}>{item.label}</span>
                    </div>

                    {item.badge !== undefined && (
                      <span
                        className={cn(
                          'font-mono font-bold leading-none border',
                          isCollapsed
                            ? 'lg:absolute lg:-top-1 lg:-right-1 lg:text-[8px] lg:px-1.5 lg:py-0.5 lg:rounded-full text-[10px] px-2 py-0.5 rounded-full'
                            : 'text-[10px] px-2 py-0.5 rounded-full',
                          item.badgeColor === 'emerald'
                            ? 'bg-emerald-950/80 text-emerald-300 border-emerald-500/50 shadow-[0_0_8px_rgba(16,185,129,0.3)]'
                            : item.badgeColor === 'purple'
                            ? 'bg-purple-950/80 text-purple-300 border-purple-500/50 shadow-[0_0_8px_rgba(168,85,247,0.3)]'
                            : item.badgeColor === 'amber'
                            ? 'bg-amber-950/80 text-amber-300 border-amber-500/50 shadow-[0_0_8px_rgba(245,158,11,0.3)]'
                            : 'bg-cyan-950/80 text-cyan-300 border-cyan-500/50 shadow-[0_0_8px_rgba(6,182,212,0.3)]'
                        )}
                      >
                        {item.badge}
                      </span>
                    )}

                    {item.isConfidential && (
                      <span
                        className={cn(
                          'font-mono uppercase border',
                          isCollapsed
                            ? 'lg:absolute lg:-top-1 lg:-right-1 lg:w-2 lg:h-2 lg:p-0 lg:rounded-full lg:bg-purple-400 lg:border-purple-300 text-[9px] bg-purple-950/70 text-purple-300 px-1.5 py-0.5 rounded-full border-purple-500/40'
                            : 'text-[9px] bg-purple-950/70 text-purple-300 px-1.5 py-0.5 rounded-full border-purple-500/40'
                        )}
                      >
                        {isCollapsed ? <span className="lg:hidden">RESTRICTED</span> : 'RESTRICTED'}
                      </span>
                    )}

                    {/* Floating Cyber Tooltip for Collapsed Desktop Rail */}
                    {isCollapsed && (
                      <div className="hidden lg:group-hover:flex items-center gap-2 absolute left-full ml-3 px-3 py-1.5 bg-[#040c1a]/95 border border-cyan-400/60 text-cyan-200 text-xs font-mono font-semibold rounded-xl shadow-[0_0_20px_rgba(6,182,212,0.4)] whitespace-nowrap z-50 pointer-events-none backdrop-blur-md">
                        <span>{item.label}</span>
                        {item.badge !== undefined && (
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-500/40">
                            {item.badge}
                          </span>
                        )}
                      </div>
                    )}
                  </NavLink>
                );
              })}
            </div>
          ))}
        </div>

        {/* Footer Meta */}
        <div
          className={cn(
            'border-t border-cyan-500/20 bg-[#040711]/80 shrink-0 transition-all duration-300',
            isCollapsed ? 'p-2 lg:p-2' : 'p-3'
          )}
        >
          {isCollapsed ? (
            <div
              className="hidden lg:flex items-center justify-center p-2 rounded-xl text-cyan-400 cursor-pointer"
              title="EVENT HQ · ONLINE"
            >
              <Radio className="w-4 h-4 text-cyan-400 animate-pulse shadow-[0_0_8px_#22d3ee]" />
            </div>
          ) : null}

          <div className={cn('text-[11px] text-slate-400 flex items-center justify-between px-1', isCollapsed && 'lg:hidden')}>
            <span className="font-mono text-[10px] text-slate-500">EVENT HQ · 2026</span>
            <span className="flex items-center gap-1.5 text-[10px] font-mono text-cyan-400">
              <Radio className="w-3 h-3 text-cyan-400 animate-pulse shadow-[0_0_6px_#22d3ee]" />
              ONLINE
            </span>
          </div>
        </div>
      </aside>
    </>
  );
}
