import { ArrowRight, ExternalLink, Instagram, MapPinned, ShieldCheck, Sparkles, Trophy } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import instagramQr from '../assets/asymptotes-instagram-qr.png';
import { LiveShell, Mark } from './LiveShell';

const modules = [
  ['01', 'Treasure Hunt', 'Decode the route, verify each station QR, and submit the event code earned from the physical puzzle. The first 16 final submissions qualify.', true],
  ['02', 'Round two', 'Rules are announced only to Round 1 qualifiers.', false],
  ['03', 'Round three', 'Rules are announced only to continuing teams.', false],
  ['04', 'Final round', 'The final challenge will be unveiled during the event.', false],
];

export function LandingPage() {
  const navigate = useNavigate();
  return <LiveShell><main className="landing-page"><header className="landing-nav live-reveal"><Mark/><button className="nav-login" onClick={() => navigate('/login')}>Event login <ArrowRight size={16}/></button></header>
    <section className="landing-hero live-reveal"><div className="hero-kicker"><Sparkles size={15}/> BMSIT · BENGALURU</div><h1>Follow the <span>unseen.</span></h1><p>ASYMPTOTES is a four-round campus challenge built for sharp minds, fast teams, and careful observation.</p><div className="hero-actions"><button className="primary-button" onClick={() => navigate('/login')}>Enter the event <ArrowRight size={17}/></button><a className="outline-link" href="https://instagram.com/asymptotes_bmsit" target="_blank" rel="noreferrer"><Instagram size={17}/> Updates</a></div><div className="hero-orbit"><span/><span/><span/><MapPinned size={30}/></div></section>
    <section className="round-grid">{modules.map(([number, title, detail, active]) => <article className={`round-card live-reveal ${active ? 'active' : ''}`} key={String(number)}><div><em>ROUND {number}</em>{active ? <ShieldCheck size={20}/> : <Trophy size={20}/>}</div><h2>{title}</h2><p>{detail}</p></article>)}</section>
    <section className="r1-rules live-reveal" aria-labelledby="r1-rules-title"><div className="eyebrow"><ShieldCheck size={14}/> ROUND 01 · TREASURE HUNT</div><h2 id="r1-rules-title">How to play</h2><ol><li>Solve the questions in your assigned physical envelope and work out the required event code on paper first.</li><li>At each active location, scan the single QR shown by the station admin. It works only for a team assigned to that location at that time.</li><li>Enter the event code only after scanning. Capital letters do not matter; for the final checkpoint, separate the two parts with a dash or a space.</li><li>Every incorrect submitted code deducts <strong>5 points</strong>. Each checkpoint allows up to three submissions, then event staff must unlock it.</li><li>Your next clue appears only after a correct submission. The first 16 teams to complete the final checkpoint qualify.</li></ol><p className="r1-rules-note">Do not share, photograph, or publish physical puzzle answers. Official results and updates are posted on Instagram.</p></section>
    <section className="public-info live-reveal"><div><Instagram size={20}/><div><strong>Official updates</strong><span>@ASYMPTOTES_BMSIT</span></div></div><img src={instagramQr} alt="Instagram QR for ASYMPTOTES_BMSIT"/><a href="https://www.bmsit.ac.in/" target="_blank" rel="noreferrer">BMSIT website <ExternalLink size={14}/></a></section>
  </main></LiveShell>;
}

export function ResultsPage() {
  const location = useLocation();
  const message = (location.state as { message?: string } | null)?.message || 'Round 1 is complete for this team.';
  return <LiveShell><main className="auth-page"><Mark/><section className="results-card live-reveal"><div className="finish-icon"><Trophy size={29}/></div><div className="eyebrow">ROUND 01 RESULTS</div><h1>Watch <span>Instagram.</span></h1><p>{message} The next announcement will be published through the official ASYMPTOTES account.</p><img className="instagram-qr" src={instagramQr} alt="Instagram QR for ASYMPTOTES_BMSIT"/><a className="insta-handle" href="https://instagram.com/asymptotes_bmsit" target="_blank" rel="noreferrer"><Instagram size={20}/>@ASYMPTOTES_BMSIT</a></section></main></LiveShell>;
}
