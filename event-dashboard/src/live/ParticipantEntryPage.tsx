import { useEffect, useState } from 'react';
import { LogOut, MapPin, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { LiveShell, Mark } from './LiveShell';
import { ParticipantPage } from './ParticipantPage';
import { clearSession, getSession, request } from './eventApi';

type Assignment = { participant_id: string; participant_name: string; table_number: number };
type Round2Assignment = { available: boolean; team_identifier: string | null; team_name: string; assignments: Assignment[] };

export function ParticipantEntryPage() {
  const [round2, setRound2] = useState<Round2Assignment | null>(null);
  const [checking, setChecking] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    if (getSession()?.role !== 'PARTICIPANT') { navigate('/login', { replace: true }); return; }
    request<Round2Assignment>('/r2/participant/assignment')
      .then(setRound2)
      .catch(() => setRound2(null))
      .finally(() => setChecking(false));
  }, []);

  if (checking) return <LiveShell><main className="mobile-page"><div className="load-card live-reveal">Checking your current round...</div></main></LiveShell>;
  if (!round2?.available) return <ParticipantPage />;

  return <LiveShell><main className="mobile-page participant-page"><header className="topbar live-reveal"><Mark/><button aria-label="Sign out" onClick={() => { clearSession(); navigate('/login'); }}><LogOut size={18}/></button></header>
    <section className="staff-hero live-reveal"><div className="eyebrow"><Users size={14}/> ROUND 02 · CABO</div><h1>Your table <span>assignments.</span></h1><p><strong>{round2.team_identifier}</strong> · {round2.team_name}</p><p>Each member must report to the table shown beside their name. Keep this screen ready while you separate.</p></section>
    <section className="answer-card live-reveal r2-score-card"><div className="eyebrow"><MapPin size={14}/> MEMBER TABLES</div><h2>Find your Cabo table</h2>{round2.assignments.map(item => <div className="r2-player" key={item.participant_id}><span><b>{item.participant_name}</b></span><small>TABLE {String(item.table_number).padStart(2, '0')}</small></div>)}</section>
  </main></LiveShell>;
}
