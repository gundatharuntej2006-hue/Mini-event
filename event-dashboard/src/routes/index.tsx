import { Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from '../components/layout/MainLayout';
import { OverviewPage } from '../pages/OverviewPage';
import { TeamsPage } from '../pages/TeamsPage';
import { ParticipantsPage } from '../pages/ParticipantsPage';
import { RoundsPage } from '../pages/RoundsPage';
import { Round1ExpeditionPage } from '../pages/Round1ExpeditionPage';
import { Round2CaboPage } from '../pages/Round2CaboPage';
import { ScoreboardPage } from '../pages/ScoreboardPage';
import { SecretAgentsPage } from '../pages/SecretAgentsPage';
import { CodeFragmentsPage } from '../pages/CodeFragmentsPage';
import { BlackMarketPage } from '../pages/BlackMarketPage';
import { Round4LegalBattlePage } from '../pages/Round4LegalBattlePage';
import { FinalePage } from '../pages/FinalePage';
import { SettingsPage } from '../pages/SettingsPage';
import { PublicRegistrationPage } from '../pages/PublicRegistrationPage';
import { NotFoundPage } from '../pages/NotFoundPage';

export function AppRoutes() {
  return (
    <Routes>
      {/* Standalone Public Registration Page */}
      <Route path="/register" element={<PublicRegistrationPage />} />

      <Route path="/" element={<MainLayout />}>
        <Route index element={<OverviewPage />} />
        <Route path="overview" element={<Navigate to="/" replace />} />
        <Route path="teams" element={<TeamsPage />} />
        <Route path="participants" element={<ParticipantsPage />} />
        <Route path="rounds" element={<RoundsPage />} />
        <Route path="round-1" element={<Round1ExpeditionPage />} />
        <Route path="expedition" element={<Navigate to="/round-1" replace />} />
        <Route path="round-2" element={<Round2CaboPage />} />
        <Route path="cabo" element={<Navigate to="/round-2" replace />} />
        <Route path="round-3" element={<BlackMarketPage />} />
        <Route path="black-market" element={<Navigate to="/round-3" replace />} />
        <Route path="round-4" element={<Round4LegalBattlePage />} />
        <Route path="legal-battle" element={<Navigate to="/round-4" replace />} />
        <Route path="scoreboard" element={<ScoreboardPage />} />
        <Route path="secret-agents" element={<SecretAgentsPage />} />
        <Route path="code-fragments" element={<CodeFragmentsPage />} />
        <Route path="judges" element={<Round4LegalBattlePage />} />
        <Route path="finale" element={<FinalePage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
