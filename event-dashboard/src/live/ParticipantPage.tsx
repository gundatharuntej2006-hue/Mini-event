import { FormEvent, useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Check, Compass, Instagram, LogOut, ScanLine, Send, ShieldAlert } from 'lucide-react';
import gsap from 'gsap';
import instagramQr from '../assets/asymptotes-instagram-qr.png';
import { LiveShell, Mark } from './LiveShell';
import { clearSession, getSession, request } from './eventApi';

type State = { complete: boolean; checkpoint: number; round_started: boolean; riddle?: string; is_scanned?: boolean; attempts_used?: number; is_locked?: boolean; instagram?: string };

export function ParticipantPage() {
  const [state, setState] = useState<State | null>(null); const [answer, setAnswer] = useState(''); const [notice, setNotice] = useState(''); const [error, setError] = useState(''); const [sending, setSending] = useState(false);
  const { location } = useParams(); const navigate = useNavigate(); const reveal = useRef<HTMLDivElement>(null);
  const load = async () => { try { setState(await request<State>('/participant/state')); } catch (e) { setError(e instanceof Error ? e.message : 'Unable to load event.'); } };
  useEffect(() => { if (getSession()?.role !== 'PARTICIPANT') { navigate('/', { replace: true }); return; } load(); }, []);
  useEffect(() => { if (!location || !getSession()) return; (async () => { try { const data = await request<State>('/participant/scan', 'POST', { location: Number(location) }); setState(data); setNotice('Location verified. Enter the envelope answer exactly.'); } catch (e) { setError(e instanceof Error ? e.message : 'Scan failed.'); } finally { navigate('/play', { replace: true }); } })(); }, [location]);
  useEffect(() => { if (!state?.riddle || state.checkpoint === 1 || !reveal.current || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return; gsap.fromTo(reveal.current, { autoAlpha: 0, y: 18 }, { autoAlpha: 1, y: 0, duration: .45, ease: 'power3.out' }); }, [state?.checkpoint, state?.riddle]);
  async function submit(e: FormEvent) { e.preventDefault(); if (!answer || sending) return; setSending(true); setError(''); try { const result = await request<{ correct: boolean; state: State }>('/participant/answer', 'POST', { answer }); setState(result.state); setNotice(result.correct ? (result.state.complete ? 'Your time has been recorded.' : 'Correct. Your next clue is ready.') : 'Not accepted. Check capitals, spaces, and hyphens.'); if (result.correct) setAnswer(''); } catch (err) { setError(err instanceof Error ? err.message : 'Unable to submit.'); } finally { setSending(false); } }
  const logout = () => { clearSession(); navigate('/'); };
  return <LiveShell><main className="mobile-page"><header className="topbar live-reveal"><Mark /><button aria-label="Sign out" onClick={logout}><LogOut size={18}/></button></header>
    {!state ? <div className="load-card live-reveal">Loading your event...</div> : state.complete ? <section className="finish-card live-reveal"><div className="finish-icon"><Check size={30}/></div><div className="eyebrow">ROUND 01 COMPLETE</div><h1>Your time is <span>recorded.</span></h1><p>Please take a break and wait for results on Instagram.</p><img className="instagram-qr" src={instagramQr} alt="Instagram QR for ASYMPTOTES_BMSIT"/><div className="insta-handle"><Instagram size={20}/>@ASYMPTOTES_BMSIT</div></section> : <>
      <section className="progress-line live-reveal"><span className="active">0{state.checkpoint}</span><i /><span>03</span><small>MINI ROUND {state.checkpoint}</small></section>
      {!state.round_started ? <section className="event-card live-reveal"><Compass size={28}/><h2>Stand by at the start point.</h2><p>The event will unlock when a super admin starts the round.</p></section> : state.is_locked ? <section className="event-card danger live-reveal"><ShieldAlert size={28}/><h2>Checkpoint paused</h2><p>Please speak to the nearest event volunteer.</p></section> : !state.is_scanned ? <section className="event-card live-reveal" ref={reveal}><ScanLine size={30}/><div className="eyebrow">LOCATION CHECK</div><h1>{state.checkpoint === 1 ? 'Use your physical first clue.' : 'Your next clue.'}</h1>{state.checkpoint > 1 && <p className="riddle">{state.riddle}</p>}<p className="subnote">When you arrive, scan only the QR displayed at that location.</p></section> : <section className="answer-card live-reveal"><div className="eyebrow"><Check size={14}/> LOCATION VERIFIED</div><h1>Enter the final answer.</h1><p>It must match exactly: capitals, spaces, and hyphens matter.</p><form onSubmit={submit}><input value={answer} onChange={e => setAnswer(e.target.value)} autoCorrect="off" autoCapitalize="off" placeholder="TYPE ANSWER" autoFocus/><button className="primary-button" disabled={!answer || sending}>{sending ? 'Checking...' : <>Submit <Send size={17}/></>}</button></form></section>}
      {(notice || error) && <div className={`toast live-reveal ${error ? 'toast-error' : ''}`}>{error || notice}</div>}
    </>}</main></LiveShell>;
}
