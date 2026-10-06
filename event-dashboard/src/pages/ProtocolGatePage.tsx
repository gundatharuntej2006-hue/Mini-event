import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ShieldCheck,
  AlertTriangle,
  QrCode,
  MapPin,
  ArrowRight,
  Printer,
  CheckCircle2,
  RotateCcw,
  Compass,
  Radio,
  Lock,
} from 'lucide-react';
import { backendApiService } from '../services/backendApiService';
import { GateCheckinResult } from '../types/round1';

interface GateConfig {
  gateNumber: number;
  name: string;
  theme: string;
  checkpointLocation: string;
  expectedFragment: string;
  fallbackInstructions: string;
}

const GATE_DATA: Record<number, GateConfig> = {
  1: {
    gateNumber: 1,
    name: 'The Signal Scramble',
    theme: 'Patterns · Ciphers · Frequency Decryption',
    checkpointLocation: 'GATE 42',
    expectedFragment: 'ODD',
    fallbackInstructions: 'If mobile network fails or battery is low, request an Official Yellow Gate 1 Marshal Physical Slip with ink stamp.',
  },
  2: {
    gateNumber: 2,
    name: 'The Route Riddle',
    theme: 'Coordinates · Maps · Campus Navigation',
    checkpointLocation: 'Map Point J',
    expectedFragment: '42',
    fallbackInstructions: 'Physical campus grid cards and backup route maps are available with roving marshals wearing hi-vis bands.',
  },
  3: {
    gateNumber: 3,
    name: 'The Logic Lockdown',
    theme: 'Constraint Satisfaction · Boolean Gates',
    checkpointLocation: 'Lock 48 / Stationary',
    expectedFragment: 'ODD · 42 Validation',
    fallbackInstructions: 'In case of digital sync delays, obtain an Official Gate 3 Progression Pass signed by the Chief Marshal.',
  },
};

