import { type FormEvent, useEffect, useMemo, useState } from 'react';
import {
  ArrowRight, Atom, BookOpen, CalendarClock, Check, ChevronRight,
  CircleDot, Clock3, FileText, FlaskConical, History, LogOut, Orbit,
  ShieldCheck, Sparkles, Users, X, LockKeyhole,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { clearSession, getSession, request } from '../live/eventApi';
import axiomVisual from '../assets/project-axiom-key-visual.png';

type Deadlines = { mentor_decision: string; statement: string; preference: string };
type Statement = {
  title: string; domain: string; project_track: 'RESEARCH' | 'PRODUCT'; problem_statement: string; project_context: string;
  helpful_skills: string; status: 'DRAFT' | 'SUBMITTED'; submitted_at: string | null;
};
type AxiomMe = {
  display_name: string; college_email?: string; is_super_admin?: boolean;
  roster_type?: 'MENTOR_CANDIDATE' | 'MEMBER';
  role_choice?: 'PENDING' | 'MENTOR' | 'PARTICIPANT' | 'OPTED_OUT';
  statement?: Statement | null; deadlines: Deadlines;
};
type ControlOverview = {
  total: number; mentor_candidates: number; members: number; submitted_statements: number;
  choices: Record<string, number>;
  people: { name: string; email: string; roster_type: string; role_choice: string }[];
};

const formatDeadline = (value: string) => new Intl.DateTimeFormat('en-IN', {
  day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', timeZone: 'Asia/Kolkata',
}).format(new Date(value));

function AxiomBackdrop() {
  return <div className="ax-backdrop" aria-hidden="true"><i/><i/><i/><span>∑</span><span>π</span><span>∞</span></div>;
}

function AxiomLogo() {
  return <div className="ax-logo"><span><Atom size={19}/></span><div><b>EVENTS AT ASYMPTOTES</b><small>MATHEMATICS · BMSIT</small></div></div>;
}

function AxiomHeader({ compact = false }: { compact?: boolean }) {
  const navigate = useNavigate();
  return <header className={`ax-header ${compact ? 'compact' : ''}`}><button className="ax-brand-button" onClick={() => navigate('/')}><AxiomLogo/></button><nav><button onClick={() => navigate('/past-events')}><History size={15}/> Past events</button>{getSession() && <button onClick={() => { clearSession(); navigate('/login'); }}><LogOut size={15}/> Sign out</button>}</nav></header>;
}

function PasswordPanel() {
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function changePassword(event: FormEvent) {
    event.preventDefault();
    setError(''); setMessage('');
    if (newPassword !== confirmation) { setError('The two new passwords do not match.'); return; }
    setBusy(true);
    try {
      await request('/axiom/password', 'POST', {
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirmation: confirmation,
      });
      setMessage('Password changed. Sign in again using your new password.');
      setTimeout(() => { clearSession(); navigate('/login', { replace: true }); }, 1200);
    } catch (item) { setError(item instanceof Error ? item.message : 'Could not change the password.'); }
    finally { setBusy(false); }
  }

  return <section className="ax-password-panel">
    <div className="ax-section-title"><div><span>SECURITY</span><h2>Make this account yours.</h2></div><p>Your new password replaces the initial phone-number credential and becomes the only valid password for future logins.</p></div>
    <form onSubmit={changePassword}>
      <label>Current password<input type="password" autoComplete="current-password" value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} required/></label>
      <label>New password<input type="password" autoComplete="new-password" minLength={8} maxLength={72} value={newPassword} onChange={event => setNewPassword(event.target.value)} required/></label>
      <label>Confirm new password<input type="password" autoComplete="new-password" minLength={8} maxLength={72} value={confirmation} onChange={event => setConfirmation(event.target.value)} required/></label>
      <button className="ax-primary compact" disabled={busy}><LockKeyhole size={16}/>{busy ? 'Changing…' : 'Change password'}</button>
    </form>
    <small>Use at least eight characters. Passwords are stored only as secure hashes.</small>
    {error && <div className="ax-alert"><X size={16}/>{error}</div>}
    {message && <div className="ax-password-success"><Check size={16}/>{message}</div>}
  </section>;
}

