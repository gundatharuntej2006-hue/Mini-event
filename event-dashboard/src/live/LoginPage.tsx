import { FormEvent, useEffect, useState } from 'react';
import { AlertCircle, ArrowRight, Eye, EyeOff, KeyRound, LockKeyhole, Mail, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { LiveShell } from './LiveShell';
import { signIn, warmBackend } from './eventApi';

function AxiomLoginMark() {
  return <div className="axiom-login-mark" aria-label="Project Axiom">
    <span className="ax-glyph" aria-hidden="true"><img src="/axiom/axiom-foundation.png" alt=""/><i className="ax-conclusion-orbit"><b/></i></span>
    <span><b>PROJECT AXIOM</b><small>AN ASYMPTOTES INITIATIVE</small></span>
  </div>;
}

export function LoginPage() {
  const [loginId, setLoginId] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => { void warmBackend(); }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(''); setLoading(true);
    try {
      const session = await signIn(loginId, password);
      if ('redirect' in session) {
        navigate('/results', { replace: true, state: { message: session.message } });
        return;
      }
      if (session.experience === 'axiom') navigate(session.role === 'SUPER_ADMIN' ? '/axiom/control' : '/axiom', { replace: true });
      else navigate(session.role === 'PARTICIPANT' ? '/play' : session.role === 'ADMIN' ? '/station' : '/control', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to sign in.');
    } finally { setLoading(false); }
  }

  return <LiveShell><main className="auth-page ax-login ax-login-immersive">
    <div className="ax-login-home-underlay" aria-hidden="true"><div className="ax-login-underlay-title">LOOK UP.<br/>THEN BUILD<br/>FORWARD.</div><div className="ax-login-underlay-earth"/></div>
    <div className="ax-login-grain" aria-hidden="true"/>
    <div className="ax-glass-weather" aria-hidden="true"/>
    <section className="ax-login-story live-reveal" aria-label="Project Axiom introduction">
      <AxiomLoginMark/>
      <p className="ax-login-overline">MATHEMATICS · RESEARCH · CREATION</p>
      <h1>Start with a<br/><span className="ax-fluid-word">question.</span><br/>Build what<br/>comes next.</h1>
      <p className="ax-login-intro">A private space for Club Asymptotes members to turn considered questions into research, products and work that lasts.</p>
      <div className="ax-login-principle"><i/> Every discovery begins somewhere.</div>
      <svg className="ax-login-geometry" viewBox="0 0 560 190" fill="none" aria-hidden="true">
        <path d="M10 147H550" stroke="currentColor" opacity=".14"/>
        <path className="ax-geo-flow" d="M18 135C99 135 103 30 190 30S289 147 365 147 456 42 545 42" stroke="currentColor" strokeWidth="1.1" opacity=".58"/>
        <path d="M145 148 232 23 318 148M185 148 232 80 280 148" stroke="currentColor" strokeWidth="1.1" opacity=".44"/>
        <circle cx="232" cy="23" r="3.5" fill="currentColor"/><circle cx="365" cy="147" r="3" fill="currentColor"/>
      </svg>
      <div className="ax-login-meta"><span>CLUB ASYMPTOTES</span><span>BMSIT</span><span>EST. BY CURIOSITY</span></div>
    </section>

    <section className="ax-login-form-wrap live-reveal" aria-label="Secure sign in">
      <div className="ax-login-form-card">
        <div className="ax-login-card-kicker"><span>MEMBER WORKSPACE</span><span><i/> SECURE ACCESS</span></div>
        <h2>Welcome back<span>.</span></h2>
        <p>Sign in to continue your work, explore projects and keep building.</p>
        <form onSubmit={submit}>
          <label>College email or Council ID
            <span className="ax-login-input"><input autoCapitalize="none" autoCorrect="off" value={loginId} onChange={event => setLoginId(event.target.value)} placeholder="name@bmsit.in" required/><Mail size={17}/></span>
          </label>
          <label>Password
            <span className="ax-login-input"><input type={showPassword ? 'text' : 'password'} value={password} onChange={event => setPassword(event.target.value)} placeholder="Enter password" required/><LockKeyhole size={17}/><button type="button" onClick={() => setShowPassword(value => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeOff size={16}/> : <Eye size={16}/>}</button></span>
          </label>
          {error && <div className="form-error"><AlertCircle size={16}/>{error}</div>}
          <div className="ax-login-status"><span><ShieldCheck size={14}/> Authorised members only</span><span>Individual access</span></div>
          <button className="ax-login-submit" disabled={loading}>{loading ? 'Opening workspace...' : <>Sign in to Axiom <ArrowRight size={18}/></>}</button>
        </form>
        <p className="ax-login-help"><KeyRound size={14}/> Use your allocated college email (or Council ID) and personal password.</p>
      </div>
      <button className="ax-login-back" type="button" onClick={() => navigate('/')}>← Back to Club Asymptotes</button>
      <p className="ax-login-foot">PROJECT AXIOM · INDIVIDUAL CREDENTIALS · DO NOT SHARE ACCESS</p>
    </section>
  </main></LiveShell>;
}
