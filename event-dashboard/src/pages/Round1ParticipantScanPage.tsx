import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Compass,
  MapPin,
  Lock,
  CheckCircle2,
  AlertTriangle,
  Send,
  LogOut,
  RefreshCw,
  Trophy,
  QrCode,
  ShieldAlert,
} from 'lucide-react';
import { backendApiService } from '../services/backendApiService';
import { ParticipantCurrentState } from '../types/round1';

export function Round1ParticipantScanPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Session state
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('r1_participant_token'));
  const [storedTeamId, setStoredTeamId] = useState<string | null>(() => localStorage.getItem('r1_team_id'));
  const [inputTeamId, setInputTeamId] = useState('');
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Participant checkpoint state
  const [participantState, setParticipantState] = useState<ParticipantCurrentState | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Scan & Answer submission state
  const [scanMessage, setScanMessage] = useState<{ isSuccess: boolean; text: string } | null>(null);
  const [isProcessingScan, setIsProcessingScan] = useState(false);
  const scanInProgressRef = useRef(false);
  const [answerInput, setAnswerInput] = useState('');
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [answerFeedback, setAnswerFeedback] = useState<{ isCorrect: boolean; text: string } | null>(null);

  // Fetch current participant state
  const loadParticipantState = useCallback(async (sessionToken: string) => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const res = await backendApiService.getParticipantCurrentState(sessionToken);
      if (res.data) {
        setParticipantState(res.data);
      } else {
        setFetchError('Unable to load participant status from server.');
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Session expired or invalid.';
      setFetchError(detail);
      if (err.response?.status === 401 || err.response?.status === 404) {
        // Clear invalid session
        localStorage.removeItem('r1_participant_token');
        localStorage.removeItem('r1_team_id');
        setToken(null);
        setStoredTeamId(null);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Handle Initial Load
  useEffect(() => {
    if (token) {
      loadParticipantState(token);
    }
  }, [token, loadParticipantState]);

  // Handle URL Location Scan Param (?location=X)
  const processLocationParam = useCallback(async (sessionToken: string, locParam: string) => {
    const locNum = parseInt(locParam, 10);
    if (isNaN(locNum)) return;
    if (scanInProgressRef.current) return;

    scanInProgressRef.current = true;
    setIsProcessingScan(true);
    setScanMessage(null);
    try {
      const res = await backendApiService.submitParticipantLocationScan(sessionToken, locNum);
      if (res.data) {
        if (res.data.is_correct_location) {
          setScanMessage({
            isSuccess: true,
            text: `Station verified! You have arrived at Location ${locNum}. Solve the checkpoint challenge below.`,
          });
        } else {
          setScanMessage({
            isSuccess: false,
            text: res.data.message || 'This is not your current assigned location.',
          });
        }
        // Refresh full state
        await loadParticipantState(sessionToken);
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'This is not your current assigned location.';
      setScanMessage({
        isSuccess: false,
        text: detail,
      });
      await loadParticipantState(sessionToken);
    } finally {
      scanInProgressRef.current = false;
      setIsProcessingScan(false);
      // Clean query parameter from URL so refresh doesn't re-trigger
      searchParams.delete('location');
      setSearchParams(searchParams, { replace: true });
    }
  }, [loadParticipantState, searchParams, setSearchParams]);

  useEffect(() => {
    const locParam = searchParams.get('location');
    if (token && locParam && !isProcessingScan && !scanInProgressRef.current) {
      processLocationParam(token, locParam);
    }
  }, [token, searchParams, isProcessingScan, processLocationParam]);

  // Authentication submission
  const handleAuthenticate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputTeamId.trim()) return;

    setIsAuthenticating(true);
    setAuthError(null);
    try {
      const res = await backendApiService.createParticipantSession(inputTeamId.trim());
      if (res.data && res.data.session_token) {
        localStorage.setItem('r1_participant_token', res.data.session_token);
        localStorage.setItem('r1_team_id', res.data.team_identifier);
        setToken(res.data.session_token);
        setStoredTeamId(res.data.team_identifier);

        // If there was no pending location param, load state; if there is, the useEffect will trigger processLocationParam
        const locParam = searchParams.get('location');
        if (!locParam) {
          loadParticipantState(res.data.session_token);
        }
      }
    } catch (err: any) {
      setAuthError(err.response?.data?.detail || 'Invalid Team ID. Please enter an active 4-digit Team ID (e.g. 1001-1032).');
    } finally {
      setIsAuthenticating(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('r1_participant_token');
    localStorage.removeItem('r1_team_id');
    setToken(null);
    setStoredTeamId(null);
    setParticipantState(null);
    setScanMessage(null);
    setAnswerFeedback(null);
  };

  // Submit Checkpoint Answer
  const handleSubmitAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !answerInput.trim() || isSubmittingAnswer) return;

    setIsSubmittingAnswer(true);
    setAnswerFeedback(null);
    try {
      const res = await backendApiService.submitParticipantAnswer(token, answerInput.trim());
      if (res.data) {
        if (res.data.is_correct) {
          setAnswerFeedback({
            isCorrect: true,
            text: res.data.message || 'CORRECT! Proceeding to next checkpoint.',
          });
          setAnswerInput('');
        } else {
          setAnswerFeedback({
            isCorrect: false,
            text: res.data.is_locked_out
              ? 'Maximum attempts reached. Please contact the organizer.'
              : `Incorrect answer. ${res.data.attempts_remaining} attempts remaining.`,
          });
        }
        await loadParticipantState(token);
      }
    } catch (err: any) {
      setAnswerFeedback({
        isCorrect: false,
        text: err.response?.data?.detail || 'Submission error. Please retry.',
      });
      await loadParticipantState(token);
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  // 1. Participant Authentication View (if not logged in)
  if (!token) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center px-4 py-8 font-sans selection:bg-cyan-500 selection:text-black">
        <div className="w-full max-w-md bg-slate-900 border border-cyan-500/30 rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-500" />

          {/* Header */}
          <div className="text-center space-y-2 mb-8">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-500/40 text-cyan-400 text-xs font-mono tracking-wider uppercase">
              <Compass className="w-3.5 h-3.5 animate-spin-slow" />
              <span>ROUND 1 · ODDYSSEY PROTOCOL</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black font-display tracking-tight text-white uppercase">
              SQUAD CHECK-IN
            </h1>
            <p className="text-xs text-slate-400 font-mono">
              Enter your official 4-digit Team ID to unlock checkpoint navigation and station verification.
            </p>
          </div>

          {/* Auth Form */}
          <form onSubmit={handleAuthenticate} className="space-y-5">
            <div>
              <label htmlFor="teamIdInput" className="block text-xs font-mono text-cyan-300 uppercase tracking-wider mb-2">
                4-Digit Team ID
              </label>
              <input
                id="teamIdInput"
                type="text"
                maxLength={6}
                value={inputTeamId}
                onChange={(e) => setInputTeamId(e.target.value.trim())}
                placeholder="e.g. 1014"
                className="w-full text-center text-2xl font-mono font-bold tracking-widest bg-slate-950 border border-slate-700 focus:border-cyan-400 text-white rounded-2xl py-3 px-4 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all placeholder:text-slate-600"
                autoFocus
              />
            </div>

            {authError && (
              <div className="p-3 rounded-xl bg-red-950/60 border border-red-500/50 text-red-200 text-xs font-mono flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <span>{authError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={isAuthenticating || !inputTeamId.trim()}
              className="w-full py-3.5 px-4 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-white font-mono font-bold text-sm tracking-wider uppercase transition-all shadow-[0_0_20px_rgba(6,182,212,0.3)] flex items-center justify-center gap-2"
            >
              {isAuthenticating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>AUTHENTICATING...</span>
                </>
              ) : (
                <span>ENTER ODDYSSEY</span>
              )}
            </button>
          </form>

          {/* Footer Notice */}
          <div className="mt-8 pt-4 border-t border-slate-800 text-center text-[11px] font-mono text-slate-500">
            EVENT HQ TOURNAMENT SYSTEM · ZERO LOCAL DEVICE CLOCK TRUST
          </div>
        </div>
      </div>
    );
  }

  // 2. Logged In Participant View
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-black">
      {/* Top Mobile Bar */}
      <header className="sticky top-0 z-40 bg-slate-900/90 backdrop-blur-md border-b border-cyan-500/30 px-4 py-3">
        <div className="max-w-md mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-cyan-950 border border-cyan-500/50 flex items-center justify-center text-cyan-400">
              <Compass className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest leading-none">
                ODDYSSEY PROTOCOL
              </div>
              <div className="text-sm font-bold text-white font-mono">
                TEAM {participantState?.team_identifier || storedTeamId}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => token && loadParticipantState(token)}
              disabled={isLoading}
              title="Refresh status"
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>

            <button
              onClick={handleLogout}
              title="Switch Team"
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-rose-400 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-md w-full mx-auto px-4 py-6 space-y-4">
        {fetchError && (
          <div className="p-3.5 rounded-2xl bg-rose-950/60 border border-rose-500/50 text-rose-200 text-xs font-mono flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{fetchError}</span>
          </div>
        )}

        {/* Checkpoint Progress Stepper */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-3 flex items-center justify-between text-xs font-mono">
          {[1, 2, 3].map((cpNum) => {
            const currentCp = participantState?.current_checkpoint || 1;
            const isCompleted = participantState?.is_complete || currentCp > cpNum;
            const isCurrent = currentCp === cpNum && !participantState?.is_complete;

            return (
              <div key={cpNum} className="flex items-center gap-2">
                <div
                  className={`w-7 h-7 rounded-xl flex items-center justify-center font-bold text-xs transition-colors ${
                    isCompleted
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                      : isCurrent
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400'
                      : 'bg-slate-800 text-slate-500 border border-slate-700'
                  }`}
                >
                  {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : `R1.${cpNum}`}
                </div>
                <span
                  className={`text-[11px] hidden sm:inline ${
                    isCurrent ? 'text-white font-bold' : isCompleted ? 'text-emerald-400' : 'text-slate-500'
                  }`}
                >
                  CP {cpNum}
                </span>
                {cpNum < 3 && <div className="w-4 sm:w-8 h-px bg-slate-800 mx-1" />}
              </div>
            );
          })}
        </div>

        {/* Scan Feedback Banner */}
        {scanMessage && (
          <div
            className={`p-4 rounded-2xl border text-xs font-mono flex items-start gap-3 transition-all ${
              scanMessage.isSuccess
                ? 'bg-emerald-950/50 border-emerald-500/50 text-emerald-200'
                : 'bg-rose-950/60 border-rose-500/50 text-rose-200'
            }`}
          >
            {scanMessage.isSuccess ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <strong className="block font-bold mb-0.5">
                {scanMessage.isSuccess ? 'STATION SCAN VERIFIED' : 'SCAN REJECTED'}
              </strong>
              <span>{scanMessage.text}</span>
            </div>
          </div>
        )}

        {/* Global Round Inactive State */}
        {participantState && !participantState.is_round_active && !participantState.is_complete && (
          <div className="p-5 rounded-2xl bg-amber-950/40 border border-amber-500/40 text-amber-200 space-y-2">
            <div className="flex items-center gap-2 font-mono font-bold text-amber-400">
              <AlertTriangle className="w-5 h-5" />
              <span>ROUND 1 HAS NOT STARTED</span>
            </div>
            <p className="text-xs text-amber-200/90 leading-relaxed font-mono">
              The organizer console has not yet triggered the official Round 1 start timer. Please wait at the base point until the starting signal is given.
            </p>
          </div>
        )}

        {/* Completed State */}
        {participantState?.is_complete ? (
          <div className="bg-gradient-to-b from-slate-900 to-emerald-950/30 border-2 border-emerald-500/50 rounded-3xl p-6 sm:p-8 text-center space-y-5 shadow-2xl">
            <div className="w-16 h-16 rounded-3xl bg-emerald-500/20 border border-emerald-400 flex items-center justify-center mx-auto text-emerald-400">
              <Trophy className="w-8 h-8" />
            </div>

            <div className="space-y-1">
              <div className="text-xs font-mono uppercase tracking-widest text-emerald-400 font-bold">
                PROTOCOL FINISHED
              </div>
              <h2 className="text-2xl sm:text-3xl font-black font-display text-white tracking-tight">
                ROUND 1 COMPLETE
              </h2>
              <div className="text-lg font-bold font-mono text-cyan-300">
                RETURN TO BASE POINT
              </div>
            </div>

            <p className="text-xs text-slate-300 font-mono leading-relaxed bg-slate-900/80 p-4 rounded-2xl border border-slate-800">
              All 3 checkpoints successfully verified and completed! Report to the central tournament organizer desk immediately to verify official server stop timestamp.
            </p>
          </div>
        ) : participantState?.is_locked ? (
          /* Locked Out State */
          <div className="bg-rose-950/30 border-2 border-rose-500/50 rounded-3xl p-6 text-center space-y-4 shadow-xl">
            <div className="w-14 h-14 rounded-2xl bg-rose-500/20 border border-rose-400 flex items-center justify-center mx-auto text-rose-400">
              <Lock className="w-7 h-7" />
            </div>

            <div className="space-y-1">
              <div className="text-xs font-mono uppercase tracking-widest text-rose-400 font-bold">
                LOCKOUT PROTOCOL ENGAGED
              </div>
              <h2 className="text-xl font-black font-display text-white">
                MAXIMUM ATTEMPTS REACHED
              </h2>
            </div>

            <p className="text-xs text-rose-200 font-mono leading-relaxed bg-black/40 p-3 rounded-xl border border-rose-500/30">
              Maximum attempts reached. Please contact the organizer.
            </p>
          </div>
        ) : (
          /* Active Checkpoint View */
          <>
            {/* Card 1: Checkpoint Location Clue */}
            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 space-y-4 shadow-xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-cyan-400" />
                  <span className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                    CHECKPOINT {participantState?.current_checkpoint || 1} TARGET
                  </span>
                </div>
                <div className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-cyan-950 border border-cyan-500/40 text-cyan-300">
                  {participantState?.qr_scanned ? 'AT STATION' : 'EN ROUTE'}
                </div>
              </div>

              {/* Riddle & Location Clue */}
              <div className="space-y-3">
                <div className="text-sm font-semibold text-slate-200">
                  {participantState?.location_name || 'Assigned Station'}
                </div>

                <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 text-xs font-mono text-cyan-200/90 leading-relaxed">
                  <strong className="block text-slate-400 uppercase text-[10px] tracking-wider mb-1">
                    Station Riddle:
                  </strong>
                  {participantState?.location_riddle || 'Navigate to your assigned station.'}
                </div>

                {participantState?.location_target && (
                  <div className="text-[11px] font-mono text-slate-400 px-1">
                    <span className="text-slate-500">Target Hint: </span>
                    {participantState.location_target}
                  </div>
                )}
              </div>
            </div>

            {/* Card 2: Question & Scan Status */}
            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 space-y-4 shadow-xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <QrCode className="w-4 h-4 text-blue-400" />
                  <span className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                    STATION VERIFICATION
                  </span>
                </div>
                <div
                  className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-md ${
                    participantState?.qr_scanned
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/40'
                      : 'bg-amber-950 text-amber-300 border border-amber-500/40'
                  }`}
                >
                  {participantState?.qr_scanned ? 'UNLOCKED' : 'AWAITING SCAN'}
                </div>
              </div>

              {!participantState?.qr_scanned ? (
                /* Unscanned State */
                <div className="py-6 text-center space-y-3">
                  <div className="w-12 h-12 rounded-2xl bg-cyan-950/60 border border-cyan-500/30 flex items-center justify-center mx-auto text-cyan-400">
                    <QrCode className="w-6 h-6 animate-pulse" />
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-sm font-bold text-white font-mono uppercase">
                      SCAN PHYSICAL QR AT LOCATION
                    </h3>
                    <p className="text-xs text-slate-400 font-mono max-w-xs mx-auto">
                      Scan the physical QR badge mounted at this location with your smartphone camera to unlock the envelope question challenge.
                    </p>
                  </div>
                </div>
              ) : (
                /* Scanned State: Answer Submission Form */
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-400">Challenge Status:</span>
                    <span
                      className={`font-bold ${
                        (participantState?.attempts_remaining ?? 3) <= 1 ? 'text-rose-400' : 'text-cyan-300'
                      }`}
                    >
                      ATTEMPTS REMAINING: {participantState?.attempts_remaining ?? 3} / 3
                    </span>
                  </div>

                  <form onSubmit={handleSubmitAnswer} className="space-y-3">
                    <div>
                      <label htmlFor="answerInput" className="block text-[11px] font-mono text-slate-400 uppercase mb-1.5">
                        Submit Envelope Answer:
                      </label>
                      <input
                        id="answerInput"
                        type="text"
                        value={answerInput}
                        onChange={(e) => setAnswerInput(e.target.value)}
                        placeholder="ENTER YOUR ANSWER"
                        disabled={isSubmittingAnswer || participantState?.is_locked}
                        className="w-full text-center text-lg font-mono font-bold tracking-wider bg-slate-950 border border-slate-700 focus:border-cyan-400 text-white rounded-xl py-2.5 px-3 focus:outline-none focus:ring-1 focus:ring-cyan-500/30 uppercase placeholder:text-slate-600"
                        autoFocus
                      />
                    </div>

                    {answerFeedback && (
                      <div
                        className={`p-3 rounded-xl border text-xs font-mono flex items-start gap-2 ${
                          answerFeedback.isCorrect
                            ? 'bg-emerald-950/60 border-emerald-500/50 text-emerald-200'
                            : 'bg-rose-950/60 border-rose-500/50 text-rose-200'
                        }`}
                      >
                        {answerFeedback.isCorrect ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                        )}
                        <span>{answerFeedback.text}</span>
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={isSubmittingAnswer || !answerInput.trim() || participantState?.is_locked}
                      className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 disabled:opacity-40 text-white font-mono font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-lg"
                    >
                      {isSubmittingAnswer ? (
                        <>
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          <span>VERIFYING ANSWER...</span>
                        </>
                      ) : (
                        <>
                          <Send className="w-4 h-4" />
                          <span>SUBMIT ANSWER</span>
                        </>
                      )}
                    </button>
                  </form>
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