export function AxiomLandingPage() {
  const navigate = useNavigate();
  return <main className="ax-site"><AxiomBackdrop/><AxiomHeader/>
    <section className="ax-hero">
      <div className="ax-hero-copy">
        <div className="ax-kicker"><Sparkles size={14}/> A NEW INTERNAL BUILD CYCLE</div>
        <h1>Ideas need a place to <em>converge.</em></h1>
        <p>Project Axiom is an internal programme for Asymptotes’ core members. Every small team chooses one path—conduct useful research or build a practical product—with one shared purpose: making the club better.</p>
        <div className="ax-hero-actions"><button className="ax-primary" onClick={() => navigate('/login')}>Enter Project Axiom <ArrowRight size={18}/></button><button className="ax-secondary" onClick={() => navigate('/past-events')}>Explore our past work</button></div>
      </div>
      <div className="ax-orbit-stage" aria-label="Project Axiom matching model">
        <img className="ax-key-visual" src={axiomVisual} alt="Abstract Project Axiom research system"/>
        <div className="ax-orbit-ring ring-a"/><div className="ax-orbit-ring ring-b"/>
        <div className="ax-orbit-core"><Orbit size={30}/><b>AXIOM</b><small>BUILD · TEST · LEARN</small></div>
        <div className="ax-node node-one"><Users size={17}/><span>People</span></div>
        <div className="ax-node node-two"><FileText size={17}/><span>Problems</span></div>
        <div className="ax-node node-three"><FlaskConical size={17}/><span>Projects</span></div>
      </div>
    </section>
    <section className="ax-manifesto">
      <div><span>01 · CHOOSE</span><h2>One project. One clear path.</h2><p>Each proposal is either research or product-based, with a practical benefit for Club Asymptotes.</p></div>
      <div><span>02 · COLLABORATE</span><h2>Core members work in small teams.</h2><p>Members choose with intent, explain their contribution, and work closely with an assigned mentor.</p></div>
      <div><span>03 · IMPROVE</span><h2>Everything returns value to the club.</h2><p>New knowledge, internal tools, better systems or stronger event experiences—presented at the semester showcase.</p></div>
    </section>
    <section className="ax-window"><div><div className="ax-kicker"><CalendarClock size={14}/> CURRENT WINDOW</div><h2>Mentor decisions close<br/><em>31 October · 6:00 PM IST</em></h2></div><button onClick={() => navigate('/login')}>Review your invitation <ChevronRight size={18}/></button></section>
    <footer className="ax-footer"><AxiomLogo/><p>Built by Club Asymptotes · Department of Mathematics · BMSIT</p></footer>
  </main>;
}

function Timeline({ deadlines, active }: { deadlines: Deadlines; active: number }) {
  const items = [
    ['Role decision', formatDeadline(deadlines.mentor_decision)],
    ['Problem statements', formatDeadline(deadlines.statement)],
    ['Member preferences', formatDeadline(deadlines.preference)],
    ['Team formation', 'Council review'],
  ];
  return <div className="ax-timeline">{items.map((item, index) => <div className={index <= active ? 'active' : ''} key={item[0]}><span>{index < active ? <Check size={14}/> : index + 1}</span><section><b>{item[0]}</b><small>{item[1]}</small></section></div>)}</div>;
}

