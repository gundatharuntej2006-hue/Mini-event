import { FormEvent, useState } from 'react';
import { KeyRound, LockKeyhole, ArrowRight, AlertCircle, Atom } from 'lucide-react';
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
      if ('redirect' in session) {
        navigate('/results', { replace: true, state: { message: session.message } });
        return;
      }
      if (session.experience === 'axiom') navigate(session.role === 'SUPER_ADMIN' ? '/axiom/control' : '/axiom', { replace: true });
      else navigate(session.role === 'PARTICIPANT' ? '/play' : session.role === 'ADMIN' ? '/station' : '/control', { replace: true });
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to sign in.'); } finally { setLoading(false); }
  }
  return <LiveShell><main className="auth-page ax-login"><Mark /><section className="auth-card live-reveal">
    <div className="ax-login-symbol"><Atom size={30}/></div><div className="eyebrow"><KeyRound size={14} /> EVENTS AT ASYMPTOTES · SECURE ACCESS</div>
    <h1>Enter your <span>workspace.</span></h1><p>Use your verified BMSIT email and the initial credential issued to you. Club Council may continue with its secure ID.</p>
    <form onSubmit={submit}>
      <label>College email or Council ID<input autoCapitalize="none" autoCorrect="off" value={loginId} onChange={e => setLoginId(e.target.value)} placeholder="name@bmsit.in" required /></label>
      <label>Password<div className="input-icon"><LockKeyhole size={17}/><input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter password" required /></div></label>
      {error && <div className="form-error"><AlertCircle size={16}/>{error}</div>}
      <button className="primary-button" disabled={loading}>{loading ? 'Opening workspace...' : <>Continue securely <ArrowRight size={18}/></>}</button>
    </form>
  </section><button className="text-link live-reveal" type="button" onClick={() => navigate('/')}>Back to Events at Asymptotes</button><p className="auth-foot live-reveal">Project Axiom · Individual credentials · Do not share access.</p></main></LiveShell>;
}
