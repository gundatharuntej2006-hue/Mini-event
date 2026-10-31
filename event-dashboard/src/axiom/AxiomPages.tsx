import { type CSSProperties, type FormEvent, type PointerEvent as ReactPointerEvent, type RefObject, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowDown, ArrowRight, ArrowUp, BadgeCheck, BookOpen, CalendarClock, Check,
  ChevronRight, CircleDot, FileText, FlaskConical, History, Layers3,
  LockKeyhole, LogOut, MoveRight, Orbit, ShieldCheck, Sparkles, X,
} from 'lucide-react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useNavigate } from 'react-router-dom';
import { clearSession, getSession, request } from '../live/eventApi';

gsap.registerPlugin(ScrollTrigger);

type Deadlines = { mentor_decision: string; statement: string; preference: string };
type Statement = {
  title: string; domain: string; project_track: 'RESEARCH' | 'PRODUCT'; problem_statement: string;
  project_context: string; helpful_skills: string; status: 'DRAFT' | 'SUBMITTED'; submitted_at: string | null;
};
type Project = Statement & { id: string; mentor_name: string };
type Preference = { statement_id: string; preference_rank: number; proposed_solution: string; contribution: string };
type ProjectWorkspace = { agreement_accepted: boolean; window_open: boolean; window_closed: boolean; projects: Project[]; preferences: Preference[] };
type AxiomMe = {
  display_name: string; college_email?: string; is_super_admin?: boolean;
  roster_type?: 'MENTOR_CANDIDATE' | 'MEMBER';
  role_choice?: 'PENDING' | 'MENTOR' | 'PARTICIPANT' | 'OPTED_OUT';
  statement?: Statement | null; deadlines: Deadlines;
};
type MatchingTeam = { statement_id: string; title: string; track: string; members: { name: string; preference_rank: number }[] };
type ControlOverview = {
  total: number; mentor_candidates: number; members: number; submitted_statements: number; preference_count: number;
  choices: Record<string, number>; matching_preview: MatchingTeam[];
  people: { name: string; email: string; roster_type: string; role_choice: string }[];
};

const formatDeadline = (value: string) => new Intl.DateTimeFormat('en-IN', {
  day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', timeZone: 'Asia/Kolkata',
}).format(new Date(value));
const countWords = (value: string) => value.trim() ? value.trim().split(/\s+/).length : 0;

