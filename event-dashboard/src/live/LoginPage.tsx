import { FormEvent, useState } from 'react';
import { KeyRound, LockKeyhole, ArrowRight, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Mark, LiveShell } from './LiveShell';
import { signIn } from './eventApi';

export function LoginPage() {
  const [loginId, setLoginId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setLoading(true);
    try {
      const session = await signIn(loginId, password);
      navigate(session.role === 'PARTICIPANT' ? '/play' : session.role === 'ADMIN' ? '/station' : '/control', { replace: true });
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to sign in.'); } finally { setLoading(false); }
  }
  return <LiveShell><main className="auth-page"><Mark /><section className="auth-card live-reveal">
    <div className="eyebrow"><KeyRound size={14} /> ROUND 01 · TREASURE HUNT</div>
    <h1>Find the <span>unseen.</span></h1><p>Use the event ID and password provided to your team or event staff.</p>
    <form onSubmit={submit}>
      <label>Event ID<input autoCapitalize="characters" autoCorrect="off" value={loginId} onChange={e => setLoginId(e.target.value.toUpperCase())} placeholder="TEAM1001" required /></label>
      <label>Password<div className="input-icon"><LockKeyhole size={17}/><input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter password" required /></div></label>
      {error && <div className="form-error"><AlertCircle size={16}/>{error}</div>}
      <button className="primary-button" disabled={loading}>{loading ? 'Signing in...' : <>Enter event <ArrowRight size={18}/></>}</button>
    </form>
  </section><p className="auth-foot live-reveal">BMSIT · Bengaluru · Keep your login within your team.</p></main></LiveShell>;
}
