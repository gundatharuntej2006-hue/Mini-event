import { type CSSProperties, type FormEvent, type PointerEvent as ReactPointerEvent, type RefObject, useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowDown, ArrowRight, CalendarClock, Check,
  ChevronRight, CircleDot, FileText, FlaskConical, History, Layers3,
  LockKeyhole, LogOut, MoveRight, Orbit, ShieldCheck, Sparkles, X,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { clearSession, getSession, request } from '../live/eventApi';
import earthTexture from '../assets/earth-blue-marble-nasa.jpg';
import earthNightLights from '../assets/earth-night-lights-nasa.jpg';

type Deadlines = { team_finalization: string };
type Statement = {
  id?: string; statement_slot?: number;
  title: string; domain: string; project_track: 'RESEARCH' | 'PRODUCT'; problem_statement: string;
  project_context: string; helpful_skills: string; status: 'DRAFT' | 'SUBMITTED'; submitted_at: string | null;
};
type Project = Statement & { id: string; publisher_name: string; is_publisher: boolean };
type Application = { statement_id: string; proposed_solution: string; contribution: string };
type ProjectWorkspace = { agreement_accepted: boolean; selection_open: boolean; team_finalization_deadline: string; projects: Project[]; applications: Application[] };
type AxiomMe = {
  display_name: string; college_email?: string; is_super_admin?: boolean;
  roster_type?: 'MENTOR_CANDIDATE' | 'MEMBER';
  role_choice?: 'PENDING' | 'MENTOR' | 'PARTICIPANT' | 'OPTED_OUT';
  statement?: Statement | null; statements?: Statement[]; deadlines: Deadlines;
};
type MatchingTeam = { statement_id: string; title: string; track: string; members: { name: string; preference_rank: number }[] };
type ControlOverview = {
  total: number; mentor_candidates: number; members: number; submitted_statements: number; preference_count: number;
  choices: Record<string, number>; matching_preview: MatchingTeam[];
  people: { name: string; email: string; roster_type: string; role_choice: string }[];
};

type SkyMode = 'auto' | 'morning' | 'afternoon' | 'evening' | 'night';
type SkyPhase = Exclude<SkyMode, 'auto'>;
const SKY_MODES: Array<{ value: SkyMode; label: string }> = [
  { value: 'auto', label: 'Auto · IST' }, { value: 'morning', label: 'Morning' },
  { value: 'afternoon', label: 'Afternoon' }, { value: 'evening', label: 'Evening' }, { value: 'night', label: 'Night' },
];
const getIndiaMinutes = () => {
  const parts = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(new Date());
  const hour = Number(parts.find((part) => part.type === 'hour')?.value || 0);
  const minute = Number(parts.find((part) => part.type === 'minute')?.value || 0);
  return hour * 60 + minute;
};
const getSkyClock = (mode: SkyMode): { phase: SkyPhase; minutes: number } => {
  const previewMinutes: Record<SkyPhase, number> = { morning: 7 * 60 + 15, afternoon: 13 * 60 + 30, evening: 18 * 60, night: 22 * 60 };
  const minutes = mode === 'auto' ? getIndiaMinutes() : previewMinutes[mode];
  const phase: SkyPhase = mode !== 'auto' ? mode : minutes >= 330 && minutes < 720 ? 'morning' : minutes >= 720 && minutes < 990 ? 'afternoon' : minutes >= 990 && minutes < 1155 ? 'evening' : 'night';
  return { phase, minutes };
};

const formatDeadline = (value: string) => new Intl.DateTimeFormat('en-IN', {
  day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit', timeZone: 'Asia/Kolkata',
}).format(new Date(value));
const countWords = (value: string) => value.trim() ? value.trim().split(/\s+/).length : 0;

function useAxiomMotion(root: RefObject<HTMLElement>) {
  useEffect(() => {
    const element = root.current;
    if (!element || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    let disposed = false;
    let teardown = () => {};
    void Promise.all([import('gsap'), import('gsap/ScrollTrigger')]).then(([gsapModule, triggerModule]) => {
      if (disposed) return;
      const gsap = gsapModule.gsap;
      gsap.registerPlugin(triggerModule.ScrollTrigger);
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
        const orbitCore = element.querySelector('.ax-orbit-core');
        const atomCaption = element.querySelector('.ax-atom-caption');
        if (orbitCore) supernatural.to(orbitCore, { opacity: 0, scale: .28, filter: 'blur(9px)', ease: 'none' }, 0);
        if (atomCaption) supernatural.to(atomCaption, { opacity: 0, y: 34, ease: 'none' }, .08);
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
      teardown = () => { cleanups.forEach(fn => fn()); context.revert(); };
    });
    return () => { disposed = true; teardown(); };
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

function closedStringPath(time: number, phase = 0) {
  const points: string[] = [];
  const count = 180;
  for (let index = 0; index <= count; index += 1) {
    const theta = (index / count) * Math.PI * 2;
    // A classical visual analogue of a closed string: two oppositely travelling
    // waves plus a higher harmonic. Their superposition changes the loop shape.
    const left = 20 * Math.sin(2 * theta - time * 1.18 + phase);
    const right = 13 * Math.sin(3 * theta + time * .92 - phase * .7);
    const harmonic = 6 * Math.sin(5 * theta - time * 1.7 + phase * 1.4);
    const radius = 142 + left + right + harmonic;
    const x = 260 + radius * Math.cos(theta);
    const y = 175 + radius * .58 * Math.sin(theta) + 9 * Math.sin(2 * theta + time * .7);
    points.push(`${index === 0 ? 'M' : 'L'}${x.toFixed(2)} ${y.toFixed(2)}`);
  }
  return `${points.join(' ')} Z`;
}

function StringTheoryLab() {
  const primary = useRef<SVGPathElement>(null);
  const echoA = useRef<SVGPathElement>(null);
  const echoB = useRef<SVGPathElement>(null);
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      primary.current?.setAttribute('d', closedStringPath(.6));
      echoA.current?.setAttribute('d', closedStringPath(.6, .45));
      echoB.current?.setAttribute('d', closedStringPath(.6, -.45));
      return;
    }
    let frame = 0;
    const started = performance.now();
    const draw = (stamp: number) => {
      const time = (stamp - started) / 1000;
      primary.current?.setAttribute('d', closedStringPath(time));
      echoA.current?.setAttribute('d', closedStringPath(time, .42));
      echoB.current?.setAttribute('d', closedStringPath(time, -.42));
      frame = window.requestAnimationFrame(draw);
    };
    frame = window.requestAnimationFrame(draw);
    return () => window.cancelAnimationFrame(frame);
  }, []);
  return <section className="ax-string-lab ax-scroll">
    <div className="ax-lab-copy"><span>MAGNIFICATION · CLOSED STRING</span><h2>Not an orbit.<br/><em>A vibration.</em></h2><p>String theory models fundamental objects as one-dimensional strings. This view isolates one closed loop and projects its motion into two dimensions so the changing modes can be seen.</p><div className="ax-mode-notes"><article><b>01</b><div><strong>Left-moving mode</strong><small>A wave travels around the loop in one direction.</small></div></article><article><b>02</b><div><strong>Right-moving mode</strong><small>A second wave travels in the opposite direction.</small></div></article><article><b>03</b><div><strong>Superposition</strong><small>The modes overlap, producing the continuously changing profile.</small></div></article></div><small className="ax-physics-note">Conceptual classical projection. A full string-theory description is quantum and may require additional dimensions.</small></div>
    <div className="ax-loop-viewport" aria-label="Animated projection of harmonic modes on a closed string"><div className="ax-loop-grid"/><svg viewBox="0 0 520 350" role="img" aria-label="Closed string vibrating through several harmonic modes"><defs><linearGradient id="loopSpectrum" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#67e8f9"/><stop offset=".48" stopColor="#c4b5fd"/><stop offset="1" stopColor="#f0abfc"/></linearGradient><filter id="loopGlow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><path ref={echoA} className="ax-loop-echo echo-a"/><path ref={echoB} className="ax-loop-echo echo-b"/><path ref={primary} className="ax-loop-main" filter="url(#loopGlow)"/></svg><div className="ax-mode-chip chip-left">ψ<sub>L</sub> left-moving</div><div className="ax-mode-chip chip-right">ψ<sub>R</sub> right-moving</div><div className="ax-frequency"><i/><span>MODE ENERGY</span><b>n = 2 + 3 + 5</b></div></div>
  </section>;
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

function NightSkyCanvas({ mode }: { mode: SkyMode }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d', { alpha: false, desynchronized: true });
    if (!canvas || !context) return;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const memory = (navigator as Navigator & { deviceMemory?: number }).deviceMemory ?? 4;
    const lowPower = navigator.hardwareConcurrency <= 4 || memory <= 4;
    const frameInterval = lowPower ? 50 : 33;
    let width = 0; let height = 0; let ratio = 1; let frame = 0; let lastPaint = 0; let scrollProgress = 0; let pageVisible = !document.hidden;
    let skyClock = getSkyClock(mode); let lastClockUpdate = 0;
    let nextMeteor = performance.now() + 1400 + Math.random() * 4200;
    let meteor: { started: number; x: number; y: number; dx: number; dy: number; length: number; duration: number; brightness: number; twin: boolean } | null = null;
    let nextImpact = performance.now() + 4000 + Math.random() * 3000;
    type ImpactSpark = { angle: number; speed: number; size: number; heat: number };
    type SkyImpact = { started: number; x: number; y: number; direction: number; scale: number; meteorSide: number; sparks: ImpactSpark[] };
    let impact: SkyImpact | null = null;
    type Star = { x: number; y: number; depth: number; radius: number; phase: number; pulse: number; tone: [number, number, number]; glow: boolean };
    type Firefly = { x: number; y: number; phase: number; speed: number; radius: number; drift: number };
    type Flight = { x: number; y: number; speed: number; phase: number; direction: number; scale: number; bank: number; delayUntil: number };
    let stars: Star[] = []; let fireflies: Firefly[] = []; let flights: Flight[] = [];

    const randomiseFlight = (flight: Flight, time: number, initial = false) => {
      flight.direction = Math.random() > .5 ? 1 : -1;
      flight.x = initial ? Math.random() * 1.3 - .15 : (flight.direction > 0 ? -.22 : 1.22);
      flight.y = .16 + Math.random() * .68;
      flight.speed = .0024 + Math.random() * .0035;
      flight.phase = Math.random() * Math.PI * 2;
      flight.scale = .72 + Math.random() * .68;
      flight.bank = -.045 + Math.random() * .09;
      flight.delayUntil = initial ? time + Math.random() * 2800 : time + 1100 + Math.random() * 7200;
    };

    const launchMeteor = (time: number) => {
      const fromLeft = Math.random() > .34;
      const shallow = Math.random() > .48;
      meteor = {
        started: time,
        x: fromLeft ? -.08 + Math.random() * .45 : .66 + Math.random() * .4,
        y: .025 + Math.random() * .39,
        dx: (fromLeft ? 1 : -1) * (.18 + Math.random() * .34),
        dy: shallow ? .09 + Math.random() * .13 : .2 + Math.random() * .25,
        length: 58 + Math.random() * 170,
        duration: 620 + Math.random() * 920,
        brightness: .62 + Math.random() * .38,
        twin: Math.random() > .78,
      };
    };

    const launchImpact = (time: number) => {
      const zone = Math.floor(Math.random() * 3);
      const impactX = zone === 1 ? (Math.random() > .5 ? .08 + Math.random() * .17 : .75 + Math.random() * .17) : .16 + Math.random() * .68;
      const impactY = zone === 0 ? .13 + Math.random() * .16 : zone === 1 ? .31 + Math.random() * .36 : .72 + Math.random() * .16;
      impact = {
        started: time,
        x: impactX,
        y: impactY,
        direction: Math.random() > .5 ? 1 : -1,
        scale: .82 + Math.random() * .72,
        meteorSide: Math.random() > .5 ? 1 : -1,
        sparks: Array.from({ length: 16 + Math.floor(Math.random() * 13) }, () => ({
          angle: Math.random() * Math.PI * 2,
          speed: .45 + Math.random() * 1.25,
          size: .7 + Math.random() * 2.1,
          heat: .45 + Math.random() * .55,
        })),
      };
      meteor = null;
      nextMeteor = time + 8500 + Math.random() * 4500;
    };

    const paintSun = (x: number, y: number, radius: number, warmth: number, alpha = 1) => {
      const halo = context.createRadialGradient(x, y, 0, x, y, radius * 7.5);
      halo.addColorStop(0, `rgba(255,250,214,${alpha * .92})`);
      halo.addColorStop(.13, `rgba(255,${Math.round(224 - warmth * 42)},${Math.round(145 - warmth * 52)},${alpha * .54})`);
      halo.addColorStop(.48, `rgba(255,134,70,${alpha * .12})`);
      halo.addColorStop(1, 'rgba(255,110,40,0)');
      context.fillStyle = halo; context.beginPath(); context.arc(x, y, radius * 7.5, 0, Math.PI * 2); context.fill();
      context.fillStyle = `rgba(255,${Math.round(245 - warmth * 35)},${Math.round(194 - warmth * 73)},${alpha})`;
      context.shadowBlur = radius * 1.8; context.shadowColor = 'rgba(255,209,116,.72)';
      context.beginPath(); context.arc(x, y, radius, 0, Math.PI * 2); context.fill(); context.shadowBlur = 0;
    };

    const paintCloud = (x: number, y: number, scale: number, alpha: number) => {
      context.save(); context.translate(x, y); context.scale(scale, scale);
      const lobes = [[-34, 7, 19], [-17, -2, 25], [5, -11, 31], [29, -1, 24], [45, 10, 16], [8, 13, 38]];
      context.filter = 'blur(7px)';
      context.fillStyle = `rgba(78,126,163,${alpha * .2})`; context.beginPath(); context.ellipse(5, 18, 70, 22, 0, 0, Math.PI * 2); context.fill();
      context.filter = 'none';
      lobes.forEach(([cloudX, cloudY, cloudRadius], index) => {
        const lobe = context.createRadialGradient(cloudX - cloudRadius * .3, cloudY - cloudRadius * .42, cloudRadius * .08, cloudX, cloudY, cloudRadius);
        lobe.addColorStop(0, `rgba(255,255,255,${alpha * (index === 2 ? 1 : .9)})`);
        lobe.addColorStop(.58, `rgba(236,246,252,${alpha * .78})`);
        lobe.addColorStop(1, `rgba(145,181,207,${alpha * .22})`);
        context.fillStyle = lobe; context.beginPath(); context.arc(cloudX, cloudY, cloudRadius, 0, Math.PI * 2); context.fill();
      });
      const base = context.createLinearGradient(0, 2, 0, 28); base.addColorStop(0, `rgba(244,251,255,${alpha * .76})`); base.addColorStop(1, `rgba(130,172,204,${alpha * .17})`);
      context.fillStyle = base; context.beginPath(); context.ellipse(4, 13, 54, 19, 0, 0, Math.PI * 2); context.fill();
      context.fillStyle = `rgba(255,255,255,${alpha * .16})`; context.beginPath(); context.ellipse(-18, -18, 25, 7, -.13, 0, Math.PI * 2); context.fill();
      context.restore();
    };

    const paintBirdFlock = (time: number, direction: number, evening = false) => {
      const progress = (time * (evening ? .000023 : .000028) + (evening ? .38 : .08)) % 1;
      const leadX = (direction > 0 ? -.14 + progress * 1.28 : 1.14 - progress * 1.28) * width;
      const leadY = (evening ? .29 : .24) * height + Math.sin(progress * Math.PI * 2) * 12;
      const birds = [[0, 0], [-22, -12], [-22, 12], [-45, -23], [-45, 23], [-70, -31], [-70, 31]];
      context.strokeStyle = evening ? 'rgba(35,30,46,.72)' : 'rgba(43,63,78,.66)'; context.lineWidth = 1.35;
      birds.forEach(([birdX, birdY], index) => {
        const x = leadX + birdX * direction; const y = leadY + birdY;
        const flap = Math.sin(time * .012 + index * 1.7) * 2.4;
        context.beginPath(); context.moveTo(x - 5, y + flap); context.quadraticCurveTo(x - 2, y - 3, x, y); context.quadraticCurveTo(x + 2, y - 3, x + 5, y - flap); context.stroke();
      });
    };

    const paintFireflies = (time: number) => {
      fireflies.forEach((firefly) => {
        const pulse = Math.max(0, Math.sin(time * .001 * firefly.speed + firefly.phase));
        const brightness = Math.pow(pulse, 4);
        if (brightness < .025) return;
        const x = (firefly.x + Math.sin(time * .00022 + firefly.phase) * firefly.drift) * width;
        const y = (firefly.y + Math.cos(time * .00017 + firefly.phase * 1.3) * firefly.drift * .65) * height;
        const haloRadius = firefly.radius * (5.5 + brightness * 4);
        const halo = context.createRadialGradient(x, y, 0, x, y, haloRadius);
        halo.addColorStop(0, `rgba(239,255,133,${.92 * brightness})`); halo.addColorStop(.22, `rgba(201,255,90,${.42 * brightness})`); halo.addColorStop(1, 'rgba(174,255,77,0)');
        context.fillStyle = halo; context.beginPath(); context.arc(x, y, haloRadius, 0, Math.PI * 2); context.fill();
        context.fillStyle = `rgba(250,255,184,${brightness})`; context.beginPath(); context.arc(x, y, firefly.radius, 0, Math.PI * 2); context.fill();
      });
    };

    const paintAfternoonBalloon = (time: number) => {
      const progress = (time * .000017 + .21) % 1;
      const x = (-.1 + progress * 1.2) * width; const y = (.24 + Math.sin(progress * Math.PI * 2) * .035) * height;
      const scale = width < 700 ? .72 : 1;
      context.save(); context.translate(x, y); context.scale(scale, scale);
      const balloon = context.createLinearGradient(-12, -22, 15, 20);
      balloon.addColorStop(0, 'rgba(252,237,191,.95)'); balloon.addColorStop(.48, 'rgba(218,91,66,.95)'); balloon.addColorStop(1, 'rgba(107,49,81,.92)');
      context.fillStyle = balloon; context.beginPath(); context.ellipse(0, 0, 15, 21, 0, 0, Math.PI * 2); context.fill();
      context.strokeStyle = 'rgba(75,46,48,.65)'; context.lineWidth = 1; context.beginPath(); context.moveTo(-9, 16); context.lineTo(-4, 27); context.moveTo(9, 16); context.lineTo(4, 27); context.stroke();
      context.fillStyle = 'rgba(70,48,35,.86)'; context.fillRect(-5, 27, 10, 6); context.restore();
    };

    const buildField = () => {
      ratio = Math.min(window.devicePixelRatio || 1, lowPower ? 1 : 1.25);
      width = window.innerWidth; height = window.innerHeight;
      canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
      canvas.style.width = `${width}px`; canvas.style.height = `${height}px`;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      const count = width < 700 ? (lowPower ? 80 : 110) : (lowPower ? 135 : 190);
      const starTones: Array<[number, number, number]> = [[217, 232, 255], [244, 247, 255], [255, 239, 211], [203, 222, 255]];
      stars = Array.from({ length: count }, () => ({
        x: Math.random(), y: Math.random(), depth: .15 + Math.random() * .85,
        radius: .28 + Math.pow(Math.random(), 2.6) * 1.95, phase: Math.random() * Math.PI * 2, pulse: .24 + Math.random() * .68,
        tone: starTones[Math.floor(Math.random() * starTones.length)], glow: Math.random() > .91,
      }));
      fireflies = Array.from({ length: width < 700 ? 24 : 38 }, () => ({
        x: .035 + Math.random() * .93, y: .48 + Math.random() * .34,
        phase: Math.random() * Math.PI * 2, speed: .65 + Math.random() * 1.4,
        radius: .75 + Math.random() * 1.25, drift: .004 + Math.random() * .013,
      }));
      flights = Array.from({ length: 3 }, () => ({ x: 0, y: 0, speed: 0, phase: 0, direction: 1, scale: 1, bank: 0, delayUntil: 0 }));
      flights.forEach((flight) => randomiseFlight(flight, performance.now(), true));
    };
    const updateScroll = () => {
      const available = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      scrollProgress = Math.min(1, Math.max(0, window.scrollY / available));
    };
    const draw = (time: number) => {
      frame = 0;
      if (!pageVisible) return;
      if (!reduceMotion && time - lastPaint < frameInterval) { frame = window.requestAnimationFrame(draw); return; }
      lastPaint = time;
      if (time - lastClockUpdate > 30000) { skyClock = getSkyClock(mode); lastClockUpdate = time; }
      const { phase, minutes } = skyClock;
      const palettes: Record<SkyPhase, [string, string, string, string]> = {
        night: ['#01030b', '#030b1c', '#07182d', '#102d4b'],
        morning: ['#1b4168', '#5e99c4', '#b9d8e7', '#f7c78d'],
        afternoon: ['#1679bd', '#37a0dd', '#81c7e8', '#d7eef7'],
        evening: ['#111a3a', '#50385e', '#b85d65', '#f3a15f'],
      };
      const palette = palettes[phase];
      const sky = context.createLinearGradient(0, 0, 0, height);
      sky.addColorStop(0, palette[0]); sky.addColorStop(.34, palette[1]); sky.addColorStop(.7, palette[2]); sky.addColorStop(1, palette[3]);
      context.fillStyle = sky; context.fillRect(0, 0, width, height);
      const glow = context.createRadialGradient(width * .52, height * .62, 0, width * .52, height * .62, Math.max(width, height) * .82);
      glow.addColorStop(0, phase === 'night' ? 'rgba(28,76,126,.18)' : phase === 'evening' ? 'rgba(255,151,96,.18)' : 'rgba(255,239,203,.12)');
      glow.addColorStop(.55, phase === 'night' ? 'rgba(9,31,64,.07)' : 'rgba(255,205,148,.04)'); glow.addColorStop(1, 'rgba(0,0,0,0)');
      context.fillStyle = glow; context.fillRect(0, 0, width, height);
      const horizon = context.createLinearGradient(0, height * .68, 0, height);
      horizon.addColorStop(0, 'rgba(20,53,86,0)'); horizon.addColorStop(1, phase === 'night' ? 'rgba(54,91,119,.12)' : phase === 'evening' ? 'rgba(255,157,92,.24)' : 'rgba(239,246,248,.16)');
      context.fillStyle = horizon; context.fillRect(0, height * .68, width, height * .32);

      if (phase === 'morning') {
        const morningProgress = Math.min(1, Math.max(0, (minutes - 330) / 390));
        paintSun(width * (.06 + morningProgress * .18), height * (.91 - Math.sin(morningProgress * Math.PI * .5) * .47), width < 700 ? 14 : 21, .28, .94);
        const drift = (time * .000007) % 1;
        paintCloud((-.2 + drift * 1.4) * width, height * .36, width < 700 ? .62 : .9, .34);
        paintCloud((1.12 - drift * .8) * width, height * .51, width < 700 ? .46 : .68, .24);
        paintBirdFlock(time, 1);
      } else if (phase === 'afternoon') {
        const afternoonProgress = Math.min(1, Math.max(0, (minutes - 720) / 270));
        paintSun(width * (.57 + afternoonProgress * .22), height * (.17 + afternoonProgress * .08), width < 700 ? 13 : 20, 0, .82);
        const drift = (time * .000005) % 1;
        paintCloud((-.18 + drift * 1.45) * width, height * .42, width < 700 ? .72 : 1.08, .57);
        paintCloud((.92 - drift * .75) * width, height * .22, width < 700 ? .5 : .78, .42);
        paintCloud((.25 + drift * .62) * width, height * .66, width < 700 ? .42 : .64, .31);
        paintAfternoonBalloon(time);
      } else if (phase === 'evening') {
        const eveningProgress = Math.min(1, Math.max(0, (minutes - 990) / 165));
        paintSun(width * (.76 + eveningProgress * .12), height * (.63 + eveningProgress * .12), width < 700 ? 15 : 23, .88, 1 - eveningProgress * .22);
        const drift = (time * .000006) % 1;
        paintCloud((-.15 + drift * 1.3) * width, height * .47, width < 700 ? .58 : .88, .24);
        paintFireflies(time);
      }

      const travel = scrollProgress * 1.65;
      const starVisibility = phase === 'night' ? 1 : phase === 'evening' ? .22 : phase === 'morning' ? .035 : 0;
      stars.forEach((star) => {
        if (starVisibility <= 0) return;
        const zoom = 1 + travel * star.depth * 1.15;
        const x = width * (.5 + (star.x - .5) * zoom);
        const yUnit = (star.y + travel * (.12 + star.depth * .28)) % 1.18 - .09;
        const y = height * yUnit;
        if (x < -8 || x > width + 8 || y < -8 || y > height + 8) return;
        const twinkle = reduceMotion ? .78 : .57 + Math.sin(time * .001 * star.pulse + star.phase) * .29;
        const radius = star.radius * (1 + travel * star.depth * .7);
        const [red, green, blue] = star.tone;
        if (star.glow) {
          const halo = context.createRadialGradient(x, y, 0, x, y, radius * 4.8);
          halo.addColorStop(0, `rgba(${red},${green},${blue},${Math.max(.12, twinkle * .28) * starVisibility})`);
          halo.addColorStop(1, `rgba(${red},${green},${blue},0)`);
          context.fillStyle = halo; context.beginPath(); context.arc(x, y, radius * 4.8, 0, Math.PI * 2); context.fill();
        }
        context.beginPath(); context.arc(x, y, radius, 0, Math.PI * 2);
        context.fillStyle = `rgba(${red},${green},${blue},${Math.max(.18, twinkle) * starVisibility})`; context.fill();
      });

      if (!reduceMotion && phase === 'night' && !impact && time >= nextImpact) launchImpact(time);

      if (!reduceMotion && phase === 'night' && !impact && !meteor && time >= nextMeteor) {
        launchMeteor(time);
      }
      if (phase === 'night' && meteor) {
        const age = (time - meteor.started) / meteor.duration;
        if (age >= 1) { meteor = null; nextMeteor = time + 1800 + Math.random() * 8200; }
        else {
          const headX = width * (meteor.x + age * meteor.dx); const headY = height * (meteor.y + age * meteor.dy);
          const directionAngle = Math.atan2(meteor.dy * height, meteor.dx * width);
          const tailX = headX - Math.cos(directionAngle) * meteor.length; const tailY = headY - Math.sin(directionAngle) * meteor.length;
          const alpha = Math.sin(age * Math.PI) * meteor.brightness;
          const paintTrail = (offset: number, opacity: number, lineWidth: number) => {
            const normalX = -Math.sin(directionAngle) * offset; const normalY = Math.cos(directionAngle) * offset;
            const trail = context.createLinearGradient(tailX + normalX, tailY + normalY, headX + normalX, headY + normalY);
            trail.addColorStop(0, 'rgba(154,204,247,0)'); trail.addColorStop(.72, `rgba(198,228,255,${alpha * opacity * .38})`); trail.addColorStop(1, `rgba(250,253,255,${alpha * opacity})`);
            context.strokeStyle = trail; context.lineWidth = lineWidth; context.beginPath(); context.moveTo(tailX + normalX, tailY + normalY); context.lineTo(headX + normalX, headY + normalY); context.stroke();
          };
          paintTrail(0, 1, 1 + meteor.brightness * 1.15);
          if (meteor.twin) paintTrail(5 + meteor.brightness * 5, .58, .75);
        }
      }

      if (!reduceMotion && phase === 'night') flights.forEach((flight, index) => {
        if (time < flight.delayUntil) return;
        flight.x += flight.speed * flight.direction;
        if ((flight.direction > 0 && flight.x > 1.22) || (flight.direction < 0 && flight.x < -.22)) {
          randomiseFlight(flight, time);
          return;
        }
        const x = flight.x * width; const y = (flight.y + Math.sin(time * .00012 + flight.phase) * .012) * height;
        const blink = Math.sin(time * .006 + flight.phase) > .64;
        const planeScale = flight.scale * (width < 700 ? 1.18 : 1.46);
        context.save(); context.translate(x, y); context.scale(flight.direction * planeScale, planeScale); context.rotate(flight.bank);
        context.fillStyle = 'rgba(181,199,218,.58)';
        context.beginPath(); context.moveTo(12, 0); context.quadraticCurveTo(5, -2, -9, -1.35); context.lineTo(-13, 0); context.lineTo(-9, 1.35); context.quadraticCurveTo(5, 2, 12, 0); context.fill();
        context.fillStyle = 'rgba(150,174,200,.52)';
        context.beginPath(); context.moveTo(2, 0); context.lineTo(-5, -7); context.lineTo(-8, -6.4); context.lineTo(-3, 0); context.lineTo(-7, 6.2); context.lineTo(-4, 6.8); context.lineTo(3, 0); context.fill();
        context.beginPath(); context.moveTo(-8, 0); context.lineTo(-12, -3); context.lineTo(-13, -2.5); context.lineTo(-10, .3); context.fill();
        context.restore();
        const lightRadius = (index === 0 ? 2.15 : 1.75) * flight.scale;
        const pulse = blink ? 1 : .22;
        context.shadowBlur = blink ? 10 : 3; context.shadowColor = 'rgba(255,74,86,.9)';
        context.fillStyle = `rgba(255,74,86,${pulse})`; context.beginPath(); context.arc(x - 5 * flight.direction * planeScale, y - 5.7 * planeScale, lightRadius, 0, Math.PI * 2); context.fill();
        context.shadowColor = 'rgba(84,255,171,.9)'; context.fillStyle = `rgba(84,255,171,${pulse})`; context.beginPath(); context.arc(x - 5 * flight.direction * planeScale, y + 5.7 * planeScale, lightRadius, 0, Math.PI * 2); context.fill();
        context.shadowColor = 'rgba(242,249,255,.9)'; context.fillStyle = `rgba(242,249,255,${blink ? .95 : .34})`; context.beginPath(); context.arc(x + 10 * flight.direction * planeScale, y, lightRadius * .78, 0, Math.PI * 2); context.fill();
        context.shadowBlur = 0;
      });

      if (phase === 'night' && impact) {
        const activeImpact = impact;
        const age = (time - activeImpact.started) / 2800;
        if (age >= 1) {
          impact = null;
          nextImpact = time + 43000 + Math.random() * 10000;
        } else {
          const targetX = activeImpact.x * width; const targetY = activeImpact.y * height;
          const approach = Math.min(1, age / .48);
          const ease = 1 - Math.pow(1 - approach, 3);
          const planeX = targetX - activeImpact.direction * (1 - ease) * Math.min(width * .34, 340);
          const planeY = targetY + Math.sin(approach * Math.PI) * 9 * activeImpact.scale;
          const planeScale = activeImpact.scale * (width < 700 ? 1.28 : 1.58);
          if (age < .55) {
            context.save(); context.translate(planeX, planeY); context.scale(activeImpact.direction * planeScale, planeScale); context.rotate(-activeImpact.direction * .025);
            context.fillStyle = 'rgba(205,216,226,.72)';
            context.beginPath(); context.moveTo(12, 0); context.quadraticCurveTo(5, -2, -9, -1.35); context.lineTo(-13, 0); context.lineTo(-9, 1.35); context.quadraticCurveTo(5, 2, 12, 0); context.fill();
            context.fillStyle = 'rgba(169,186,204,.68)';
            context.beginPath(); context.moveTo(2, 0); context.lineTo(-5, -7); context.lineTo(-8, -6.4); context.lineTo(-3, 0); context.lineTo(-7, 6.2); context.lineTo(-4, 6.8); context.lineTo(3, 0); context.fill();
            context.restore();
            const meteorStartX = targetX + activeImpact.meteorSide * Math.min(width * .42, 390); const meteorStartY = targetY - Math.min(height * .37, 310);
            const meteorX = meteorStartX + (targetX - meteorStartX) * ease; const meteorY = meteorStartY + (targetY - meteorStartY) * ease;
            const meteorAngle = Math.atan2(targetY - meteorStartY, targetX - meteorStartX);
            const tailLength = 70 + activeImpact.scale * 80;
            const meteorTailX = meteorX - Math.cos(meteorAngle) * tailLength; const meteorTailY = meteorY - Math.sin(meteorAngle) * tailLength;
            const collisionTrail = context.createLinearGradient(meteorTailX, meteorTailY, meteorX, meteorY);
            collisionTrail.addColorStop(0, 'rgba(151,204,255,0)'); collisionTrail.addColorStop(.65, 'rgba(207,233,255,.38)'); collisionTrail.addColorStop(1, 'rgba(255,255,255,.98)');
            context.strokeStyle = collisionTrail; context.lineWidth = 2.2; context.beginPath(); context.moveTo(meteorTailX, meteorTailY); context.lineTo(meteorX, meteorY); context.stroke();
          }
          if (age >= .46) {
            const blast = Math.min(1, (age - .46) / .54); const fade = Math.pow(1 - blast, 1.35); const blastRadius = (10 + blast * 82) * activeImpact.scale;
            const fire = context.createRadialGradient(targetX, targetY, 0, targetX, targetY, blastRadius);
            fire.addColorStop(0, `rgba(255,255,238,${fade})`); fire.addColorStop(.16, `rgba(255,218,112,${fade * .96})`); fire.addColorStop(.48, `rgba(255,99,32,${fade * .72})`); fire.addColorStop(1, 'rgba(93,28,15,0)');
            context.fillStyle = fire; context.beginPath(); context.arc(targetX, targetY, blastRadius, 0, Math.PI * 2); context.fill();
            context.strokeStyle = `rgba(255,191,92,${fade * .48})`; context.lineWidth = 1.5; context.beginPath(); context.arc(targetX, targetY, blastRadius * 1.12, 0, Math.PI * 2); context.stroke();
            activeImpact.sparks.forEach((spark) => {
              const distance = blast * blast * 88 * activeImpact.scale * spark.speed;
              const sparkX = targetX + Math.cos(spark.angle) * distance; const sparkY = targetY + Math.sin(spark.angle) * distance + blast * blast * 26;
              context.fillStyle = `rgba(255,${Math.round(105 + spark.heat * 130)},${Math.round(25 + spark.heat * 70)},${fade * spark.heat})`;
              context.beginPath(); context.arc(sparkX, sparkY, spark.size * (1 - blast * .55), 0, Math.PI * 2); context.fill();
            });
          }
        }
      }
      if (!reduceMotion) frame = window.requestAnimationFrame(draw);
    };
    const updateVisibility = () => {
      pageVisible = !document.hidden;
      if (pageVisible && !reduceMotion && !frame) frame = window.requestAnimationFrame(draw);
      if (!pageVisible && frame) { window.cancelAnimationFrame(frame); frame = 0; }
    };
    buildField(); updateScroll();
    window.addEventListener('resize', buildField); window.addEventListener('scroll', updateScroll, { passive: true });
    document.addEventListener('visibilitychange', updateVisibility);
    frame = window.requestAnimationFrame(draw);
    return () => { window.cancelAnimationFrame(frame); window.removeEventListener('resize', buildField); window.removeEventListener('scroll', updateScroll); document.removeEventListener('visibilitychange', updateVisibility); };
  }, [mode]);
  return <canvas ref={canvasRef} className="ax-night-canvas" aria-hidden="true"/>;
}

export function AxiomLandingPage() {
  const navigate = useNavigate();
  const [skyMode, setSkyMode] = useState<SkyMode>('auto');
  const [clockTick, setClockTick] = useState(0);
  useEffect(() => { const timer = window.setInterval(() => setClockTick((tick) => tick + 1), 30000); return () => window.clearInterval(timer); }, []);
  const skyClock = useMemo(() => getSkyClock(skyMode), [skyMode, clockTick]);
  const indiaTime = useMemo(() => new Intl.DateTimeFormat('en-IN', { timeZone: 'Asia/Kolkata', hour: 'numeric', minute: '2-digit' }).format(new Date()), [clockTick]);
  return <main className="ax-sky-home" data-sky-phase={skyClock.phase}>
    <NightSkyCanvas mode={skyMode}/>
    <div className="ax-earth-wrap" aria-hidden="true"><div className="ax-earth-globe"><div className="ax-earth-map" style={{ backgroundImage: `url(${earthTexture})` }}/><div className="ax-earth-lights" style={{ backgroundImage: `url(${earthNightLights})` }}/></div></div>
    <header className="ax-sky-header"><span>ASYMPTOTES · BMSIT</span><div><small>{skyMode === 'auto' ? `${indiaTime} IST` : `${skyClock.phase} preview`}</small><button onClick={() => navigate('/login')}>Enter workspace <ArrowRight size={16}/></button></div></header>
    <nav className="ax-sky-modes" aria-label="Sky time"><span>SKY</span>{SKY_MODES.map((option) => <button key={option.value} className={skyMode === option.value ? 'active' : ''} aria-pressed={skyMode === option.value} onClick={() => setSkyMode(option.value)}>{option.label}</button>)}</nav>
    <section className="ax-sky-intro"><div><span>PROJECT AXIOM</span><h1>Look up.<br/><em>Then build forward.</em></h1><p>A private research and product initiative for the people building Asymptotes from within.</p><button onClick={() => navigate('/login')}>Enter Project Axiom <ArrowRight size={17}/></button></div><small>SCROLL THROUGH THE SKY</small></section>
    <div className="ax-sky-distance" aria-hidden="true"/>
  </main>;
}

export function AxiomLandingPageAtomArchive() {
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
              <linearGradient id="axiomStringA" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#67e8f9"/><stop offset=".48" stopColor="#c4b5fd"/><stop offset="1" stopColor="#f0abfc"/></linearGradient>
              <linearGradient id="axiomStringB" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#e0f2fe"/><stop offset=".44" stopColor="#a78bfa"/><stop offset="1" stopColor="#fb7185"/></linearGradient>
              <radialGradient id="axiomCore" cx="42%" cy="36%"><stop offset="0" stopColor="#ffffff"/><stop offset=".18" stopColor="#67e8f9"/><stop offset=".5" stopColor="#a78bfa"/><stop offset="1" stopColor="#071431" stopOpacity=".15"/></radialGradient>
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
          <div className="ax-orbit-core"><Orbit size={27}/><b>STRING FIELD</b><small>MODES IN SUPERPOSITION</small></div>
        </div></div>
        <div className="ax-atom-caption"><span>STRING FIELD · 01</span><p><b>Many vibrations. One system.</b> Inspired by string theory, this living atom visualises Project Axiom: individual ideas move differently, yet combine to create one coherent body of work.</p><small>Artistic interpretation—not a scientific simulation.</small></div>
      </div>
    </section>

    <StringTheoryLab/>

    <section className="ax-statement ax-scroll"><span>THE PREMISE</span><p>Events create moments. <em>Communities create momentum.</em></p><small>Project Axiom gives our internal team the time, trust and structure to create work that lasts beyond one event.</small></section>

    <section className="ax-paths ax-scroll">
      <div className="ax-section-intro"><span>CHOOSE A DIRECTION</span><h2>Two paths.<br/><em>Equal ambition.</em></h2><p>A project follows one clear track. The difference is the output—not the value.</p></div>
      <article className="research ax-glass" onPointerMove={interactivePointer}><div className="ax-path-number">R/01</div><FlaskConical/><span>RESEARCH</span><h3>Turn a question into knowledge.</h3><p>Investigate a meaningful problem, test assumptions and produce findings the club can learn from or act upon.</p><small>QUESTION · METHOD · EVIDENCE · INSIGHT</small></article>
      <article className="product ax-glass" onPointerMove={interactivePointer}><div className="ax-path-number">P/02</div><Layers3/><span>PRODUCT · SOFTWARE OR HARDWARE</span><h3>Turn a need into something useful.</h3><p>Design, prototype and deliver one practical software or hardware product that improves how the club works.</p><small>NEED · DESIGN · PROTOTYPE · IMPACT</small></article>
    </section>

    <section className="ax-process ax-scroll"><div className="ax-section-intro"><span>THE SYSTEM</span><h2>Preference, purpose<br/>and human judgment.</h2></div><div className="ax-process-line">{[
      ['01','Frame','Mentors submit one concise research or product challenge.'],['02','Explore','Members read every released project under an originality agreement.'],['03','Respond','Each member ranks up to three and explains a solution and contribution.'],['04','Match','Preference fit, mentor review and balanced capacity shape the teams.'],['05','Create','Teams work through checkpoints and present at the internal showcase.'],
    ].map(([n,title,copy]) => <article key={n}><b>{n}</b><div><span>{title}</span><p>{copy}</p></div></article>)}</div></section>

    <section className="ax-window ax-scroll ax-glass" onPointerMove={interactivePointer}><div><div className="ax-kicker"><CalendarClock size={14}/> CURRENT WINDOW</div><h2>Built for the people<br/><em>already building the club.</em></h2><p>Private access for the approved Asymptotes core roster.</p></div><button className="ax-primary" onClick={() => navigate('/login')}>Open your invitation <ChevronRight size={18}/></button></section>
    <footer className="ax-footer"><AxiomLogo/><p>Think · build · share · grow</p></footer>
  </main>;
}

function ProjectJourney({ deadlines, active }: { deadlines: Deadlines; active: number }) {
  const items = [
    ['01','Publish openly','Any participant can publish any number of research or product project briefs.','Open now'],
    ['02','Apply with intent','Anyone can apply to any number of projects with their own solution and contribution.','Open now'],
    ['03','Select a team','Each publisher reviews their applicants and selects up to three people.','Publisher controlled'],
    ['04','Finalise teams','A publisher plus up to three selected applicants makes a four-person team.',formatDeadline(deadlines.team_finalization)],
    ['05','Review one','Teams present the problem framing, plan and early evidence.','29 Nov 2026'],
    ['06','Review two','An online review after semester examinations checks progress, evidence and execution.','After semester ends · Online'],
    ['07','Final showcase','Completed work is demonstrated, recognised and the winning project is announced.','First week of next semester'],
  ];
  return <section className="ax-journey ax-scroll"><div className="ax-section-title"><div><span>PROJECT LIFECYCLE</span><h2>From decision<br/><em>to demonstration.</em></h2></div><p>Every stage leaves a clear output. Nothing disappears after team formation.</p></div><div className="ax-journey-track">{items.map(([number,title,copy,date],index)=><article className={index<active?'complete':index===active?'current':''} key={number}><header><b>{number}</b><span>{index<active?<Check size={15}/>:index===active?'NOW':'NEXT'}</span></header><h3>{title}</h3><p>{copy}</p><small>{date}</small></article>)}</div></section>;
}

function ParticipantProjectCall({ onSaved }: { onSaved: () => void }) {
  const blank={title:'',domain:'',project_track:'RESEARCH' as 'RESEARCH'|'PRODUCT',problem_statement:'',project_context:'',helpful_skills:''};
  const [open,setOpen]=useState(false); const [draft,setDraft]=useState(blank);
  const publishRequestId=useRef<string|null>(null);
  const pendingPublish=false;
  const [busy,setBusy]=useState(false); const [error,setError]=useState(''); const [message,setMessage]=useState('');
  const psWords=countWords(draft.problem_statement); const contextWords=countWords(draft.project_context);
  const formReady=draft.title.trim().length>=4&&draft.domain.trim().length>=2&&draft.problem_statement.trim().length>=20&&draft.project_context.trim().length>=20&&psWords<=44&&contextWords<=88;
  async function save(){if(!formReady){setError('Complete every required field before publishing. The problem statement and explanation must each contain at least 20 characters.');return;}setBusy(true);setError('');setMessage('');publishRequestId.current??=crypto.randomUUID();const payload={...draft,submit:true,client_request_id:publishRequestId.current};try{const created=await request<{id:string}>('/axiom/projects','POST',payload,{retry:true,timeoutMs:90_000});if(!created?.id)throw new Error('The database did not confirm the new project. Nothing was cleared—please try again.');publishRequestId.current=null;await onSaved();setDraft(blank);setOpen(false);setMessage('Project published and confirmed in the project board.');}catch(item){setError(item instanceof Error?item.message:'The project was not published. Your form is still here—please try again.');}finally{setBusy(false);}}
  return <section className="ax-editor ax-scroll ax-glass" onPointerMove={interactivePointer}>
    <div className="ax-section-title"><div><span>OPEN PROJECT BOARD</span><h2>Build a team around<br/><em>your own idea.</em></h2></div><p>Publish as many research or product briefs as you need. You will have full control over selecting applicants for each project.</p></div>
    {!open?<button className="ax-primary" disabled={pendingPublish} onClick={()=>setOpen(true)}>{pendingPublish?'Publishing saved project…':'Publish a project'} <ArrowRight size={17}/></button>:<><div className="ax-editor-grid"><label>Project title<input required minLength={4} maxLength={140} value={draft.title} onChange={e=>setDraft({...draft,title:e.target.value})} placeholder="A short, memorable title"/></label><label>Domain<input required minLength={2} maxLength={100} value={draft.domain} onChange={e=>setDraft({...draft,domain:e.target.value})} placeholder="AI, education, accessibility…"/></label><label className="wide">Project path<select value={draft.project_track} onChange={e=>setDraft({...draft,project_track:e.target.value as 'RESEARCH'|'PRODUCT'})}><option value="RESEARCH">Research — investigate and produce a useful finding</option><option value="PRODUCT">Product — build a software or hardware solution</option></select></label><label className="wide">Problem statement<textarea required minLength={20} maxLength={1200} value={draft.problem_statement} onChange={e=>setDraft({...draft,problem_statement:e.target.value})} placeholder="What specific problem should your team solve?"/><small className={psWords>44?'over':''}>{psWords} / 44 words · minimum 20 characters</small></label><label className="wide">Why this matters and what success looks like<textarea required minLength={20} maxLength={2400} value={draft.project_context} onChange={e=>setDraft({...draft,project_context:e.target.value})} placeholder="Explain the need, constraints and intended outcome."/><small className={contextWords>88?'over':''}>{contextWords} / 88 words · minimum 20 characters</small></label><label className="wide">Helpful skills — not eligibility requirements<input maxLength={600} value={draft.helpful_skills} onChange={e=>setDraft({...draft,helpful_skills:e.target.value})} placeholder="Research, frontend, statistics, electronics…"/></label></div><div className="ax-editor-actions"><span><ShieldCheck/> Your project will be visible to signed participants.</span><button className="ax-primary compact" disabled={busy||!formReady} onClick={()=>void save()}>{busy?'Publishing…':'Publish project'}</button></div></>}
    {error&&<div className="ax-alert"><X/>{error}</div>}{message&&<div className="ax-password-success"><Check/>{message}</div>}
  </section>;
}

function ParticipantWorkspace() {
  const [workspace,setWorkspace]=useState<ProjectWorkspace|null>(null); const [applications,setApplications]=useState<Application[]>([]); const [myProjects,setMyProjects]=useState<Array<Project & { applications:{account_id:string;name:string;proposed_solution:string;contribution:string;selected:boolean}[];selection_open:boolean}>>([]);
  const [busy,setBusy]=useState(false); const [error,setError]=useState(''); const [message,setMessage]=useState(''); const [signatureName,setSignatureName]=useState(''); const [signatureEmail,setSignatureEmail]=useState(''); const [agreementChecked,setAgreementChecked]=useState(false); const [selectedProject,setSelectedProject]=useState<Project|null>(null);
  const load=async()=>{try{const next=await request<ProjectWorkspace>('/axiom/projects');setWorkspace(next);setApplications(next.applications);if(next.agreement_accepted){const mine=await request<{projects:Array<Project & {applications:{account_id:string;name:string;proposed_solution:string;contribution:string;selected:boolean}[];selection_open:boolean}>}>('/axiom/my-projects');setMyProjects(mine.projects);}}catch(item){setError(item instanceof Error?item.message:'Could not load projects.');}};
  useEffect(()=>{void load();},[]);
  async function accept(){setBusy(true);setError('');try{await request('/axiom/agreement','POST',{accepted:agreementChecked,full_name:signatureName,college_email:signatureEmail},{retry:true,timeoutMs:60_000});await load();}catch(item){setError(item instanceof Error?item.message:'Could not record your signature.');}finally{setBusy(false);}}
  function updateApplication(id:string,patch:Partial<Application>){setApplications(applications.some(item=>item.statement_id===id)?applications.map(item=>item.statement_id===id?{...item,...patch}:item):[...applications,{statement_id:id,proposed_solution:'',contribution:'',...patch}]);}
  async function apply(project:Project){const application=applications.find(item=>item.statement_id===project.id);if(!application)return;setBusy(true);setError('');setMessage('');try{await request(`/axiom/projects/${project.id}/application`,'PUT',application,{retry:true,timeoutMs:60_000});setMessage(`Your application for ${project.title} has been recorded.`);await load();}catch(item){setError(item instanceof Error?item.message:'Could not record your application.');}finally{setBusy(false);}}
  async function saveSelection(projectId:string,ids:string[]){setBusy(true);setError('');try{await request(`/axiom/projects/${projectId}/selections`,'PUT',{participant_account_ids:ids},{retry:true,timeoutMs:60_000});setMessage('Your project team selection has been saved.');await load();}catch(item){setError(item instanceof Error?item.message:'Could not save team selection.');}finally{setBusy(false);}}
  if(!workspace)return <section className="ax-member-wait ax-scroll"><Orbit/><h2>Opening the project vault…</h2>{error&&<p>{error}</p>}</section>;
  if(!workspace.agreement_accepted)return <section className="ax-agreement ax-scroll ax-glass" onPointerMove={interactivePointer}><div className="ax-agreement-seal"><ShieldCheck/></div><div><span>CONFIDENTIAL PROJECT ACCESS</span><h2>Sign before<br/><em>you explore.</em></h2><p>Project briefs are confidential Club Asymptotes material. Access is personal to your signed-in college account and requires this recorded acknowledgement.</p><div className="ax-contract"><b>Project Axiom — Confidentiality & Intellectual-Property Acknowledgement</b><p>I will use project statements, solution approaches, research directions, product concepts and related material only for Project Axiom. I will not copy, publish, forward, distribute, submit, commercialise, present as my own or use any material outside this programme without written permission from its author and Club Asymptotes.</p><p>I confirm that my proposal and contribution are my own work. My signed name, college email, agreement version, time and an integrity-protected evidence record will be retained.</p></div><div className="ax-editor-grid"><label>Full name — exactly as on your account<input value={signatureName} onChange={event=>setSignatureName(event.target.value)} placeholder="Type your full name"/></label><label>College email — exactly as on your account<input value={signatureEmail} onChange={event=>setSignatureEmail(event.target.value)} placeholder="Type your college email"/></label></div><label><input type="checkbox" checked={agreementChecked} onChange={event=>setAgreementChecked(event.target.checked)}/> I have read this acknowledgement and electronically sign it using the name and college email above.</label><button className="ax-primary" disabled={busy||!agreementChecked||!signatureName.trim()||!signatureEmail.trim()} onClick={()=>void accept()}>{busy?'Recording signature…':'Sign and access projects'} <ArrowRight size={17}/></button>{error&&<div className="ax-alert"><X/>{error}</div>}</div></section>;
  const activeApplication=selectedProject?applications.find(item=>item.statement_id===selectedProject.id):undefined;
  const applicationWords=activeApplication?countWords(activeApplication.proposed_solution)+countWords(activeApplication.contribution):0;
  return <><ParticipantProjectCall onSaved={load}/><section className="ax-project-workspace ax-scroll">
    <div className="ax-section-title"><div><span>PROJECT EXPLORER</span><h2>Find an idea worth<br/><em>building together.</em></h2></div><p>Open a project to read its full brief, then apply with your own solution and contribution.</p></div>
    {workspace.projects.length===0?<div className="ax-empty-projects"><FileText/><h3>No submitted projects yet.</h3><p>Be the first to publish one.</p></div>:<div className="ax-project-grid">{workspace.projects.map((project,index)=><button className="ax-project-card ax-glass" type="button" key={project.id} onPointerMove={interactivePointer} onClick={()=>{setError('');setMessage('');setSelectedProject(project);}} style={{'--delay':`${index*.06}s`} as CSSProperties}>
      <header><span>{project.project_track==='RESEARCH'?'RESEARCH':'PRODUCT'}</span><small>{project.domain}</small><ChevronRight size={18}/></header><div className="ax-project-card-mark">{String(index+1).padStart(2,'0')}</div><h3>{project.title}</h3><p>{project.problem_statement}</p><div className="ax-project-meta"><span>PUBLISHED BY</span><b>{project.publisher_name}</b></div><footer>Open project brief <ArrowRight size={15}/></footer>
    </button>)}</div>}
    {error&&<div className="ax-alert"><X/>{error}</div>}{message&&<div className="ax-password-success"><Check/>{message}</div>}
  </section>{selectedProject&&<div className="ax-project-overlay" role="dialog" aria-modal="true" aria-label={`${selectedProject.title} project brief`} onMouseDown={event=>{if(event.target===event.currentTarget)setSelectedProject(null);}}><article className="ax-project-sheet ax-glass" onPointerMove={interactivePointer}>
    <button className="ax-project-close" type="button" aria-label="Close project brief" onClick={()=>setSelectedProject(null)}><X size={20}/></button><header><span>{selectedProject.project_track==='RESEARCH'?'RESEARCH PROJECT':'PRODUCT PROJECT'}</span><small>{selectedProject.domain}</small></header><div className="ax-project-sheet-title"><div className="ax-project-orb"><Sparkles size={24}/></div><div><p>PUBLISHED BY <b>{selectedProject.publisher_name}</b></p><h2>{selectedProject.title}</h2></div></div><section><span>THE PROBLEM</span><p>{selectedProject.problem_statement}</p></section><section><span>THE BRIEF</span><p>{selectedProject.project_context}</p></section><section className="ax-skills"><span>HELPFUL SKILLS</span><p>{selectedProject.helpful_skills||'No fixed skill requirements — bring curiosity and a useful point of view.'}</p></section>{selectedProject.is_publisher?<div className="ax-password-success"><Check/> This is your project. Review applicants in <b>My Projects</b> below.</div>:<div className="ax-response-editor ax-project-application">{error&&<div className="ax-alert" role="alert">{error}</div>}{message&&<div className="ax-password-success" role="status">{message}</div>}<div className="ax-application-head"><span>YOUR APPLICATION</span><p>Show the publisher how you would approach this work.</p></div><label>Your proposed solution<textarea value={activeApplication?.proposed_solution||''} onChange={event=>updateApplication(selectedProject.id,{proposed_solution:event.target.value})} placeholder="How would you approach this problem?"/></label><label>How you would contribute<textarea value={activeApplication?.contribution||''} onChange={event=>updateApplication(selectedProject.id,{contribution:event.target.value})} placeholder="What will you bring to this team?"/></label><small className={applicationWords>88?'over':''}>{applicationWords} / 88 words</small><button className="ax-primary" disabled={busy||!activeApplication?.proposed_solution.trim()||!activeApplication?.contribution.trim()||applicationWords>88} onClick={()=>void apply(selectedProject)}>{activeApplication?'Update application':'Apply to project'} <ArrowRight size={16}/></button></div>}</article></div>}<section className="ax-matching ax-scroll"><div className="ax-section-title"><div><span>MY PROJECTS</span><h2>Choose your<br/><em>team.</em></h2></div><p>Select up to three applicants per project. With you, each team can contain at most four people. Selections close {formatDeadline(workspace.team_finalization_deadline)}.</p></div>{myProjects.length===0?<div className="ax-empty-projects"><FileText/><h3>You have not published a project yet.</h3></div>:<div className="ax-matching-grid">{myProjects.map(project=>{const selected=project.applications.filter(item=>item.selected).map(item=>item.account_id);return <article key={project.id}><header><span>{project.project_track}</span><b>{selected.length+1}/4</b></header><h3>{project.title}</h3>{project.applications.length?project.applications.map(applicant=><label className="ax-match-person" key={applicant.account_id}><input type="checkbox" checked={selected.includes(applicant.account_id)} disabled={!project.selection_open||(!selected.includes(applicant.account_id)&&selected.length>=3)} onChange={event=>{const next=event.target.checked?[...selected,applicant.account_id]:selected.filter(item=>item!==applicant.account_id);setMyProjects(myProjects.map(item=>item.id===project.id?{...item,applications:item.applications.map(candidate=>({...candidate,selected:next.includes(candidate.account_id)}))}:item));}}/><span>{applicant.name.split(' ').map(part=>part[0]).slice(0,2).join('')}</span><b>{applicant.name}</b><small>{applicant.proposed_solution}</small></label>):<p>No applications yet.</p>}<button className="ax-primary compact" disabled={busy||!project.selection_open} onClick={()=>void saveSelection(project.id,project.applications.filter(item=>item.selected).map(item=>item.account_id))}>Save team · {selected.length+1}/4</button></article>})}</div>}</section></>;
}

export function AxiomDashboardPage() {
  const navigate=useNavigate(); const root=useRef<HTMLElement>(null); useAxiomMotion(root);
  const [data,setData]=useState<AxiomMe|null>(null); const [error,setError]=useState('');
  const load=async()=>{try{const next=await request<AxiomMe>('/axiom/me');if(next.is_super_admin){navigate('/axiom/control',{replace:true});return;}setData(next);}catch(item){setError(item instanceof Error?item.message:'Could not load Project Axiom.');}};
  useEffect(()=>{if(!getSession())navigate('/login',{replace:true});else void load();},[]);
  if(!data)return <main className="ax-site ax-dashboard"><AxiomBackdrop/><AxiomHeader compact/><div className="ax-loading"><Orbit/> Loading your workspace…{error&&<p>{error}</p>}</div></main>;
  return <main ref={root} className="ax-site ax-dashboard ax-premium" onPointerMove={interactivePointer}><AxiomBackdrop/><AxiomHeader compact/>
    <section className="ax-dash-head"><div><div className="ax-kicker"><CircleDot/> PRIVATE AXIOM WORKSPACE</div><h1>Welcome, <em>{data.display_name.split(' ')[0]}.</em></h1><p>{data.college_email}</p></div><div className="ax-status-pill"><span/><div><small>CURRENT STATUS</small><b>PARTICIPANT</b></div></div></section>
    <ProjectJourney deadlines={data.deadlines} active={1}/>{error&&<div className="ax-alert"><X/>{error}</div>}
    <ParticipantWorkspace/>
    <PasswordPanel/>
  </main>;
}

export function AxiomControlPage() {
  const navigate=useNavigate(); const root=useRef<HTMLElement>(null); useAxiomMotion(root); const [data,setData]=useState<ControlOverview|null>(null); const [error,setError]=useState('');
  useEffect(()=>{request<ControlOverview>('/axiom/control/overview').then(setData).catch(item=>setError(item.message));},[]);
  const ready=useMemo(()=>data?.people.filter(person=>person.role_choice!=='PENDING').length||0,[data]);
  return <main ref={root} className="ax-site ax-dashboard ax-premium" onPointerMove={interactivePointer}><AxiomBackdrop/><AxiomHeader compact/><section className="ax-dash-head"><div><div className="ax-kicker"><ShieldCheck/> CLUB COUNCIL CONTROL</div><h1>Axiom, <em>at a glance.</em></h1><p>Open projects. Publisher-controlled teams. Human final judgment.</p></div><button className="ax-secondary" onClick={()=>navigate('/')}>Public page</button></section>{error&&<div className="ax-alert"><X/>{error}</div>}{data&&<><ProjectJourney deadlines={{team_finalization:'2026-11-06T15:00:00+05:30'}} active={Math.min(3,ready?1:0)}/><section className="ax-stat-grid ax-scroll"><div><small>ACTIVE ROSTER</small><b>{data.total}</b><span>approved accounts</span></div><div><small>PARTICIPANTS</small><b>{ready}</b><span>open project board</span></div><div><small>PROJECTS</small><b>{data.submitted_statements}</b><span>published statements</span></div><div><small>RESPONSES</small><b>{data.preference_count}</b><span>legacy records</span></div></section>
    <section className="ax-matching ax-scroll"><div className="ax-section-title"><div><span>PROJECT SELECTIONS</span><h2>Publisher-led teams.</h2></div><p>Each project publisher reviews applications and may select up to three applicants. With the publisher, a team can have at most four people.</p></div>{data.matching_preview.length===0?<div className="ax-empty-projects"><Orbit/><h3>Waiting for published projects.</h3></div>:<div className="ax-matching-grid">{data.matching_preview.map(team=><article key={team.statement_id}><header><span>{team.track}</span><b>{team.members.length + 1}/4</b></header><h3>{team.title}</h3>{team.members.length?team.members.map(member=><div className="ax-match-person" key={member.name}><span>{member.name.split(' ').map(part=>part[0]).slice(0,2).join('')}</span><b>{member.name}</b><small>Selected applicant</small></div>):<p>No applicants selected yet.</p>}</article>)}</div>}</section>
    <section className="ax-roster ax-scroll"><div className="ax-section-title"><div><span>LIVE ROSTER</span><h2>People and decisions.</h2></div><p>Legacy event accounts remain paused.</p></div><div className="ax-roster-table">{data.people.map(person=><article key={person.email}><div className="ax-avatar">{person.name.split(' ').slice(0,2).map(part=>part[0]).join('')}</div><div><b>{person.name}</b><small>{person.email}</small></div><span>{person.roster_type==='MENTOR_CANDIDATE'?'CANDIDATE':'MEMBER'}</span><em className={person.role_choice.toLowerCase()}>{person.role_choice.replace('_',' ')}</em></article>)}</div></section><PasswordPanel/></>}</main>;
}

export function PastEventsPage() {
  const navigate=useNavigate(); const root=useRef<HTMLElement>(null); useAxiomMotion(root);
  return <main ref={root} className="ax-site ax-premium"><AxiomBackdrop/><AxiomHeader/><section className="ax-past-hero"><div className="ax-kicker"><History/> PAST EVENTS · ARCHIVE</div><h1>Experiments worth <em>remembering.</em></h1><p>Previous event systems are preserved as read-only records while Project Axiom becomes the current internal workspace.</p></section><section className="ax-past-card ax-scroll"><div className="ax-past-number">01</div><div><span>2026 · TWO-DAY FLAGSHIP</span><h2>ODDyssey</h2><p>A digitised treasure hunt, mathematical Cabo deck, live challenge stations and a legal-reasoning finale.</p></div><div className="ax-archive-badge"><ShieldCheck/> READ-ONLY ARCHIVE</div></section><button className="ax-secondary ax-back" onClick={()=>navigate('/')}><MoveRight/> Return to Project Axiom</button></main>;
}
