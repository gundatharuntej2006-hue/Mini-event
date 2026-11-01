import { lazy, Suspense, type ComponentType } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

function lazyNamed<T extends Record<string, ComponentType<object>>>(loader: () => Promise<T>, name: keyof T) {
  return lazy(async () => ({ default: (await loader())[name] }));
}

const LoginPage = lazyNamed(() => import('../live/LoginPage'), 'LoginPage');
const ParticipantEntryPage = lazyNamed(() => import('../live/ParticipantEntryPage'), 'ParticipantEntryPage');
const AdminPage = lazyNamed(() => import('../live/StaffPagesV2'), 'AdminPage');
const SuperAdminPage = lazyNamed(() => import('../live/StaffPagesV2'), 'SuperAdminPage');
const ResultsPage = lazyNamed(() => import('../live/PublicPages'), 'ResultsPage');
const AxiomLandingPage = lazyNamed(() => import('../axiom/AxiomPages'), 'AxiomLandingPage');
const AxiomDashboardPage = lazyNamed(() => import('../axiom/AxiomPages'), 'AxiomDashboardPage');
const AxiomControlPage = lazyNamed(() => import('../axiom/AxiomPages'), 'AxiomControlPage');
const PastEventsPage = lazyNamed(() => import('../axiom/AxiomPages'), 'PastEventsPage');
const AccountManagementPage = lazyNamed(() => import('../live/AccountManagementPage'), 'AccountManagementPage');
const Round2SuperPage = lazyNamed(() => import('../live/Round2Pages'), 'Round2SuperPage');
const Round2AdminPage = lazyNamed(() => import('../live/Round2Pages'), 'Round2AdminPage');
const Round3SuperPage = lazyNamed(() => import('../live/Round3Pages'), 'Round3SuperPage');
const Round3PuzzleParticipantPage = lazyNamed(() => import('../live/Round3PuzzlePages'), 'Round3PuzzleParticipantPage');
const Round3PuzzleStationPage = lazyNamed(() => import('../live/Round3PuzzlePages'), 'Round3PuzzleStationPage');
const Round3PuzzleDemoPage = lazyNamed(() => import('../live/Round3PuzzlePages'), 'Round3PuzzleDemoPage');

function RouteFallback() {
  return <main className="route-loading" aria-live="polite"><span />Opening workspace…</main>;
}

export function AppRoutes() {
  return (
    <Suspense fallback={<RouteFallback />}><Routes>
      <Route path="/" element={<AxiomLandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/axiom" element={<AxiomDashboardPage />} />
      <Route path="/axiom/control" element={<AxiomControlPage />} />
      <Route path="/past-events" element={<PastEventsPage />} />
      <Route path="/play" element={<ParticipantEntryPage />} />
      <Route path="/scan/:location" element={<ParticipantEntryPage />} />
      <Route path="/station" element={<AdminPage />} />
      <Route path="/control" element={<SuperAdminPage />} />
      <Route path="/accounts" element={<AccountManagementPage />} />
      <Route path="/round2/control" element={<Round2SuperPage />} />
      <Route path="/round2/station" element={<Round2AdminPage />} />
      <Route path="/round3/play" element={<Round3PuzzleParticipantPage />} />
      <Route path="/round3/control" element={<Round3SuperPage />} />
      <Route path="/round3/station" element={<Round3PuzzleStationPage />} />
      <Route path="/round3/demo" element={<Round3PuzzleDemoPage />} />
      <Route path="/round3/games/*" element={<Navigate to="/round3/play" replace />} />
      <Route path="/results" element={<ResultsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes></Suspense>
  );
}