function useAxiomMotion(root: RefObject<HTMLElement>) {
  useEffect(() => {
    const element = root.current;
    if (!element || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const context = gsap.context(() => {
      const heroItems = element.querySelectorAll('.ax-hero-copy > *');
      const orbitStage = element.querySelector('.ax-orbit-stage');
      if (heroItems.length) gsap.fromTo(heroItems, { y: 34, opacity: 0 }, { y: 0, opacity: 1, duration: 1.05, stagger: .1, ease: 'power3.out' });
      if (orbitStage) gsap.fromTo(orbitStage, { scale: .9, opacity: 0, rotate: -2 }, { scale: 1, opacity: 1, rotate: 0, duration: 1.4, ease: 'expo.out' });
      gsap.utils.toArray<HTMLElement>('.ax-scroll').forEach((item) => {
        gsap.fromTo(item, { y: 54, opacity: 0 }, {
          y: 0, opacity: 1, duration: .95, ease: 'power3.out',
          scrollTrigger: { trigger: item, start: 'top 88%', once: true },
        });
      });
      const scene = element.querySelector('.ax-scene-scroll');
      const shards = element.querySelectorAll('.ax-spectral-shard');
      const heroCopy = element.querySelector('.ax-hero-copy');
      if (scene) {
        const supernatural = gsap.timeline({
          scrollTrigger: { trigger: '.ax-hero', start: 'top top', end: 'bottom top', scrub: 1.55 },
        });
        supernatural.to(scene, { yPercent: 22, scale: 1.16, rotate: 4, filter: 'blur(.7px)', ease: 'none' }, 0);
        if (heroCopy) supernatural.to(heroCopy, { yPercent: -8, opacity: .48, ease: 'none' }, 0);
        if (shards.length) supernatural.to(shards, { y: (index) => index % 2 ? -125 : 145, rotate: (index) => index % 2 ? 95 : -80, stagger: .025, ease: 'none' }, 0);
        const stringAtom = element.querySelector('.ax-string-atom');
        if (stringAtom) supernatural.to(stringAtom, { rotate: -16, scale: 1.1, ease: 'none' }, 0);
        element.querySelectorAll<SVGPathElement>('.ax-string-path').forEach((path, index) => {
          const morph = path.dataset.morph;
          if (morph) supernatural.to(path, { attr: { d: morph }, strokeWidth: index % 2 ? 2.6 : 3.35, ease: 'none' }, 0);
        });
      }
    }, element);

    const magnetic = [...element.querySelectorAll<HTMLElement>('.ax-primary,.ax-secondary,.ax-header nav button')];
    const cleanups = magnetic.map((button) => {
      const move = (event: PointerEvent) => {
        if (event.pointerType === 'touch') return;
        const box = button.getBoundingClientRect();
        gsap.to(button, { x: (event.clientX - box.left - box.width / 2) * .13, y: (event.clientY - box.top - box.height / 2) * .18, duration: .25, overwrite: true });
      };
      const leave = () => gsap.to(button, { x: 0, y: 0, duration: .55, ease: 'elastic.out(1,.4)' });
      button.addEventListener('pointermove', move); button.addEventListener('pointerleave', leave);
      return () => { button.removeEventListener('pointermove', move); button.removeEventListener('pointerleave', leave); };
    });
    return () => { cleanups.forEach(fn => fn()); context.revert(); };
  }, [root]);
}

function interactivePointer(event: ReactPointerEvent<HTMLElement>) {
  if (event.pointerType === 'touch') return;
  const box = event.currentTarget.getBoundingClientRect();
  const x = (event.clientX - box.left) / box.width;
  const y = (event.clientY - box.top) / box.height;
  event.currentTarget.style.setProperty('--ax-x', `${x * 100}%`);
  event.currentTarget.style.setProperty('--ax-y', `${y * 100}%`);
  event.currentTarget.style.setProperty('--ax-tilt-x', `${(x - .5) * 6}deg`);
  event.currentTarget.style.setProperty('--ax-tilt-y', `${(y - .5) * -6}deg`);
  event.currentTarget.style.setProperty('--ax-image-x', `${(x - .5) * 24}px`);
  event.currentTarget.style.setProperty('--ax-image-y', `${(y - .5) * 18}px`);
  event.currentTarget.style.setProperty('--ax-glow-x', `${(x - .5) * -10}px`);
  event.currentTarget.style.setProperty('--ax-glow-y', `${(y - .5) * -8}px`);
  event.currentTarget.style.setProperty('--ax-depth-x', `${(x - .5) * -8}px`);
  event.currentTarget.style.setProperty('--ax-depth-y', `${(y - .5) * -6}px`);
}

function AxiomBackdrop() {
  return <div className="ax-backdrop" aria-hidden="true"><i/><i/><i/><span>∑</span><span>π</span><span>∞</span><div className="ax-noise"/></div>;
}

function AxiomLogo() {
  return <div className="ax-logo"><span className="ax-glyph"><i/><i/><b>A</b></span><div><b>PROJECT AXIOM</b><small>AN ASYMPTOTES INITIATIVE</small></div></div>;
}

function AxiomHeader({ compact = false }: { compact?: boolean }) {
  const navigate = useNavigate();
  return <header className={`ax-header ${compact ? 'compact' : ''}`}><button className="ax-brand-button" onClick={() => navigate('/')}><AxiomLogo/></button><nav><button onClick={() => navigate('/past-events')}><History size={15}/> Past work</button>{getSession() ? <button onClick={() => { clearSession(); navigate('/login'); }}><LogOut size={15}/> Sign out</button> : <button onClick={() => navigate('/login')}>Member access <ArrowRight size={15}/></button>}</nav></header>;
}

function PasswordPanel() {
  const navigate = useNavigate();
  const [fields, setFields] = useState({ current: '', next: '', confirm: '' });
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState(''); const [error, setError] = useState('');
  async function changePassword(event: FormEvent) {
    event.preventDefault(); setError(''); setMessage('');
    if (fields.next !== fields.confirm) { setError('The two new passwords do not match.'); return; }
    setBusy(true);
    try {
      await request('/axiom/password', 'POST', { current_password: fields.current, new_password: fields.next, new_password_confirmation: fields.confirm });
      setMessage('Password changed. Sign in again using your new password.');
      setTimeout(() => { clearSession(); navigate('/login', { replace: true }); }, 1200);
    } catch (item) { setError(item instanceof Error ? item.message : 'Could not change the password.'); }
    finally { setBusy(false); }
  }
  return <section className="ax-password-panel ax-scroll ax-glass" onPointerMove={interactivePointer}>
    <div className="ax-section-title"><div><span>SECURITY</span><h2>Make this account yours.</h2></div><p>Your new password replaces the initial credential and becomes the only valid password for future logins.</p></div>
    <form onSubmit={changePassword}>
      <label>Current password<input type="password" autoComplete="current-password" value={fields.current} onChange={event => setFields({...fields, current:event.target.value})} required/></label>
      <label>New password<input type="password" autoComplete="new-password" minLength={8} maxLength={72} value={fields.next} onChange={event => setFields({...fields, next:event.target.value})} required/></label>
      <label>Confirm password<input type="password" autoComplete="new-password" minLength={8} maxLength={72} value={fields.confirm} onChange={event => setFields({...fields, confirm:event.target.value})} required/></label>
      <button className="ax-primary compact" disabled={busy}><LockKeyhole size={16}/>{busy ? 'Changing…' : 'Change password'}</button>
    </form>
    <small>Minimum eight characters. Passwords are stored only as secure hashes.</small>
    {error && <div className="ax-alert"><X size={16}/>{error}</div>}{message && <div className="ax-password-success"><Check size={16}/>{message}</div>}
  </section>;
}

export function AxiomLandingPage() {
  const navigate = useNavigate(); const root = useRef<HTMLElement>(null); useAxiomMotion(root);
  return <main ref={root} className="ax-site ax-premium" onPointerMove={interactivePointer}><AxiomBackdrop/><AxiomHeader/>
    <section className="ax-hero">
      <div className="ax-hero-copy">
        <div className="ax-kicker"><Sparkles size={14}/> BUILT FROM WITHIN · SEMESTER 01</div>
        <div className="ax-title-lockup"><span>PROJECT</span><h1>Axiom<em>.</em></h1></div>
        <p>Not another volunteer list. A private studio where Asymptotes’ core members investigate an idea or build a product—and leave the club stronger than they found it.</p>
        <div className="ax-hero-actions"><button className="ax-primary" onClick={() => navigate('/login')}>Enter the workspace <ArrowRight size={18}/></button><button className="ax-secondary" onClick={() => document.querySelector('.ax-paths')?.scrollIntoView({behavior:'smooth'})}>Discover the initiative <ArrowDown size={17}/></button></div>
        <div className="ax-hero-proof"><span><b>02</b> paths</span><span><b>01</b> community</span><span><b>∞</b> possibility</span></div>
      </div>
      <div className="ax-orbit-stage" aria-label="Project Axiom interactive creation system" onPointerMove={interactivePointer}>
        <div className="ax-scene-scroll"><div className="ax-scene-body">
          <div className="ax-spectral-field"><i/><i/><i/></div><div className="ax-visual-halo"/>
          <svg className="ax-string-atom" viewBox="0 0 720 720" role="img" aria-label="An artistic string-theory-inspired atom with luminous vibrating filaments">
            <defs>
              <linearGradient id="axiomStringA" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#d8ff67"/><stop offset=".48" stopColor="#8fb5ff"/><stop offset="1" stopColor="#ffc95c"/></linearGradient>
              <linearGradient id="axiomStringB" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#fff7d0"/><stop offset=".44" stopColor="#8deaff"/><stop offset="1" stopColor="#a995ff"/></linearGradient>
              <radialGradient id="axiomCore" cx="42%" cy="36%"><stop offset="0" stopColor="#ffffff"/><stop offset=".18" stopColor="#d8ff67"/><stop offset=".5" stopColor="#759fff"/><stop offset="1" stopColor="#071431" stopOpacity=".15"/></radialGradient>
              <filter id="axiomGlow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="3.5" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
              <filter id="axiomSoftGlow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="12"/></filter>
            </defs>
            <g className="ax-string-depth" fill="none" filter="url(#axiomSoftGlow)">
              <path d="M94 357 C117 105 603 105 628 357 C603 610 117 610 94 357"/><path d="M355 77 C617 124 648 511 437 629 C230 719 58 436 137 241 C193 103 276 63 355 77"/>
            </g>
            <g className="ax-string-web" fill="none" filter="url(#axiomGlow)">
              <path className="ax-string-path path-a" pathLength="100" d="M78 360 C112 154 608 154 642 360 C608 566 112 566 78 360" data-morph="M128 142 C368 48 671 270 568 495 C460 680 78 575 122 310 C143 190 221 165 128 142"/>
              <path className="ax-string-path path-b" pathLength="100" d="M132 160 C317 82 619 235 579 431 C539 615 218 672 116 486 C34 334 66 218 132 160" data-morph="M78 349 C135 111 520 92 637 295 C746 487 457 645 243 592 C42 543 24 458 78 349"/>
              <path className="ax-string-path path-c" pathLength="100" d="M358 72 C566 120 642 487 453 618 C286 733 77 492 121 282 C157 111 258 49 358 72" data-morph="M184 92 C422 44 684 227 598 449 C521 648 172 673 87 459 C13 273 73 126 184 92"/>
              <path className="ax-string-path path-d" pathLength="100" d="M102 245 C252 78 557 109 632 303 C704 491 449 642 231 583 C37 530 2 358 102 245" data-morph="M356 68 C552 92 677 344 579 527 C473 714 111 613 94 361 C82 177 202 49 356 68"/>
              <path className="ax-string-path path-e" pathLength="100" d="M169 536 C61 399 147 111 355 94 C563 77 691 351 565 520 C472 647 269 662 169 536" data-morph="M103 203 C261 45 594 113 635 344 C674 562 343 685 164 538 C35 432 16 290 103 203"/>
              <path className="ax-string-path path-f" pathLength="100" d="M87 413 C189 601 509 650 623 425 C715 243 466 55 244 109 C72 151 23 296 87 413" data-morph="M148 561 C16 378 122 92 349 77 C596 62 708 337 588 514 C486 664 257 694 148 561"/>
              <path className="ax-string-path path-g" pathLength="100" d="M214 89 C421 24 675 248 609 461 C547 659 218 679 103 487 C5 324 65 136 214 89" data-morph="M80 278 C169 76 495 35 628 230 C770 439 510 678 273 622 C71 575 8 442 80 278"/>
            </g>
            <g className="ax-string-particles"><g className="particle-orbit particle-a"><circle cx="360" cy="83" r="8"/></g><g className="particle-orbit particle-b"><circle cx="619" cy="360" r="6"/></g><g className="particle-orbit particle-c"><circle cx="360" cy="640" r="5"/></g><g className="particle-orbit particle-d"><circle cx="105" cy="360" r="7"/></g><g className="particle-orbit particle-e"><circle cx="540" cy="152" r="4"/></g></g>
            <g className="ax-atom-nucleus"><circle className="core-aura" cx="360" cy="360" r="102"/><circle className="core-shell" cx="360" cy="360" r="65"/><circle cx="337" cy="351" r="10"/><circle cx="382" cy="342" r="8"/><circle cx="367" cy="382" r="12"/><circle cx="342" cy="383" r="6"/></g>
          </svg>
          <div className="ax-orbit-core"><Orbit size={27}/><b>AXIOM</b><small>IDEA → IMPACT</small></div>
        </div></div>
        <div className="ax-atom-caption"><span>STRING FIELD · 01</span><p><b>Many vibrations. One system.</b> Inspired by string theory, this living atom visualises Project Axiom: individual ideas move differently, yet combine to create one coherent body of work.</p><small>Artistic interpretation—not a scientific simulation.</small></div>
      </div>
    </section>

    <section className="ax-statement ax-scroll"><span>THE PREMISE</span><p>Events create moments. <em>Communities create momentum.</em></p><small>Project Axiom gives our internal team the time, trust and structure to create work that lasts beyond one event.</small></section>

    <section className="ax-paths ax-scroll">
      <div className="ax-section-intro"><span>CHOOSE A DIRECTION</span><h2>Two paths.<br/><em>Equal ambition.</em></h2><p>A project follows one clear track. The difference is the output—not the value.</p></div>
      <article className="research ax-glass" onPointerMove={interactivePointer}><div className="ax-path-number">R/01</div><FlaskConical/><span>RESEARCH</span><h3>Turn a question into knowledge.</h3><p>Investigate a meaningful problem, test assumptions and produce findings the club can learn from or act upon.</p><small>QUESTION · METHOD · EVIDENCE · INSIGHT</small></article>
      <article className="product ax-glass" onPointerMove={interactivePointer}><div className="ax-path-number">P/02</div><Layers3/><span>PRODUCT</span><h3>Turn a need into something useful.</h3><p>Design, prototype and deliver a practical tool, system or experience that improves how the club works.</p><small>NEED · DESIGN · PROTOTYPE · IMPACT</small></article>
    </section>

    <section className="ax-process ax-scroll"><div className="ax-section-intro"><span>THE SYSTEM</span><h2>Preference, purpose<br/>and human judgment.</h2></div><div className="ax-process-line">{[
      ['01','Frame','Mentors submit one concise research or product challenge.'],['02','Explore','Members read every released project under an originality agreement.'],['03','Respond','Each member ranks up to three and explains a solution and contribution.'],['04','Match','Preference fit, mentor review and balanced capacity shape the teams.'],['05','Create','Teams work through checkpoints and present at the internal showcase.'],
    ].map(([n,title,copy]) => <article key={n}><b>{n}</b><div><span>{title}</span><p>{copy}</p></div></article>)}</div></section>

    <section className="ax-window ax-scroll ax-glass" onPointerMove={interactivePointer}><div><div className="ax-kicker"><CalendarClock size={14}/> CURRENT WINDOW</div><h2>Built for the people<br/><em>already building the club.</em></h2><p>Private access for the approved Asymptotes core roster.</p></div><button className="ax-primary" onClick={() => navigate('/login')}>Open your invitation <ChevronRight size={18}/></button></section>
    <footer className="ax-footer"><AxiomLogo/><p>Think · build · share · grow</p></footer>
  </main>;
}

function Timeline({ deadlines, active }: { deadlines: Deadlines; active: number }) {
  const items = [['Role decision',formatDeadline(deadlines.mentor_decision)],['Problem statements',formatDeadline(deadlines.statement)],['Member preferences',formatDeadline(deadlines.preference)],['Team formation','Council review']];
  return <div className="ax-timeline ax-scroll">{items.map((item,index)=><div className={index<=active?'active':''} key={item[0]}><span>{index<active?<Check size={14}/>:index+1}</span><section><b>{item[0]}</b><small>{item[1]}</small></section></div>)}</div>;
}

function ParticipantWorkspace({ data }: { data: AxiomMe }) {
  const [workspace,setWorkspace]=useState<ProjectWorkspace|null>(null); const [drafts,setDrafts]=useState<Preference[]>([]);
  const [busy,setBusy]=useState(false); const [error,setError]=useState(''); const [message,setMessage]=useState('');
  const load=async()=>{try{const next=await request<ProjectWorkspace>('/axiom/projects');setWorkspace(next);setDrafts(next.preferences);}catch(item){setError(item instanceof Error?item.message:'Could not load projects.');}};
  useEffect(()=>{void load();},[]);
  async function accept(){setBusy(true);setError('');try{await request('/axiom/agreement','POST',{accepted:true});await load();}catch(item){setError(item instanceof Error?item.message:'Could not record agreement.');}finally{setBusy(false);}}
  function add(project:Project){if(drafts.some(d=>d.statement_id===project.id)||drafts.length>=3)return;setDrafts([...drafts,{statement_id:project.id,preference_rank:drafts.length+1,proposed_solution:'',contribution:''}]);}
  function update(id:string,patch:Partial<Preference>){setDrafts(drafts.map(item=>item.statement_id===id?{...item,...patch}:item));}
  function remove(id:string){setDrafts(drafts.filter(item=>item.statement_id!==id).map((item,index)=>({...item,preference_rank:index+1})));}
  function move(index:number,direction:-1|1){const target=index+direction;if(target<0||target>=drafts.length)return;const next=[...drafts];[next[index],next[target]]=[next[target],next[index]];setDrafts(next.map((item,i)=>({...item,preference_rank:i+1})));}
  async function save(){setBusy(true);setError('');setMessage('');try{await request('/axiom/preferences','PUT',{preferences:drafts});setMessage('Your ranked preferences and responses are saved.');await load();}catch(item){setError(item instanceof Error?item.message:'Could not save preferences.');}finally{setBusy(false);}}
  if(!workspace)return <section className="ax-member-wait ax-scroll"><Orbit/><h2>Opening the project vault…</h2>{error&&<p>{error}</p>}</section>;
  if(!workspace.agreement_accepted)return <section className="ax-agreement ax-scroll ax-glass" onPointerMove={interactivePointer}><div className="ax-agreement-seal"><ShieldCheck/></div><div><span>ORIGINALITY & CONFIDENTIALITY</span><h2>Read with trust.<br/>Respond with your own thinking.</h2><p>Project statements belong to their authors and to this internal programme. Do not copy, distribute, publish or submit another person’s idea elsewhere. Your proposed solution must be written in your own words.</p><label><input type="checkbox" id="axiom-agree"/> I understand and agree to protect the originality of every project shared here.</label><button className="ax-primary" disabled={busy} onClick={()=>{const box=document.querySelector<HTMLInputElement>('#axiom-agree');if(box?.checked)void accept();else setError('Please tick the agreement before continuing.');}}>{busy?'Recording…':'Accept and enter'} <ArrowRight size={17}/></button>{error&&<div className="ax-alert"><X/>{error}</div>}</div></section>;
  if(!workspace.window_open)return <section className="ax-vault ax-scroll"><div className="ax-vault-lock"><LockKeyhole/><i/><i/></div><span>PROJECT VAULT SEALED</span><h2>Good work deserves<br/><em>one fair reveal.</em></h2><p>All submitted challenges will appear together after {formatDeadline(data.deadlines.statement)}. Until then, no participant can see them.</p></section>;
  return <section className="ax-project-workspace ax-scroll">
    <div className="ax-section-title"><div><span>PROJECT EXPLORER</span><h2>Choose with intent.</h2></div><p>Rank up to three. For each, explain your solution and the value you would bring—in no more than 88 words combined.</p></div>
    {workspace.projects.length===0?<div className="ax-empty-projects"><FileText/><h3>No submitted projects yet.</h3><p>The Council will release them here when ready.</p></div>:<div className="ax-project-grid">{workspace.projects.map((project,index)=>{const draft=drafts.find(item=>item.statement_id===project.id);const words=draft?countWords(draft.proposed_solution)+countWords(draft.contribution):0;return <article className={`ax-project-card ax-glass ${draft?'selected':''}`} key={project.id} onPointerMove={interactivePointer} style={{'--delay':`${index*.06}s`} as CSSProperties}>
      <header><span>{project.project_track}</span><small>{project.domain}</small>{draft&&<b>Preference {draft.preference_rank}</b>}</header><h3>{project.title}</h3><p>{project.problem_statement}</p><div className="ax-project-meta"><span>MENTOR</span><b>{project.mentor_name}</b></div><details><summary>Read project brief <ChevronRight size={15}/></summary><p>{project.project_context}</p><small>Helpful, not required: {project.helpful_skills||'An open mind and the willingness to learn.'}</small></details>
      {!draft?<button className="ax-secondary" disabled={drafts.length>=3||workspace.window_closed} onClick={()=>add(project)}>Add as preference <ArrowRight size={15}/></button>:<div className="ax-response-editor"><div className="ax-rank-tools"><span>RANK {draft.preference_rank}</span><button onClick={()=>move(draft.preference_rank-1,-1)} disabled={draft.preference_rank===1}><ArrowUp/></button><button onClick={()=>move(draft.preference_rank-1,1)} disabled={draft.preference_rank===drafts.length}><ArrowDown/></button><button onClick={()=>remove(project.id)}><X/></button></div><label>Your proposed solution<textarea value={draft.proposed_solution} onChange={event=>update(project.id,{proposed_solution:event.target.value})} placeholder="How would you approach this problem?"/></label><label>How you would contribute<textarea value={draft.contribution} onChange={event=>update(project.id,{contribution:event.target.value})} placeholder="What will you bring to this team?"/></label><small className={words>88?'over':''}>{words} / 88 words</small></div>}
    </article>;})}</div>}
    <div className="ax-preference-dock"><div><span>{drafts.length}/3 selected</span><p>More complete preferences give the matching process better options.</p></div><button className="ax-primary" disabled={busy||workspace.window_closed||drafts.length===0||drafts.some(item=>!item.proposed_solution.trim()||!item.contribution.trim()||countWords(item.proposed_solution)+countWords(item.contribution)>88)} onClick={()=>void save()}>{busy?'Saving…':'Save ranked preferences'} <BadgeCheck size={17}/></button></div>
    {error&&<div className="ax-alert"><X/>{error}</div>}{message&&<div className="ax-password-success"><Check/>{message}</div>}
  </section>;
}

export function AxiomDashboardPage() {
  const navigate=useNavigate(); const root=useRef<HTMLElement>(null); useAxiomMotion(root);
  const [data,setData]=useState<AxiomMe|null>(null); const [error,setError]=useState(''); const [busy,setBusy]=useState(false);
  const [choice,setChoice]=useState<'MENTOR'|'PARTICIPANT'|'OPTED_OUT'|null>(null);
  const [statement,setStatement]=useState({title:'',domain:'',project_track:'RESEARCH' as 'RESEARCH'|'PRODUCT',problem_statement:'',project_context:'',helpful_skills:''});
  const load=async()=>{try{const next=await request<AxiomMe>('/axiom/me');if(next.is_super_admin){navigate('/axiom/control',{replace:true});return;}setData(next);if(next.statement)setStatement({title:next.statement.title,domain:next.statement.domain,project_track:next.statement.project_track,problem_statement:next.statement.problem_statement,project_context:next.statement.project_context,helpful_skills:next.statement.helpful_skills});}catch(item){setError(item instanceof Error?item.message:'Could not load Project Axiom.');}};
  useEffect(()=>{if(!getSession())navigate('/login',{replace:true});else void load();},[]);
  async function confirmChoice(){if(!choice)return;setBusy(true);setError('');try{await request('/axiom/role-choice','POST',{choice,confirmed:true});setChoice(null);await load();}catch(item){setError(item instanceof Error?item.message:'Could not save your decision.');}finally{setBusy(false);}}
  async function saveStatement(submit:boolean){setBusy(true);setError('');try{await request('/axiom/mentor/statement','PUT',{...statement,submit});await load();}catch(item){setError(item instanceof Error?item.message:'Could not save the problem statement.');}finally{setBusy(false);}}
  if(!data)return <main className="ax-site ax-dashboard"><AxiomBackdrop/><AxiomHeader compact/><div className="ax-loading"><Orbit/> Loading your workspace…{error&&<p>{error}</p>}</div></main>;
  const isCandidate=data.roster_type==='MENTOR_CANDIDATE'; const isMentor=data.role_choice==='MENTOR'; const isParticipant=data.roster_type==='MEMBER'||data.role_choice==='PARTICIPANT'; const activeStep=data.role_choice==='PENDING'&&isCandidate?0:isMentor?1:2;
  const psWords=countWords(statement.problem_statement); const contextWords=countWords(statement.project_context);
  return <main ref={root} className="ax-site ax-dashboard ax-premium" onPointerMove={interactivePointer}><AxiomBackdrop/><AxiomHeader compact/>
    <section className="ax-dash-head"><div><div className="ax-kicker"><CircleDot/> PRIVATE AXIOM WORKSPACE</div><h1>Welcome, <em>{data.display_name.split(' ')[0]}.</em></h1><p>{data.college_email}</p></div><div className="ax-status-pill"><span/><div><small>CURRENT STATUS</small><b>{data.role_choice==='PENDING'?(isCandidate?'Decision required':'Participant roster'):data.role_choice?.replace('_',' ')}</b></div></div></section>
    <Timeline deadlines={data.deadlines} active={activeStep}/>{error&&<div className="ax-alert"><X/>{error}</div>}
    {isCandidate&&data.role_choice==='PENDING'&&<section className="ax-decision-section ax-scroll"><div className="ax-section-title"><div><span>01 / YOUR DECISION</span><h2>How will you take part?</h2></div><p>Review every path before confirming. Your decision shapes this cycle’s teams.</p></div><div className="ax-choice-grid">
      <button className={choice==='MENTOR'?'selected':''} onClick={()=>setChoice('MENTOR')}><div><BookOpen/><span>MENTOR</span></div><h3>Frame a challenge worth solving.</h3><p>Propose one research project or product build and guide a compact internal team.</p><small>CREATE THE BRIEF</small></button>
      <button className={choice==='PARTICIPANT'?'selected':''} onClick={()=>setChoice('PARTICIPANT')}><div><FlaskConical/><span>PARTICIPANT</span></div><h3>Bring a solution and build it.</h3><p>Explore projects, rank three and explain what you can contribute.</p><small>JOIN THE WORK</small></button>
      <button className={`opt-out ${choice==='OPTED_OUT'?'selected':''}`} onClick={()=>setChoice('OPTED_OUT')}><div><X/><span>OPT OUT</span></div><h3>Sit out this cycle.</h3><p>Your club access remains safe, but you will not join a project this semester.</p><small>FUTURE CYCLES REMAIN OPEN</small></button>
    </div>{choice&&<div className="ax-confirm-bar"><p><b>Confirm {choice.replace('_',' ').toLowerCase()}?</b> This becomes your Project Axiom path.</p><button disabled={busy} onClick={()=>void confirmChoice()}>{busy?'Saving…':'Confirm decision'} <ArrowRight/></button></div>}</section>}
    {isMentor&&<section className="ax-editor ax-scroll ax-glass" onPointerMove={interactivePointer}><div className="ax-section-title"><div><span>02 / FRAME THE CHALLENGE</span><h2>Your problem statement.</h2></div><p>Clear enough to begin. Open enough to discover.</p></div><div className="ax-editor-grid"><label>Project title<input value={statement.title} onChange={e=>setStatement({...statement,title:e.target.value})} placeholder="A short, memorable title"/></label><label>Domain<input value={statement.domain} onChange={e=>setStatement({...statement,domain:e.target.value})} placeholder="Data, education, accessibility…"/></label><label className="wide">Project path<select value={statement.project_track} onChange={e=>setStatement({...statement,project_track:e.target.value as 'RESEARCH'|'PRODUCT'})}><option value="RESEARCH">Research — investigate and produce a useful finding</option><option value="PRODUCT">Product — design and create a practical solution</option></select></label><label className="wide">Problem statement<textarea value={statement.problem_statement} onChange={e=>setStatement({...statement,problem_statement:e.target.value})} placeholder="What specific problem should the team solve?"/><small className={psWords>44?'over':''}>{psWords} / 44 words</small></label><label className="wide">Why this matters and what success looks like<textarea value={statement.project_context} onChange={e=>setStatement({...statement,project_context:e.target.value})} placeholder="Explain the club need, constraints and intended outcome."/><small className={contextWords>88?'over':''}>{contextWords} / 88 words</small></label><label className="wide">Helpful skills — not eligibility requirements<input value={statement.helpful_skills} onChange={e=>setStatement({...statement,helpful_skills:e.target.value})} placeholder="Research, frontend, statistics, electronics…"/></label></div><div className="ax-editor-actions"><span><ShieldCheck/> Members accept the originality agreement before reading.</span><button className="ax-secondary" disabled={busy||psWords>44||contextWords>88} onClick={()=>void saveStatement(false)}>Save draft</button><button className="ax-primary compact" disabled={busy||psWords>44||contextWords>88} onClick={()=>void saveStatement(true)}>Submit statement</button></div></section>}
    {isParticipant&&<ParticipantWorkspace data={data}/>} {data.role_choice==='OPTED_OUT'&&<section className="ax-member-wait quiet ax-scroll"><Check/><span>DECISION RECORDED</span><h2>You have opted out of this cycle.</h2><p>You can return in a future Project Axiom cycle.</p></section>}
    <PasswordPanel/>
  </main>;
}

export function AxiomControlPage() {
  const navigate=useNavigate(); const root=useRef<HTMLElement>(null); useAxiomMotion(root); const [data,setData]=useState<ControlOverview|null>(null); const [error,setError]=useState('');
  useEffect(()=>{request<ControlOverview>('/axiom/control/overview').then(setData).catch(item=>setError(item.message));},[]);
  const ready=useMemo(()=>data?.people.filter(person=>person.role_choice!=='PENDING').length||0,[data]);
  return <main ref={root} className="ax-site ax-dashboard ax-premium" onPointerMove={interactivePointer}><AxiomBackdrop/><AxiomHeader compact/><section className="ax-dash-head"><div><div className="ax-kicker"><ShieldCheck/> CLUB COUNCIL CONTROL</div><h1>Axiom, <em>at a glance.</em></h1><p>Transparent inputs. Reviewable matching. Human final judgment.</p></div><button className="ax-secondary" onClick={()=>navigate('/')}>Public page</button></section>{error&&<div className="ax-alert"><X/>{error}</div>}{data&&<><section className="ax-stat-grid ax-scroll"><div><small>ACTIVE ROSTER</small><b>{data.total}</b><span>approved accounts</span></div><div><small>DECISIONS</small><b>{ready}</b><span>of {data.mentor_candidates} candidates</span></div><div><small>PROJECTS</small><b>{data.submitted_statements}</b><span>submitted statements</span></div><div><small>RESPONSES</small><b>{data.preference_count}</b><span>ranked preferences</span></div></section>
    <section className="ax-matching ax-scroll"><div className="ax-section-title"><div><span>PREFERENCE-FIT PREVIEW</span><h2>A transparent first pass.</h2></div><p>First choices are considered first, normal capacity is three, and only one team may expand to four. Mentor review and Council judgment remain final.</p></div>{data.matching_preview.length===0?<div className="ax-empty-projects"><Orbit/><h3>Waiting for projects and preferences.</h3></div>:<div className="ax-matching-grid">{data.matching_preview.map(team=><article key={team.statement_id}><header><span>{team.track}</span><b>{team.members.length}/3</b></header><h3>{team.title}</h3>{team.members.length?team.members.map(member=><div className="ax-match-person" key={member.name}><span>{member.name.split(' ').map(part=>part[0]).slice(0,2).join('')}</span><b>{member.name}</b><small>Preference {member.preference_rank}</small></div>):<p>No preference fit yet.</p>}</article>)}</div>}</section>
    <section className="ax-roster ax-scroll"><div className="ax-section-title"><div><span>LIVE ROSTER</span><h2>People and decisions.</h2></div><p>Legacy event accounts remain paused.</p></div><div className="ax-roster-table">{data.people.map(person=><article key={person.email}><div className="ax-avatar">{person.name.split(' ').slice(0,2).map(part=>part[0]).join('')}</div><div><b>{person.name}</b><small>{person.email}</small></div><span>{person.roster_type==='MENTOR_CANDIDATE'?'CANDIDATE':'MEMBER'}</span><em className={person.role_choice.toLowerCase()}>{person.role_choice.replace('_',' ')}</em></article>)}</div></section><PasswordPanel/></>}</main>;
}

export function PastEventsPage() {
  const navigate=useNavigate(); const root=useRef<HTMLElement>(null); useAxiomMotion(root);
  return <main ref={root} className="ax-site ax-premium"><AxiomBackdrop/><AxiomHeader/><section className="ax-past-hero"><div className="ax-kicker"><History/> PAST EVENTS · ARCHIVE</div><h1>Experiments worth <em>remembering.</em></h1><p>Previous event systems are preserved as read-only records while Project Axiom becomes the current internal workspace.</p></section><section className="ax-past-card ax-scroll"><div className="ax-past-number">01</div><div><span>2026 · TWO-DAY FLAGSHIP</span><h2>ODDyssey</h2><p>A digitised treasure hunt, mathematical Cabo deck, live challenge stations and a legal-reasoning finale.</p></div><div className="ax-archive-badge"><ShieldCheck/> READ-ONLY ARCHIVE</div></section><button className="ax-secondary ax-back" onClick={()=>navigate('/')}><MoveRight/> Return to Project Axiom</button></main>;
}