export function ProtocolGatePage() {
  const { gateNumber: paramGate } = useParams<{ gateNumber: string }>();
  const parsedGate = parseInt(paramGate || '1', 10);
  const gateNumber = parsedGate >= 1 && parsedGate <= 3 ? parsedGate : 1;

  const gate = GATE_DATA[gateNumber];

  // Registered squads list for dropdown
  const [teams, setTeams] = useState<{ id: string; name: string; team_number: number }[]>([]);
  const [teamIdentifier, setTeamIdentifier] = useState('');
  const [selectedTeamName, setSelectedTeamName] = useState('');
  const [selectedTeamId, setSelectedTeamId] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Checked-in / revealed navigation state
  const [checkinResult, setCheckinResult] = useState<GateCheckinResult | null>(null);

  // Load registered squad names on mount
  useEffect(() => {
    let isMounted = true;
    backendApiService
      .getPublicTeamsForGate()
      .then((res) => {
        if (isMounted && res.data) {
          setTeams(res.data);
        }
      })
      .catch(() => {
        // Fallback: squad can still type their team name manually
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Reset check-in state when switching gates
  useEffect(() => {
    setCheckinResult(null);
    setErrorMessage(null);
  }, [gateNumber]);

  const handleSelectTeam = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const tId = e.target.value;
    setSelectedTeamId(tId);
    const found = teams.find((t) => t.id === tId);
    if (found) {
      setSelectedTeamName(found.name);
      setTeamIdentifier(String(found.team_number).padStart(4, '0'));
    }
  };

  const handleCheckinSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const identifier = teamIdentifier.trim();
    const name = selectedTeamName.trim();
    if (!identifier && !name && !selectedTeamId) {
      setErrorMessage('Please enter your 4-digit Team ID or squad name.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const res = await backendApiService.submitGateCheckin(gateNumber, {
        team_identifier: identifier || undefined,
        team_name: name || undefined,
        team_id: selectedTeamId || undefined,
      });

      if (res.data) {
        setCheckinResult(res.data);
      } else {
        setErrorMessage(res.message || 'Check-in failed. Please verify your team ID.');
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.response?.data?.message || err.message || 'Team not found in tournament roster. Please ensure your squad is registered.';
      setErrorMessage(detail);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetForAnotherSquad = () => {
    setCheckinResult(null);
    setTeamIdentifier('');
    setSelectedTeamName('');
    setSelectedTeamId('');
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-[#030712] text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Protocol Header */}
      <header className="border-b border-cyan-500/20 bg-[#061224]/80 backdrop-blur-md sticky top-0 z-50 px-4 py-3 sm:px-6">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-400/40 text-cyan-300 flex items-center justify-center font-mono font-bold text-sm shadow-[0_0_10px_rgba(6,182,212,0.3)]">
              Ω
            </div>
            <div>
              <div className="font-display font-black text-sm tracking-wide text-white uppercase flex items-center gap-1.5">
                <span>The ODDyssey Protocol</span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-500/30">
                  QR CHECKPOINT
                </span>
              </div>
              <div className="text-[11px] text-slate-400 font-mono">
                Physical Gate Scanner · Server-Authoritative Timing
              </div>
            </div>
          </div>

          <Link
            to="/scoreboard"
            className="text-xs font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors px-2.5 py-1.5 rounded-lg border border-cyan-500/30 bg-cyan-950/40"
          >
            <span>Scoreboard</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-6 sm:px-6 space-y-6">
        {/* Gate Selection Tabs */}
        <div className="grid grid-cols-3 gap-2">
          {([1, 2, 3] as const).map((num) => {
            const isActive = num === gateNumber;
            return (
              <Link
                key={num}
                to={`/protocol/gate/${num}`}
                className={`p-3 rounded-xl border text-center transition-all flex flex-col items-center gap-1 ${
                  isActive
                    ? 'border-cyan-400 bg-cyan-950/50 text-cyan-300 shadow-[0_0_15px_rgba(6,182,212,0.2)]'
                    : 'border-cyan-500/20 bg-[#061224]/60 text-slate-400 hover:border-cyan-500/40 hover:text-slate-200'
                }`}
              >
                <span className="text-[10px] font-mono uppercase tracking-wider font-semibold">
                  Gate 0{num}
                </span>
                <span className="text-xs font-display font-bold truncate max-w-full">
                  {num === 1 ? 'Signal Scramble' : num === 2 ? 'Route Riddle' : 'Logic Lockdown'}
                </span>
                <span className="text-[9px] font-mono text-cyan-400/80">
                  {num === 1 ? 'ODD' : num === 2 ? '42' : 'VALIDATE'}
                </span>
              </Link>
            );
          })}
        </div>

        {/* Gate Header Info Card */}
        <div className="rounded-2xl border border-cyan-500/30 bg-[#061224]/85 backdrop-blur-xl p-5 sm:p-6 shadow-[0_0_30px_rgba(6,182,212,0.1)] space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-semibold bg-cyan-950/80 border border-cyan-400/40 text-cyan-300 mb-2">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                CHECKPOINT GATE {gateNumber} OF 3
              </div>
              <h1 className="text-2xl sm:text-3xl font-black font-display text-white tracking-tight uppercase">
                {gate.name}
              </h1>
              <p className="text-xs sm:text-sm text-cyan-400 font-mono mt-1">
                {gate.theme}
              </p>
            </div>

            <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 flex items-center justify-center shrink-0">
              <QrCode className="w-6 h-6" />
            </div>
          </div>

          <div className="p-3 rounded-xl bg-[#030712]/70 border border-cyan-500/20 flex items-center gap-3">
            <MapPin className="w-5 h-5 text-cyan-400 shrink-0" />
            <div>
              <div className="text-[10px] font-mono text-slate-400 uppercase">Physical Checkpoint Station</div>
              <div className="text-sm font-semibold text-white font-mono">{gate.checkpointLocation}</div>
            </div>
          </div>
        </div>

        {/* SCREEN 1: Check-in Form (Displayed if NOT checked in yet) */}
        {!checkinResult ? (
          <div className="rounded-2xl border border-cyan-500/30 bg-[#061224]/80 p-5 sm:p-6 space-y-5 shadow-lg">
            <div className="flex items-center gap-2 text-cyan-300 font-mono font-bold text-sm uppercase tracking-wide">
              <Radio className="w-4 h-4 text-cyan-400 animate-pulse" />
              <span>Squad Check-In Verification</span>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed font-sans">
              Welcome to <strong>{gate.name}</strong>. In accordance with the official rules of <em>The ODDyssey Protocol</em>, squads must register their physical presence at this checkpoint. The official server timestamp will be permanently logged upon submission.
            </p>

            <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-500/30 text-xs text-amber-200 flex items-start gap-2.5">
              <Lock className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <strong>Navigation Locked:</strong> Mission parameters, recovered fragments, and next gate coordinates will be transmitted only after your squad check-in is verified by the central event server.
              </div>
            </div>

            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/40 text-xs text-rose-200 flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <span>{errorMessage}</span>
              </div>
            )}

            <form onSubmit={handleCheckinSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-cyan-300 mb-1.5">
                  1. Enter 4-Digit Team ID (e.g. 0001, 0024)
                </label>
                <input
                  type="text"
                  maxLength={10}
                  placeholder="Enter 4-digit Team ID (e.g. 0001 or 1024)"
                  value={teamIdentifier}
                  onChange={(e) => setTeamIdentifier(e.target.value)}
                  className="w-full px-3 py-2.5 bg-[#030712] border border-cyan-500/30 rounded-xl text-sm text-white focus:outline-none focus:border-cyan-400 font-mono tracking-widest placeholder:tracking-normal placeholder:font-sans placeholder:text-slate-500"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-cyan-300 mb-1.5">
                  2. Or Select Squad from Registered Roster
                </label>
                <select
                  value={selectedTeamId}
                  onChange={handleSelectTeam}
                  className="w-full px-3 py-2.5 bg-[#030712] border border-cyan-500/30 rounded-xl text-sm text-white focus:outline-none focus:border-cyan-400 font-sans"
                >
                  <option value="">-- Choose your squad name --</option>
                  {teams.map((t) => (
                    <option key={t.id} value={t.id}>
                      #{String(t.team_number).padStart(4, '0')} — {t.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono text-cyan-300 mb-1.5">
                  3. Or Enter Squad Name Directly
                </label>
                <input
                  type="text"
                  placeholder="e.g. Levi Squad or Vanguard Titans"
                  value={selectedTeamName}
                  onChange={(e) => setSelectedTeamName(e.target.value)}
                  className="w-full px-3 py-2.5 bg-[#030712] border border-cyan-500/30 rounded-xl text-sm text-white focus:outline-none focus:border-cyan-400 font-sans placeholder:text-slate-500"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 active:scale-[0.99] text-white font-mono font-bold text-sm tracking-wide shadow-[0_0_20px_rgba(6,182,212,0.3)] transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>LOGGING OFFICIAL SERVER TIMESTAMP...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-4 h-4" />
                    <span>CHECK IN SQUAD &amp; UNLOCK NAVIGATION</span>
                  </>
                )}
              </button>
            </form>
          </div>
        ) : (
          /* SCREEN 2: Revealed Navigation Parameters (After Check-in) */
          <div className="space-y-5 animate-in fade-in slide-in-from-bottom-2 duration-300">
            {/* Check-In Receipt Banner */}
            <div className={`rounded-2xl border p-5 ${
              checkinResult.is_duplicate
                ? 'border-amber-500/40 bg-amber-950/30 text-amber-200'
                : 'border-emerald-500/40 bg-emerald-950/30 text-emerald-200'
            }`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 className={`w-6 h-6 shrink-0 ${checkinResult.is_duplicate ? 'text-amber-400' : 'text-emerald-400'}`} />
                  <div>
                    <div className="font-mono font-black text-sm uppercase tracking-wide">
                      {checkinResult.is_duplicate ? 'REPEAT SCAN RECORDED' : 'OFFICIAL CHECK-IN VERIFIED'}
                    </div>
                    <div className="text-xs text-slate-300 font-mono mt-0.5">
                      Squad: <strong className="text-white">{checkinResult.team_name}</strong> {checkinResult.team_number ? `(#${String(checkinResult.team_number).padStart(4, '0')})` : ''} · Gate 0{checkinResult.gate_number}
                    </div>
                  </div>
                </div>

                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-black/40 border border-current">
                  {checkinResult.status}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-3 pt-3 border-t border-white/10 text-xs font-mono">
                <div>
                  <span className="text-slate-400">Scan ID: </span>
                  <span className="text-white">{checkinResult.checkin_id}</span>
                </div>
                <div>
                  <span className="text-slate-400">Official Server Time: </span>
                  <span className="text-white">{new Date(checkinResult.official_scanned_at).toLocaleTimeString()} ({new Date(checkinResult.official_scanned_at).toISOString().substring(11, 19)} UTC)</span>
                </div>
                {checkinResult.split_time_formatted && (
                  <div className="sm:col-span-2 text-cyan-300">
                    <span className="text-slate-400">Split / Elapsed: </span>
                    <strong className="text-white">{checkinResult.split_time_formatted}</strong> ({checkinResult.split_seconds}s)
                  </div>
                )}
                {checkinResult.is_duplicate && (
                  <div className="sm:col-span-2 text-[11px] text-amber-300">
                    {checkinResult.notes}
                  </div>
                )}
              </div>
            </div>

            {/* Official Navigation System Terminal (Exact from ODDyssey Organiser.html) */}
            <div className="rounded-2xl border border-cyan-400/50 bg-[#020b18] p-5 sm:p-6 space-y-4 shadow-[0_0_30px_rgba(6,182,212,0.15)] relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500" />

              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono uppercase tracking-wider text-cyan-400 font-bold flex items-center gap-1.5">
                  <Compass className="w-3.5 h-3.5 text-cyan-300" />
                  ODDYSSEY NAVIGATION SYSTEM
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 border border-cyan-500/40 text-cyan-300">
                  SYSTEM STATUS: {checkinResult.navigation.system_status}
                </span>
              </div>

              {/* Exact Official Terminal Banner */}
              <div className="p-4 rounded-xl bg-black/80 border border-cyan-500/30 font-mono text-xs sm:text-sm text-cyan-200 space-y-2 leading-relaxed tracking-wide select-all">
                <p className="font-semibold text-white">
                  {checkinResult.navigation.raw_text}
                </p>
              </div>

              {/* Navigation Parameter Breakdown */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                <div className="p-3 rounded-xl bg-purple-950/30 border border-purple-500/30">
                  <div className="text-[10px] font-mono text-purple-300 uppercase">Fragment Status</div>
                  <div className="text-sm font-mono font-bold text-white mt-0.5">
                    {checkinResult.navigation.fragment_info}
                  </div>
                </div>

                {checkinResult.navigation.access_key && (
                  <div className="p-3 rounded-xl bg-cyan-950/30 border border-cyan-500/30">
                    <div className="text-[10px] font-mono text-cyan-300 uppercase">Access Key</div>
                    <div className="text-sm font-mono font-bold text-white mt-0.5">
                      {checkinResult.navigation.access_key}
                    </div>
                  </div>
                )}
              </div>

              {/* Next Gate Instructions */}
              <div className="p-3.5 rounded-xl bg-[#061224] border border-cyan-500/20 text-xs text-slate-200 space-y-1">
                <div className="font-mono text-[10px] text-cyan-400 uppercase font-semibold">Immediate Directive</div>
                <p className="font-sans leading-relaxed">{checkinResult.navigation.instructions}</p>
              </div>
            </div>

            {/* Check in another squad button */}
            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleResetForAnotherSquad}
                className="px-4 py-2.5 rounded-xl bg-[#061224] hover:bg-[#0b1f3b] border border-cyan-500/30 text-cyan-300 text-xs font-mono font-semibold transition-all flex items-center gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Check In Next Squad at Gate {gateNumber}</span>
              </button>
            </div>
          </div>
        )}

        {/* Physical Fallback Guarantee (Always Visible) */}
        <div className="rounded-2xl border border-slate-700 bg-[#090d1a] p-4 flex items-start gap-3">
          <Printer className="w-5 h-5 text-slate-400 shrink-0 mt-0.5" />
          <div className="text-xs text-slate-400 leading-relaxed font-sans">
            <strong className="text-slate-200">Official Printed Fallback Guarantee:</strong>{' '}
            {gate.fallbackInstructions}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-cyan-500/20 bg-[#061224]/80 py-4 px-4 text-center text-[11px] font-mono text-slate-500">
        The ODDyssey Protocol · 32 Teams → 16 Qualifiers · Physical Gate Telemetry
      </footer>
    </div>
  );
}