export function AxiomDashboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<AxiomMe | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [choice, setChoice] = useState<'MENTOR' | 'PARTICIPANT' | 'OPTED_OUT' | null>(null);
  const [statement, setStatement] = useState({ title: '', domain: '', project_track: 'RESEARCH' as 'RESEARCH' | 'PRODUCT', problem_statement: '', project_context: '', helpful_skills: '' });

  const load = async () => {
    try {
      const next = await request<AxiomMe>('/axiom/me');
      if (next.is_super_admin) { navigate('/axiom/control', { replace: true }); return; }
      setData(next);
      if (next.statement) setStatement({
        title: next.statement.title, domain: next.statement.domain, project_track: next.statement.project_track,
        problem_statement: next.statement.problem_statement, project_context: next.statement.project_context,
        helpful_skills: next.statement.helpful_skills,
      });
    } catch (item) { setError(item instanceof Error ? item.message : 'Could not load Project Axiom.'); }
  };
  useEffect(() => { if (!getSession()) navigate('/login', { replace: true }); else void load(); }, []);

  async function confirmChoice() {
    if (!choice) return;
    setBusy(true); setError('');
    try { await request('/axiom/role-choice', 'POST', { choice, confirmed: true }); setChoice(null); await load(); }
    catch (item) { setError(item instanceof Error ? item.message : 'Could not save your decision.'); }
    finally { setBusy(false); }
  }
  async function saveStatement(submit: boolean) {
    setBusy(true); setError('');
    try { await request('/axiom/mentor/statement', 'PUT', { ...statement, submit }); await load(); }
    catch (item) { setError(item instanceof Error ? item.message : 'Could not save the problem statement.'); }
    finally { setBusy(false); }
  }
  if (!data) return <main className="ax-site ax-dashboard"><AxiomBackdrop/><AxiomHeader compact/><div className="ax-loading"><Orbit size={28}/> Loading your workspace…{error && <p>{error}</p>}</div></main>;

  const isCandidate = data.roster_type === 'MENTOR_CANDIDATE';
  const isMentor = data.role_choice === 'MENTOR';
  const activeStep = data.role_choice === 'PENDING' && isCandidate ? 0 : isMentor ? 1 : 2;
  return <main className="ax-site ax-dashboard"><AxiomBackdrop/><AxiomHeader compact/>
    <section className="ax-dash-head"><div><div className="ax-kicker"><CircleDot size={13}/> PROJECT AXIOM · 2026</div><h1>Welcome, <em>{data.display_name.split(' ')[0]}.</em></h1><p>{data.college_email}</p></div><div className="ax-status-pill"><span/><div><small>CURRENT STATUS</small><b>{data.role_choice === 'PENDING' ? (isCandidate ? 'Decision required' : 'Participant roster') : data.role_choice?.replace('_', ' ')}</b></div></div></section>
    <Timeline deadlines={data.deadlines} active={activeStep}/>
    {error && <div className="ax-alert"><X size={17}/>{error}</div>}

    {isCandidate && data.role_choice === 'PENDING' && <section className="ax-decision-section"><div className="ax-section-title"><div><span>01 / YOUR DECISION</span><h2>How will you take part?</h2></div><p>Choose once before {formatDeadline(data.deadlines.mentor_decision)}. You may review the consequences before confirming.</p></div><div className="ax-choice-grid">
      <button className={choice === 'MENTOR' ? 'selected' : ''} onClick={() => setChoice('MENTOR')}><div><BookOpen/><span>MENTOR</span></div><h3>Bring a problem worth solving.</h3><p>Propose either a research project or a product build that can improve the club, then guide a compact internal team.</p><small>Problem statement due {formatDeadline(data.deadlines.statement)}</small></button>
      <button className={choice === 'PARTICIPANT' ? 'selected' : ''} onClick={() => setChoice('PARTICIPANT')}><div><FlaskConical/><span>PARTICIPANT</span></div><h3>Build alongside the members.</h3><p>Choose three projects, propose your own approach and join one team as a hands-on contributor.</p><small>Preferences due {formatDeadline(data.deadlines.preference)}</small></button>
      <button className={`opt-out ${choice === 'OPTED_OUT' ? 'selected' : ''}`} onClick={() => setChoice('OPTED_OUT')}><div><X/><span>OPT OUT</span></div><h3>Sit out this cycle.</h3><p>You will miss this semester’s project build, reviews and showcase—but can join a future cycle.</p><small>No project access this semester</small></button>
    </div>{choice && <div className="ax-confirm-bar"><p><b>Confirm {choice.replace('_', ' ').toLowerCase()}?</b> This selection shapes this cycle’s team formation.</p><button disabled={busy} onClick={confirmChoice}>{busy ? 'Saving…' : 'Confirm decision'} <ArrowRight size={17}/></button></div>}</section>}

    {isMentor && <section className="ax-editor"><div className="ax-section-title"><div><span>02 / FRAME THE CHALLENGE</span><h2>Your problem statement</h2></div><p>Choose one path and explain how the outcome would improve Club Asymptotes.</p></div><div className="ax-editor-grid"><label>Project title<input value={statement.title} onChange={e => setStatement({...statement, title: e.target.value})} placeholder="A short, memorable title"/></label><label>Domain<input value={statement.domain} onChange={e => setStatement({...statement, domain: e.target.value})} placeholder="e.g. accessibility, data, education"/></label><label className="wide">Project path<select value={statement.project_track} onChange={e => setStatement({...statement, project_track: e.target.value as 'RESEARCH' | 'PRODUCT'})}><option value="RESEARCH">Research project — investigate and produce a useful finding</option><option value="PRODUCT">Product build — design and create a practical solution</option></select></label><label className="wide">Problem statement<textarea value={statement.problem_statement} onChange={e => setStatement({...statement, problem_statement: e.target.value})} placeholder="What specific problem should the team solve?"/></label><label className="wide">Why this helps Club Asymptotes and the expected outcome<textarea value={statement.project_context} onChange={e => setStatement({...statement, project_context: e.target.value})} placeholder="Explain the club need, constraints and what a successful research result or finished product would look like."/></label><label className="wide">Helpful skills — not eligibility requirements<input value={statement.helpful_skills} onChange={e => setStatement({...statement, helpful_skills: e.target.value})} placeholder="Research, frontend, statistics, electronics…"/></label></div><div className="ax-editor-actions"><span><ShieldCheck size={16}/> Members must accept the originality agreement before reading submitted statements.</span><button className="ax-secondary" disabled={busy} onClick={() => saveStatement(false)}>Save draft</button><button className="ax-primary compact" disabled={busy} onClick={() => saveStatement(true)}>Submit statement</button></div></section>}

    {!isCandidate && <section className="ax-member-wait"><div><Clock3/><span>MEMBER WINDOW OPENS AFTER STATEMENTS CLOSE</span></div><h2>Your project choices begin next.</h2><p>After 2 November at 3:00 PM, submitted challenges will be released together. Read them, select up to three preferences, and explain—in your own words—your approach and contribution before the participant window closes.</p><div className="ax-lock-row"><ShieldCheck size={18}/><span>Originality agreement and college-email verification required</span><b>{formatDeadline(data.deadlines.preference)} deadline</b></div></section>}

    {data.role_choice === 'PARTICIPANT' && isCandidate && <section className="ax-member-wait"><div><Clock3/><span>PARTICIPANT PATH CONFIRMED</span></div><h2>Your project choices begin next.</h2><p>Submitted problems will be released together after the mentor window closes. Three complete preferences give the matching system the best chance to place you within your choices.</p></section>}
    {data.role_choice === 'OPTED_OUT' && <section className="ax-member-wait quiet"><div><Check/><span>DECISION RECORDED</span></div><h2>You have opted out of this cycle.</h2><p>Your club access remains safe, but you will not be included in Project Axiom team formation this semester.</p></section>}
    <PasswordPanel/>
  </main>;
}

