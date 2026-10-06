import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Trophy,
  RefreshCw,
  AlertTriangle,
  Clock,
  Flame,
  Lock,
} from 'lucide-react';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { LoadingState } from '../components/ui/LoadingState';
import { eventService } from '../services/eventService';
import { backendApiService } from '../services/backendApiService';
import { authService } from '../services/authService';
import { isLiveMode, getConnectionState, onConnectionStateChange, ConnectionState } from '../services/apiConfig';
import { TeamRound1Record, Round1Config } from '../types/round1';
import { formatTeamNumber } from '../utils/formatters';

export function ScoreboardPage() {
  const [selectedRound, setSelectedRound] = useState<1 | 2>(1);
  const [r1Records, setR1Records] = useState<TeamRound1Record[]>([]);
  const [r1Config, setR1Config] = useState<Round1Config | null>(null);
  const [r2Standings, setR2Standings] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCutoff, setFilterCutoff] = useState<'all' | 'safe' | 'risk'>('all');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
  const [connectionState, setConnectionState] = useState<ConnectionState>(getConnectionState());
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [currentUser, setCurrentUser] = useState(() => authService.getCurrentUser());

  useEffect(() => {
    const unsubAuth = authService.subscribe((u) => setCurrentUser(u));
    return () => unsubAuth();
  }, []);

  const isStaff = Boolean(
    currentUser && ['ORGANIZER', 'MARSHAL', 'JUDGE', 'ADMIN'].includes(currentUser.role)
  );

  const loadScoreboardData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      if (selectedRound === 1) {
        const data = await eventService.getRound1Data();
        setR1Records(data.records || []);
        setR1Config(data.config || null);
      } else {
        const r1Data = await eventService.getRound1Data();
        const isR1Done = r1Data.config?.isFinalized ?? false;
        if (!isR1Done) {
          setR2Standings([]);
        } else if (isLiveMode()) {
          const res = await backendApiService.getCaboStandings();
          if (res.success && res.data) {
            setR2Standings(res.data);
          }
        } else {
          const r2Data = await eventService.getRound2Data();
          setR2Standings(
            r2Data.records.slice(0, 16).map((r) => ({
              teamId: r.teamId,
              teamName: r.teamName,
              teamNumber: r.teamNumber,
              rank: r.rank,
              caboScore: r.totalPoints ?? 0,
              game1Score: r.game1Points ?? 0,
              game2Score: r.game2Points ?? 0,
              game3Score: r.game3Points ?? 0,
              combinedCardTotal: r.combinedCardTotal ?? 30,
              firstPlaceCount: r.firstPlaceCount ?? 0,
              echoStatus: r.echoStatus ?? 'PENDING',
              primeStatus: r.primeStatus ?? 'PENDING',
              isQualified: r.rank ? r.rank <= 8 : false,
            }))
          );
        }
      }
      setLastRefreshed(new Date());
    } catch (err) {
      console.error('Failed to load scoreboard standings:', err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [selectedRound]);

  useEffect(() => {
    loadScoreboardData();

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

  // Round 1 Filtered Standings
  const sortedAndFilteredR1 = useMemo(() => {
    let result = [...r1Records];
    result.sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999));
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (r) =>
          r.teamName.toLowerCase().includes(q) ||
          String(r.teamNumber).includes(q) ||
          formatTeamNumber(r.teamNumber).toLowerCase().includes(q)
      );
    }
    if (filterCutoff === 'safe') {
      result = result.filter((r) => r.rank !== null && r.rank !== undefined && r.rank <= 16);
    } else if (filterCutoff === 'risk') {
      result = result.filter((r) => r.rank === null || r.rank === undefined || r.rank > 16);
    }
    return result;
  }, [r1Records, searchQuery, filterCutoff]);

  // Round 2 Filtered Standings
  const sortedAndFilteredR2 = useMemo(() => {
    let result = [...r2Standings];
    result.sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999));
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      result = result.filter(
        (r) =>
          r.teamName?.toLowerCase().includes(q) ||
          String(r.teamNumber).includes(q) ||
          formatTeamNumber(r.teamNumber).toLowerCase().includes(q)
      );
    }
    if (filterCutoff === 'safe') {
      result = result.filter((r) => r.rank !== null && r.rank !== undefined && r.rank <= 8);
    } else if (filterCutoff === 'risk') {
      result = result.filter((r) => r.rank === null || r.rank === undefined || r.rank > 8);
    }
    return result;
  }, [r2Standings, searchQuery, filterCutoff]);

  const cutoffLimit = selectedRound === 1 ? 16 : 8;

  const formatSeconds = (sec?: number | null) => {
    if (sec === undefined || sec === null) return '—';
    const mins = Math.floor(sec / 60);
    const remainingSec = sec % 60;
    return `${mins}m ${remainingSec.toString().padStart(2, '0')}s`;
  };

  return (
    <div className="space-y-6">
      {/* 1. Hero Section */}
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

        {/* Right side controls */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2.5 self-start lg:self-center shrink-0">
          {/* Round Selector Tabs */}
          <div className="flex bg-[#030d1a] border border-cyan-500/30 rounded-xl p-1 gap-1">
            <button
              onClick={() => {
                setSelectedRound(1);
                setIsLoading(true);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all ${
                selectedRound === 1
                  ? 'bg-cyan-500 text-slate-950 font-black shadow-[0_0_10px_rgba(6,182,212,0.4)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Round 1: The ODDyssey Protocol
            </button>
            <button
              onClick={() => {
                setSelectedRound(2);
                setIsLoading(true);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all ${
                selectedRound === 2
                  ? 'bg-cyan-500 text-slate-950 font-black shadow-[0_0_10px_rgba(6,182,212,0.4)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Round 2: Cabo - The Memory Heist
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-3.5 py-2 text-xs font-semibold rounded-xl border transition-all flex items-center gap-2 backdrop-blur-md shadow-sm font-mono ${
                autoRefresh
                  ? 'bg-cyan-950/60 text-cyan-300 border-cyan-400/50 shadow-[0_0_12px_rgba(34,211,238,0.25)] hover:bg-cyan-900/60'
                  : 'bg-[#061224]/80 text-slate-400 border-cyan-500/20 hover:border-cyan-500/40'
              }`}
            >
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              <span>{autoRefresh ? '30s ON' : 'PAUSED'}</span>
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
      </div>

      {/* 2. Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        <div className="rounded-2xl border border-cyan-500/35 bg-[#061224]/85 backdrop-blur-xl p-5 shadow-[0_0_25px_rgba(6,182,212,0.12)] flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-600/20 border border-blue-400/40 text-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.3)] flex items-center justify-center shrink-0">
            <Trophy className="w-7 h-7" />
          </div>
          <div>
            <div className="text-[11px] font-mono tracking-wider font-semibold text-slate-300 uppercase">
              {selectedRound === 1 ? 'Registered Squads' : 'Qualified Squads'}
            </div>
            <div className="text-3xl font-black font-display text-white mt-0.5 tracking-tight">
              {selectedRound === 1 ? r1Records.length || 32 : 16}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5 font-sans">
              {selectedRound === 1 ? '32 teams entered' : '16 qualifiers competing'}
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-cyan-500/35 bg-[#061224]/85 backdrop-blur-xl p-5 shadow-[0_0_25px_rgba(6,182,212,0.12)] flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-cyan-600/20 border border-cyan-400/40 text-cyan-300 shadow-[0_0_15px_rgba(6,182,212,0.3)] flex items-center justify-center shrink-0">
            <Clock className="w-7 h-7" />
          </div>
          <div>
            <div className="text-[11px] font-mono tracking-wider font-semibold text-slate-300 uppercase">
              {selectedRound === 1 ? 'Gates Track' : 'Cabo Tournament'}
            </div>
            <div className="text-3xl font-black font-display text-white mt-0.5 tracking-tight">
              {selectedRound === 1 ? '3 Gates' : '3 Games'}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5 font-sans">
              {selectedRound === 1 ? 'Signal · Route · Logic' : '16 Tables · 5 Players/Table'}
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-cyan-500/35 bg-[#061224]/85 backdrop-blur-xl p-5 shadow-[0_0_25px_rgba(6,182,212,0.12)] flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.3)] flex items-center justify-center shrink-0">
            <Flame className="w-7 h-7" />
          </div>
          <div>
            <div className="text-[11px] font-mono tracking-wider font-semibold text-slate-300 uppercase">
              Safe in Cutoff
            </div>
            <div className="text-3xl font-black font-display text-white mt-0.5 tracking-tight">
              Top {cutoffLimit}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5 font-sans">
              {selectedRound === 1 ? 'Advancing to Round 2' : 'Advancing to Round 3 (Black Market)'}
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-cyan-500/35 bg-[#061224]/85 backdrop-blur-xl p-5 shadow-[0_0_25px_rgba(6,182,212,0.12)] flex items-center gap-4">
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

      {/* 3. Search & Filter Bar */}
      <div className="rounded-2xl border border-cyan-500/35 bg-[#061224]/85 backdrop-blur-xl p-3 shadow-[0_0_20px_rgba(6,182,212,0.1)] flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative flex-1 w-full">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-cyan-400/70">🔍</span>
          <input
            type="text"
            placeholder="Search squad name, number..."
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
            <option value="safe">Inside Cutoff (Top {cutoffLimit})</option>
            <option value="risk">Elimination Risk (Rank {cutoffLimit + 1}+)</option>
          </select>
        </div>
      </div>

      {/* 4. Standings Table Card */}
      <Card className="rounded-2xl border border-cyan-500/35 bg-[#061224]/85 backdrop-blur-xl shadow-[0_0_30px_rgba(6,182,212,0.12)] overflow-hidden">
        <CardHeader
          title={
            <span className="text-cyan-300 font-display font-bold text-sm tracking-wide">
              {selectedRound === 1
                ? 'Consolidated Standings (Round 1: The ODDyssey Protocol)'
                : 'Consolidated Standings (Round 2: Cabo - The Memory Heist)'}
            </span>
          }
          subtitle={
            selectedRound === 1
              ? `Top 16 squads advance to Round 2 (Cabo). Teams 17+ face elimination.`
              : `Top 8 squads advance to Round 3 (The Black Market). Max score: 75 pts.`
          }
          action={
            <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
              {selectedRound === 1 && (
                <Link
                  to="/protocol/gate/1"
                  className="text-cyan-400 hover:text-cyan-300 px-2 py-1 rounded border border-cyan-500/30 bg-cyan-950/40 mr-2"
                >
                  QR Gate Checkpoints →
                </Link>
              )}
              <span>Sync: {lastRefreshed.toLocaleTimeString()}</span>
            </div>
          }
        />
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8">
              <LoadingState message="Fetching live scoreboard standings..." />
            </div>
          ) : selectedRound === 1 && !isStaff && !r1Config?.isFinalized ? (
            // PUBLIC / PARTICIPANT ISOLATION: ROUND 1 IN PROGRESS
            <div className="p-8 sm:p-12 text-center space-y-4 max-w-lg mx-auto">
              <div className="w-16 h-16 rounded-3xl bg-cyan-950/60 border border-cyan-500/40 text-cyan-400 flex items-center justify-center mx-auto shadow-lg">
                <Lock className="w-8 h-8" />
              </div>
              <div className="space-y-1">
                <h3 className="text-xl font-bold font-display text-white uppercase tracking-tight">
                  Round 1 Telemetry Sealed
                </h3>
                <p className="text-xs text-cyan-300 font-mono">
                  The ODDyssey Protocol is currently underway across campus.
                </p>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed font-mono bg-slate-900/80 p-4 rounded-2xl border border-slate-800">
                To maintain operational mystery and eliminate pacing advantage, live rankings, split times, and scores are sealed for public viewers. Once Round 1 is concluded and finalized by the Tournament Director, the Top 16 Qualified Teams will be revealed here.
              </p>
            </div>
          ) : selectedRound === 1 && !isStaff && r1Config?.isFinalized ? (
            // PUBLIC / PARTICIPANT VIEW: FINALIZED TOP 16 QUALIFIED TEAMS
            <div className="overflow-x-auto">
              <div className="p-4 bg-emerald-950/30 border-b border-emerald-500/30 text-emerald-200 text-xs font-mono flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Trophy className="w-4 h-4 text-emerald-400" />
                  <span className="font-bold">Official Top 16 Qualified Teams &mdash; Advancing to Round 2 (Cabo)</span>
                </div>
                <span className="text-[11px] text-emerald-400/80">Round 1 Concluded</span>
              </div>
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#030712]/90 border-b border-cyan-500/20 text-[11px] font-mono uppercase tracking-wider font-bold text-cyan-400/80">
                    <th className="py-3 px-4 w-16 text-center">Rank</th>
                    <th className="py-3 px-4">Squad Name</th>
                    <th className="py-3 px-4 text-center">Team Identifier</th>
                    <th className="py-3 px-4 text-center">Qualification Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cyan-500/10 text-slate-300">
                  {sortedAndFilteredR1.slice(0, 16).map((team, idx) => (
                    <tr key={team.teamId} className="hover:bg-cyan-500/[0.05] transition-colors">
                      <td className="py-3.5 px-4 text-center font-bold font-mono text-cyan-300">
                        #{team.rank ?? idx + 1}
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-display font-bold text-white text-xs tracking-wide">{team.teamName}</div>
                      </td>
                      <td className="py-3.5 px-4 text-center font-mono text-slate-400">
                        {formatTeamNumber(team.teamNumber)}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-emerald-950/60 border border-emerald-500/40 text-emerald-300">
                          QUALIFIED (TOP 16)
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : selectedRound === 1 ? (
            // ROUND 1 TABLE (ORGANIZER / STAFF REAL-TIME VIEW)
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#030712]/90 border-b border-cyan-500/20 text-[11px] font-mono uppercase tracking-wider font-bold text-cyan-400/80">
                    <th className="py-3 px-4 w-16 text-center">Rank</th>
                    <th className="py-3 px-4">Squad</th>
                    <th className="py-3 px-4 text-center">Gate 1 (Signal)</th>
                    <th className="py-3 px-4 text-center">Gate 2 (Route)</th>
                    <th className="py-3 px-4 text-center">Gate 3 (Logic)</th>
                    <th className="py-3 px-4">Raw Time</th>
                    <th className="py-3 px-4">Penalties</th>
                    <th className="py-3 px-4">Adjusted Total</th>
                    <th className="py-3 px-4 text-center">Rank Pts</th>
                    <th className="py-3 px-4">Projected Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cyan-500/10 text-slate-300">
                  {sortedAndFilteredR1.map((team) => {
                    const rank = team.rank ?? null;
                    const isTopCutoff = rank !== null && rank <= cutoffLimit;
                    const isCutoffLine = rank === cutoffLimit;
                    const mr1 = team.miniRounds?.[0];
                    const mr2 = team.miniRounds?.[1];
                    const mr3 = team.miniRounds?.[2];
                    const rankPoints = team.rankPoints ?? (rank && rank <= 16 ? 17 - rank : 0);

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
                          <td className="py-3.5 px-4 text-center font-bold font-mono">
                            {rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : rank ?? '—'}
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="font-display font-bold text-white text-xs tracking-wide">{team.teamName}</div>
                            <div className="text-[11px] text-slate-400 font-mono">{formatTeamNumber(team.teamNumber)}</div>
                          </td>
                          <td className="py-3.5 px-4 text-center font-mono">
                            {mr1?.status === 'Completed' ? formatSeconds(mr1.durationSeconds) : '—'}
                          </td>
                          <td className="py-3.5 px-4 text-center font-mono">
                            {mr2?.status === 'Completed' ? formatSeconds(mr2.durationSeconds) : '—'}
                          </td>
                          <td className="py-3.5 px-4 text-center font-mono">
                            {mr3?.status === 'Completed' ? formatSeconds(mr3.durationSeconds) : '—'}
                          </td>
                          <td className="py-3.5 px-4 font-mono">{formatSeconds(team.rawTotalSeconds)}</td>
                          <td className="py-3.5 px-4 font-mono text-rose-400">
                            {team.totalPenaltySeconds > 0 ? `+${Math.round(team.totalPenaltySeconds / 60)}m` : '0s'}
                          </td>
                          <td className="py-3.5 px-4 font-mono font-black text-cyan-300">
                            {team.adjustedTotalSeconds !== null ? formatSeconds(team.adjustedTotalSeconds) : 'Pending'}
                          </td>
                          <td className="py-3.5 px-4 text-center font-mono font-bold text-amber-300">
                            {rankPoints > 0 ? `+${rankPoints} pts` : '0 pts'}
                          </td>
                          <td className="py-3.5 px-4">
                            {isTopCutoff ? (
                              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-emerald-950/60 border border-emerald-500/40 text-emerald-300">
                                Top 16 (Safe)
                              </span>
                            ) : (
                              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-rose-950/60 border border-rose-500/40 text-rose-300">
                                Elimination Zone
                              </span>
                            )}
                          </td>
                        </tr>
                        {isCutoffLine && (
                          <tr className="bg-rose-950/40 border-y-2 border-rose-500/60">
                            <td colSpan={10} className="py-2.5 px-4 text-center text-xs font-orbitron font-bold text-rose-300 uppercase">
                              ⚠️ Round 1 Cutoff Threshold — Top 16 Advance to Round 2 (Cabo)
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            // ROUND 2 TABLE
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#030712]/90 border-b border-cyan-500/20 text-[11px] font-mono uppercase tracking-wider font-bold text-cyan-400/80">
                    <th className="py-3 px-4 w-16 text-center">Rank</th>
                    <th className="py-3 px-4">Squad</th>
                    <th className="py-3 px-3 text-center">Game 1 (/25)</th>
                    <th className="py-3 px-3 text-center">Game 2 (/25)</th>
                    <th className="py-3 px-3 text-center">Game 3 (/25)</th>
                    <th className="py-3 px-4 text-right">Cabo Score (/75)</th>
                    <th className="py-3 px-3 text-center" title="Tie-breaker 3: More 1st places">1st Places</th>
                    <th className="py-3 px-3 text-center" title="Tie-breaker 2: Lower card total">Card Total</th>
                    <th className="py-3 px-3 text-center">ECHO</th>
                    <th className="py-3 px-3 text-center">PRIME</th>
                    <th className="py-3 px-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cyan-500/10 text-slate-300">
                  {sortedAndFilteredR2.length === 0 ? (
                    <tr>
                      <td colSpan={11} className="py-12 text-center text-slate-400">
                        <div className="flex flex-col items-center justify-center gap-2">
                          <span className="font-orbitron font-bold text-sm text-amber-300">
                            Waiting for Round 1 qualification
                          </span>
                          <span className="text-xs text-slate-400 max-w-md">
                            Round 2 (Cabo) scoreboard standings unlock automatically once Round 1 is finalized.
                          </span>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    sortedAndFilteredR2.map((squad) => {
                    const rank = squad.rank ?? null;
                    const isTopCutoff = rank !== null && rank <= 8;
                    const isCutoffLine = rank === 8;

                    return (
                      <React.Fragment key={squad.teamId}>
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
                          <td className="py-3.5 px-4 text-center font-bold font-mono">
                            {rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : rank ?? '—'}
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="font-display font-bold text-white text-xs tracking-wide">{squad.teamName}</div>
                            <div className="text-[11px] text-slate-400 font-mono">{formatTeamNumber(squad.teamNumber)}</div>
                          </td>
                          <td className="py-3.5 px-3 text-center font-mono">{squad.game1Score !== undefined ? `${squad.game1Score}p` : '—'}</td>
                          <td className="py-3.5 px-3 text-center font-mono">{squad.game2Score !== undefined ? `${squad.game2Score}p` : '—'}</td>
                          <td className="py-3.5 px-3 text-center font-mono">{squad.game3Score !== undefined ? `${squad.game3Score}p` : '—'}</td>
                          <td className="py-3.5 px-4 text-right font-mono font-black text-cyan-300 text-sm">
                            {squad.caboScore !== undefined ? `${squad.caboScore} pts` : '—'}
                          </td>
                          <td className="py-3.5 px-3 text-center font-mono text-slate-400">{squad.firstPlaceCount ?? 0}</td>
                          <td className="py-3.5 px-3 text-center font-mono text-slate-400">{squad.combinedCardTotal ?? '—'}</td>
                          <td className="py-3.5 px-3 text-center font-mono text-xs">
                            {squad.echoStatus === 'RECOVERED' ? (
                              <span className="text-emerald-300 font-bold bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-500/30">
                                ECHO ✓
                              </span>
                            ) : (
                              <span className="text-slate-600">Pending</span>
                            )}
                          </td>
                          <td className="py-3.5 px-3 text-center font-mono text-xs">
                            {squad.primeStatus === 'RECOVERED' ? (
                              <span className="text-purple-300 font-bold bg-purple-950/60 px-2 py-0.5 rounded border border-purple-500/30">
                                PRIME ✓
                              </span>
                            ) : (
                              <span className="text-slate-600">Pending</span>
                            )}
                          </td>
                          <td className="py-3.5 px-4">
                            {isTopCutoff ? (
                              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-emerald-950/60 border border-emerald-500/40 text-emerald-300">
                                Top 8 (Qualifying)
                              </span>
                            ) : (
                              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-rose-950/60 border border-rose-500/40 text-rose-300">
                                Elimination Zone
                              </span>
                            )}
                          </td>
                        </tr>
                        {isCutoffLine && (
                          <tr className="bg-cyan-950/40 border-y-2 border-cyan-400/60">
                            <td colSpan={11} className="py-2.5 px-4 text-center text-xs font-orbitron font-bold text-cyan-300 uppercase">
                              ⚡ Round 2 Cabo Cutoff Threshold — Top 8 Advance to Round 3: The Black Market
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  }))}
                </tbody>
              </table>
            </div>
          )}
          <div className="p-3 bg-[#070b16]/70 border-t border-cyan-500/20 text-center text-xs text-slate-400 font-mono">
            Public scoreboard view · Telemetry stream from FastAPI gateway · No unauthorized modifications permitted.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
