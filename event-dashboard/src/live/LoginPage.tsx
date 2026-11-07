import { FormEvent, useEffect, useState } from 'react';
import { AlertCircle, ArrowRight, Eye, EyeOff, LockKeyhole, Mail, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { AxiomNightBackdrop } from '../axiom/AxiomPages';
import earthTexture from '../assets/earth-blue-marble-nasa.jpg';
import earthNightLights from '../assets/earth-night-lights-nasa.jpg';
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
    <div className="ax-login-home-underlay" aria-hidden="true">
      <AxiomNightBackdrop/>
      <div className="ax-earth-wrap"><div className="ax-earth-globe"><div className="ax-earth-map" style={{ backgroundImage: `url(${earthTexture})` }}/><div className="ax-earth-lights" style={{ backgroundImage: `url(${earthNightLights})` }}/></div></div>
      <div className="ax-login-underlay-title">LOOK UP.<br/>THEN BUILD<br/>FORWARD.</div>
    </div>
    <div className="ax-login-grain" aria-hidden="true"/>
    <div className="ax-glass-weather" aria-hidden="true"/>
    <section className="ax-login-story" aria-label="Project Axiom introduction">
      <AxiomLoginMark/>
      <p className="ax-login-overline">MEMBER WORKSPACE</p>
      <h1>Start with a<br/><span className="ax-fluid-word">question.</span><br/>Build what<br/>comes next.</h1>
    </section>

    <section className="ax-login-form-wrap" aria-label="Secure sign in">
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
          <div className="ax-login-status"><span><ShieldCheck size={14}/> Authorised members only</span></div>
          <button className="ax-login-submit" disabled={loading}>{loading ? 'Opening workspace...' : <>Sign in to Axiom <ArrowRight size={18}/></>}</button>
        </form>
      </div>
      <button className="ax-login-back" type="button" onClick={() => navigate('/')}>← Back to Club Asymptotes</button>
    </section>
  </main></LiveShell>;
}