export function AxiomControlPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<ControlOverview | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { request<ControlOverview>('/axiom/control/overview').then(setData).catch(item => setError(item.message)); }, []);
  const ready = useMemo(() => data?.people.filter(person => person.role_choice !== 'PENDING').length || 0, [data]);
  return <main className="ax-site ax-dashboard"><AxiomBackdrop/><AxiomHeader compact/><section className="ax-dash-head"><div><div className="ax-kicker"><ShieldCheck size={13}/> CLUB COUNCIL CONTROL</div><h1>Project Axiom <em>overview.</em></h1><p>One roster, transparent decisions and a reviewable path to every final team.</p></div><button className="ax-secondary" onClick={() => navigate('/')}>Public page</button></section>{error && <div className="ax-alert"><X/>{error}</div>}{data && <><section className="ax-stat-grid"><div><small>ACTIVE ROSTER</small><b>{data.total}</b><span>approved accounts</span></div><div><small>DECISIONS RECEIVED</small><b>{ready}</b><span>of {data.mentor_candidates} candidates</span></div><div><small>CONFIRMED MENTORS</small><b>{data.choices.MENTOR || 0}</b><span>projects expected</span></div><div><small>STATEMENTS READY</small><b>{data.submitted_statements}</b><span>submitted</span></div></section><section className="ax-roster"><div className="ax-section-title"><div><span>LIVE ROSTER</span><h2>People and decisions</h2></div><p>Archisha Gupta is not included. Legacy event accounts remain paused.</p></div><div className="ax-roster-table">{data.people.map(person => <article key={person.email}><div className="ax-avatar">{person.name.split(' ').slice(0,2).map(part => part[0]).join('')}</div><div><b>{person.name}</b><small>{person.email}</small></div><span>{person.roster_type === 'MENTOR_CANDIDATE' ? 'CANDIDATE' : 'MEMBER'}</span><em className={person.role_choice.toLowerCase()}>{person.role_choice.replace('_', ' ')}</em></article>)}</div></section><PasswordPanel/></>}</main>;
}

export function PastEventsPage() {
  const navigate = useNavigate();
  return <main className="ax-site"><AxiomBackdrop/><AxiomHeader/><section className="ax-past-hero"><div className="ax-kicker"><History size={14}/> PAST EVENTS · ARCHIVE</div><h1>Experiments worth <em>remembering.</em></h1><p>The old event systems are safely archived. Scores, timestamps and verification records remain preserved while participant and staff access is paused.</p></section><section className="ax-past-card"><div className="ax-past-number">01</div><div><span>2026 · TWO-DAY FLAGSHIP</span><h2>ODDyssey</h2><p>A digitised treasure hunt, custom mathematical Cabo deck, live challenge stations and a legal reasoning finale.</p></div><div className="ax-archive-badge"><ShieldCheck/> READ-ONLY ARCHIVE</div></section><button className="ax-secondary ax-back" onClick={() => navigate('/')}><ArrowRight size={16}/> Return to current projects</button></main>;
}
