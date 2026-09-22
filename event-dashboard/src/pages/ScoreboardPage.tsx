import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Trophy,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldAlert,
  Flame,
} from 'lucide-react';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { LoadingState } from '../components/ui/LoadingState';
import { EmptyState } from '../components/ui/EmptyState';
import { eventService } from '../services/eventService';
import { isLiveMode, getConnectionState, onConnectionStateChange, ConnectionState } from '../services/apiConfig';
import { TeamRound1Record } from '../types/round1';
import { formatTeamNumber } from '../utils/formatters';

export function ScoreboardPage() {
  const [records, setRecords] = useState<TeamRound1Record[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCutoff, setFilterCutoff] = useState<'all' | 'safe' | 'risk'>('all');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
  const [connectionState, setConnectionState] = useState<ConnectionState>(getConnectionState());
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadScoreboardData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const data = await eventService.getRound1Data();
      setRecords(data.records || []);
      setLastRefreshed(new Date());
    } catch (err) {
      console.error('Failed to load scoreboard standings:', err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadScoreboardData();

    // Subscribe to event updates
    const unsubscribe = eventService.subscribe(() => {
      loadScoreboardData();
    });

    const handleModeChange = () => {
      loadScoreboardData();
    };
    window.addEventListener('app_mode_change', handleModeChange);

    const unsubConn = onConnectionStateChange((state) => {
      setConnectionState(state);
    });

    return () => {
      unsubscribe();
      unsubConn();
      window.removeEventListener('app_mode_change', handleModeChange);
    };
  }, [loadScoreboardData]);

  // Auto-refresh interval (30 seconds)
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      loadScoreboardData();
    }, 30000);
    return () => clearInterval(interval);
  }, [autoRefresh, loadScoreboardData]);

  // Sort and filter standings
  const sortedAndFilteredRecords = useMemo(() => {
    let result = [...records];

    // Sort by rank ascending (null ranks at bottom)
    result.sort((a, b) => {
      const rankA = a.rank ?? 999;
      const rankB = b.rank ?? 999;
      return rankA - rankB;
    });

    // Search query filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (r) =>
          r.teamName.toLowerCase().includes(q) ||
          String(r.teamNumber).includes(q) ||
          formatTeamNumber(r.teamNumber).toLowerCase().includes(q)
      );
    }

    // Cutoff filter (Rank 24 cutoff for Round 1 -> Round 2)
    if (filterCutoff === 'safe') {
      result = result.filter((r) => r.rank !== null && r.rank !== undefined && r.rank <= 24);
    } else if (filterCutoff === 'risk') {
      result = result.filter((r) => r.rank === null || r.rank === undefined || r.rank > 24);
    }

    return result;
  }, [records, searchQuery, filterCutoff]);

  const totalTeams = records.length;
  const completedCount = records.filter((r) => r.isComplete).length;
  const safeCount = records.filter((r) => r.rank !== null && r.rank !== undefined && r.rank <= 24).length;
  const cutoffLimit = 24;

  const formatSeconds = (sec?: number | null) => {
    if (sec === undefined || sec === null) return '—';
    const mins = Math.floor(sec / 60);
    const remainingSec = sec % 60;
    return `${mins}m ${remainingSec.toString().padStart(2, '0')}s`;
  };

  return (
    <div className="space-y-6">
      {/* 1. Hero Section matching Reference Image */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-2 min-h-[140px]">
        <div>
          <div className="text-2xl sm:text-3xl lg:text-4xl font-black font-display tracking-tight uppercase leading-tight">
            <span className="text-white">LIVE </span>
            <span className="text-cyan-400 drop-shadow-[0_0_15px_rgba(34,211,238,0.8)]">TOURNAMENT</span>
            <div className="text-white drop-shadow-[0_0_20px_rgba(255,255,255,0.2)]">SCOREBOARD</div>
          </div>
          <p className="text-xs sm:text-sm text-slate-300 mt-2 max-w-xl font-sans leading-relaxed">
            Real-time consolidated standings, elimination cutoff thresholds, and multi-round telemetry
          </p>
          <div className="mt-3 flex items-center gap-2.5">
            {!isLiveMode() ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-amber-950/60 border border-amber-400/50 text-amber-300 shadow-[0_0_12px_rgba(251,191,36,0.3)]">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                Demo Standings
              </span>
            ) : connectionState === 'offline' ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-rose-950/60 border border-rose-400/50 text-rose-300 shadow-[0_0_12px_rgba(244,63,94,0.3)]">
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                FastAPI Offline
              </span>
            ) : connectionState === 'checking' ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-cyan-950/40 border border-cyan-500/40 text-cyan-300">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                Connecting to Gateway...
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-cyan-950/60 border border-cyan-400/50 text-cyan-300 shadow-[0_0_12px_rgba(34,211,238,0.3)]">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                Live API Connected
              </span>
            )}
          </div>
        </div>

        {/* Right side controls matching reference */}
        <div className="flex items-center gap-2.5 self-start lg:self-center shrink-0">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3.5 py-2 text-xs font-semibold rounded-xl border transition-all flex items-center gap-2 backdrop-blur-md shadow-sm font-mono ${
              autoRefresh
                ? 'bg-cyan-950/60 text-cyan-300 border-cyan-400/50 shadow-[0_0_12px_rgba(34,211,238,0.25)] hover:bg-cyan-900/60'
                : 'bg-[#061224]/80 text-slate-400 border-cyan-500/20 hover:border-cyan-500/40'
            }`}
          >
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>Auto-refresh: {autoRefresh ? '30s ON' : 'PAUSED'}</span>
          </button>

          <button
            onClick={loadScoreboardData}
            disabled={isRefreshing}
            className="px-4 py-2 text-xs font-semibold rounded-xl border border-cyan-400/50 bg-cyan-950/60 text-cyan-300 hover:bg-cyan-900/60 shadow-[0_0_12px_rgba(34,211,238,0.25)] transition-all flex items-center gap-2 font-mono"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Notice Banner */}
      {!isLiveMode() && (
        <div className="bg-amber-950/40 border border-amber-500/30 p-3.5 rounded-2xl flex items-center gap-3 text-xs text-amber-200 font-mono backdrop-blur-md shadow-[0_0_15px_rgba(251,191,36,0.1)]">
          <ShieldAlert className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <span>
            <strong>Demo Simulation:</strong> Operating on simulated tournament dataset. Toggle <strong>Live API</strong> in navbar to stream real-time database standings from FastAPI.
          </span>
        </div>
      )}

      {/* 2. Primary 4 Horizontal Metric Cards matching Reference Image */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        {/* Card 1: Registered Squads */}
        <div className="rounded-2xl border border-cyan-500/35 bg-[#061224]/85 backdrop-blur-xl p-5 shadow-[0_0_25px_rgba(6,182,212,0.12)] hover:border-cyan-400/60 hover:shadow-[0_0_35px_rgba(6,182,212,0.22)] transition-all flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-600/20 border border-blue-400/40 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.3)] flex items-center justify-center shrink-0">
            <Trophy className="w-7 h-7" />
          </div>
          <div>
            <div className="text-[11px] font-mono tracking-wider font-semibold text-slate-300 uppercase">
              Registered Squads
            </div>
            <div className="text-3xl font-black font-display text-white mt-0.5 tracking-tight">
              {totalTeams}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5 font-sans">
              Total tournament field
            </div>
          </div>
        </div>

        {/* Card 2: Completed Expeditions */}
        <div className="rounded-2xl border border-cyan-500/35 bg-[#061224]/85 backdrop-blur-xl p-5 shadow-[0_0_25px_rgba(6,182,212,0.12)] hover:border-cyan-400/60 hover:shadow-[0_0_35px_rgba(6,182,212,0.22)] transition-all flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-cyan-500/20 border border-cyan-400/40 text-cyan-300 shadow-[0_0_15px_rgba(6,182,212,0.3)] flex items-center justify-center shrink-0">
            <CheckCircle2 className="w-7 h-7" />
          </div>
          <div>
            <div className="text-[11px] font-mono tracking-wider font-semibold text-slate-300 uppercase">
              Completed Expeditions
            </div>
            <div className="text-3xl font-black font-display text-white mt-0.5 tracking-tight">
              {completedCount}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5 font-sans">
              {totalTeams - completedCount} in progress
            </div>
          </div>
        </div>

        {/* Card 3: Safe in Cutoff */}
        <div className="rounded-2xl border border-cyan-500/35 bg-[#061224]/85 backdrop-blur-xl p-5 shadow-[0_0_25px_rgba(6,182,212,0.12)] hover:border-cyan-400/60 hover:shadow-[0_0_35px_rgba(6,182,212,0.22)] transition-all flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.3)] flex items-center justify-center shrink-0">
            <Flame className="w-7 h-7" />
          </div>
          <div>
            <div className="text-[11px] font-mono tracking-wider font-semibold text-slate-300 uppercase">
              Safe in Cutoff
            </div>
            <div className="text-3xl font-black font-display text-white mt-0.5 tracking-tight">
              {safeCount} / {cutoffLimit}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5 font-sans">
              Projected to advance to Round 2
            </div>
          </div>
        </div>

        {/* Card 4: Cutoff Threshold */}
        <div className="rounded-2xl border border-cyan-500/35 bg-[#061224]/85 backdrop-blur-xl p-5 shadow-[0_0_25px_rgba(6,182,212,0.12)] hover:border-cyan-400/60 hover:shadow-[0_0_35px_rgba(6,182,212,0.22)] transition-all flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-purple-600/20 border border-purple-400/40 text-purple-300 shadow-[0_0_15px_rgba(168,85,247,0.3)] flex items-center justify-center shrink-0">
            <AlertTriangle className="w-7 h-7" />
          </div>
          <div>
            <div className="text-[11px] font-mono tracking-wider font-semibold text-slate-300 uppercase">
              Cutoff Threshold
            </div>
            <div className="text-3xl font-black font-display text-white mt-0.5 tracking-tight">
              Rank {cutoffLimit}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5 font-sans">
              Teams {cutoffLimit + 1}+ face elimination
            </div>
          </div>
        </div>
      </div>

      {/* 3. Search & Filter Bar matching Reference Image */}
      <div className="rounded-2xl border border-cyan-500/35 bg-[#061224]/85 backdrop-blur-xl p-3 shadow-[0_0_20px_rgba(6,182,212,0.1)] flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative flex-1 w-full">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-cyan-400/70">
            🔍
          </span>
          <input
            type="text"
            placeholder="Search squad name, number (e.g. 04 or T-04)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-transparent text-xs sm:text-sm text-white placeholder:text-slate-400 pl-9 pr-4 py-1.5 focus:outline-hidden font-sans"
          />
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-slate-300 shrink-0 self-end sm:self-center">
          <span>Cutoff Status:</span>
          <select
            value={filterCutoff}
            onChange={(e) => setFilterCutoff(e.target.value as any)}
            className="bg-[#030d1a] border border-cyan-500/40 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-hidden font-mono"
          >
            <option value="all">All Squads</option>
            <option value="safe">Inside Cutoff (Top 24)</option>
            <option value="risk">Elimination Risk (Rank 25+)</option>
          </select>
        </div>
      </div>

      {/* 4. Standings Table Card matching Reference Image */}
      <Card className="rounded-2xl border border-cyan-500/35 bg-[#061224]/85 backdrop-blur-xl shadow-[0_0_30px_rgba(6,182,212,0.12)] overflow-hidden">
        <CardHeader
          title={
            <span className="text-cyan-300 font-display font-bold text-sm tracking-wide">
              Consolidated Standings (Round 1: The Great Expedition)
            </span>
          }
          subtitle={`Top ${cutoffLimit} squads advance to Round 2 (Cabo). Teams ${cutoffLimit + 1}+ face elimination.`}
          action={
            <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
              <span>Sync: {lastRefreshed.toLocaleTimeString()}</span>
            </div>
          }
        />
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8">
              <LoadingState message="Fetching live scoreboard standings from tournament registry..." />
            </div>
          ) : sortedAndFilteredRecords.length === 0 ? (
            <div className="p-8">
              <EmptyState
                icon={Trophy}
                title="No Matching Squads"
                description={
                  searchQuery
                    ? `No registered teams match query "${searchQuery}".`
                    : 'No squad standings available at this time.'
                }
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#030712]/90 border-b border-cyan-500/20 text-[11px] font-mono uppercase tracking-wider font-bold text-cyan-400/80">
                    <th className="py-3 px-4 w-16 text-center">Rank</th>
                    <th className="py-3 px-4">Squad</th>
                    <th className="py-3 px-4 text-center">Station 1</th>
                    <th className="py-3 px-4 text-center">Station 2</th>
                    <th className="py-3 px-4 text-center">Station 3</th>
                    <th className="py-3 px-4">Raw Time</th>
                    <th className="py-3 px-4">Penalties</th>
                    <th className="py-3 px-4">Adjusted Total</th>
                    <th className="py-3 px-4">Projected Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cyan-500/10 text-slate-300">
                  {sortedAndFilteredRecords.map((team) => {
                    const rank = team.rank ?? null;
                    const isTopCutoff = rank !== null && rank <= cutoffLimit;
                    const isCutoffLine = rank === cutoffLimit;
                    const mr1 = team.miniRounds?.[0];
                    const mr2 = team.miniRounds?.[1];
                    const mr3 = team.miniRounds?.[2];

                    return (
                      <React.Fragment key={team.teamId}>
                        <tr
                          className={`transition-colors ${
                            rank === 1
                              ? 'bg-amber-950/20 border-l-2 border-amber-400 hover:bg-amber-950/30'
                              : rank === 2
                              ? 'bg-cyan-950/20 border-l-2 border-cyan-400 hover:bg-cyan-950/30'
                              : rank === 3
                              ? 'bg-violet-950/20 border-l-2 border-violet-400 hover:bg-violet-950/30'
                              : isTopCutoff
                              ? 'hover:bg-cyan-500/[0.05]'
                              : 'bg-rose-950/20 hover:bg-rose-950/30'
                          }`}
                        >
                          {/* Rank Column with Medals */}
                          <td className="py-3.5 px-4 text-center font-bold font-mono">
                            {rank === 1 ? (
                              <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-amber-500/20 text-amber-300 border border-amber-400 text-xs shadow-[0_0_12px_rgba(251,191,36,0.5)]">
                                🥇
                              </span>
                            ) : rank === 2 ? (
                              <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-slate-400/20 text-slate-200 border border-slate-300 text-xs shadow-[0_0_10px_rgba(203,213,225,0.4)]">
                                🥈
                              </span>
                            ) : rank === 3 ? (
                              <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-amber-700/20 text-amber-400 border border-amber-600 text-xs shadow-[0_0_10px_rgba(217,119,6,0.4)]">
                                🥉
                              </span>
                            ) : rank !== null ? (
                              <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-cyan-950/40 text-cyan-300 border border-cyan-500/30 text-xs font-mono font-bold">
                                {rank}
                              </span>
                            ) : (
                              <span className="text-slate-500 font-normal">—</span>
                            )}
                          </td>

                          {/* Squad Name & Identifier */}
                          <td className="py-3.5 px-4">
                            <div className="font-display font-bold text-white text-xs tracking-wide">{team.teamName}</div>
                            <div className="text-[11px] text-slate-400 font-mono">
                              {formatTeamNumber(team.teamNumber)}
                            </div>
                          </td>

                          {/* Station 1 */}
                          <td className="py-3.5 px-4 text-center font-mono">
                            {mr1?.status === 'Completed' ? (
                              <span className="text-cyan-300 font-medium">
                                {formatSeconds(mr1.durationSeconds)}
                              </span>
                            ) : mr1?.status === 'In Progress' ? (
                              <span className="text-cyan-400 animate-pulse font-bold">Active</span>
                            ) : (
                              <span className="text-slate-600">—</span>
                            )}
                          </td>

                          {/* Station 2 */}
                          <td className="py-3.5 px-4 text-center font-mono">
                            {mr2?.status === 'Completed' ? (
                              <span className="text-cyan-300 font-medium">
                                {formatSeconds(mr2.durationSeconds)}
                              </span>
                            ) : mr2?.status === 'In Progress' ? (
                              <span className="text-cyan-400 animate-pulse font-bold">Active</span>
                            ) : (
                              <span className="text-slate-600">—</span>
                            )}
                          </td>

                          {/* Station 3 */}
                          <td className="py-3.5 px-4 text-center font-mono">
                            {mr3?.status === 'Completed' ? (
                              <span className="text-cyan-300 font-medium">
                                {formatSeconds(mr3.durationSeconds)}
                              </span>
                            ) : mr3?.status === 'In Progress' ? (
                              <span className="text-cyan-400 animate-pulse font-bold">Active</span>
                            ) : (
                              <span className="text-slate-600">—</span>
                            )}
                          </td>

                          {/* Raw Time */}
                          <td className="py-3.5 px-4 font-mono font-medium text-slate-300">
                            {formatSeconds(team.rawTotalSeconds)}
                          </td>

                          {/* Penalties */}
                          <td className="py-3.5 px-4 font-mono">
                            {team.totalPenaltySeconds > 0 ? (
                              <span className="text-rose-400 font-bold">
                                +{team.totalPenaltySeconds}s
                              </span>
                            ) : (
                              <span className="text-slate-400">0s</span>
                            )}
                          </td>

                          {/* Adjusted Total */}
                          <td className="py-3.5 px-4 font-mono font-black text-cyan-300">
                            {team.adjustedTotalSeconds !== null && team.adjustedTotalSeconds !== undefined ? (
                              formatSeconds(team.adjustedTotalSeconds)
                            ) : (
                              <span className="text-slate-500 font-normal">Pending</span>
                            )}
                          </td>

                          {/* Status Badge */}
                          <td className="py-3.5 px-4">
                            {isTopCutoff ? (
                              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-semibold bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.25)]">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                In Cutoff (Safe)
                              </span>
                            ) : team.isComplete ? (
                              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-semibold bg-rose-950/60 border border-rose-500/40 text-rose-300 shadow-[0_0_10px_rgba(244,63,94,0.25)]">
                                <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                                Elimination Risk
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-mono font-semibold bg-slate-900/60 border border-slate-700 text-slate-400">
                                In Progress
                              </span>
                            )}
                          </td>
                        </tr>

                        {/* Cutoff Indicator Row */}
                        {isCutoffLine && (
                          <tr className="bg-rose-950/40 border-y-2 border-rose-500/60 shadow-[0_0_15px_rgba(244,63,94,0.3)]">
                            <td colSpan={9} className="py-2.5 px-4 text-center text-xs font-orbitron font-bold text-rose-300 tracking-wider uppercase">
                              ⚠️ Round 1 Elimination Cutoff Threshold — Top {cutoffLimit} Advance to Round 2 (Cabo)
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          <div className="p-3 bg-[#070b16]/70 border-t border-cyan-500/20 text-center text-xs text-slate-400 font-mono">
            Official scoreboard telemetry automatically refreshes when staff enter checkpoint clearances or penalties.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
