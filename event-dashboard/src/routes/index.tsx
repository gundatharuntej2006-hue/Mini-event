import { Routes, Route, Navigate } from 'react-router-dom';
import { MainLayout } from '../components/layout/MainLayout';
import { StaffOnlyRoute } from '../components/auth/StaffOnlyRoute';
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
import { ProtocolGatePage } from '../pages/ProtocolGatePage';
import { PrintableQRsPage } from '../pages/PrintableQRsPage';
import { Round1ParticipantScanPage } from '../pages/Round1ParticipantScanPage';
import { NotFoundPage } from '../pages/NotFoundPage';

export function AppRoutes() {
  return (
    <Routes>
      {/* Standalone Public Registration & Protocol Checkpoint Pages */}
      <Route path="/register" element={<PublicRegistrationPage />} />
      <Route path="/round1/scan" element={<Round1ParticipantScanPage />} />
      <Route path="/protocol/scan" element={<Round1ParticipantScanPage />} />
      <Route path="/protocol/gate/:gateNumber" element={<ProtocolGatePage />} />
      <Route path="/protocol/gate" element={<Navigate to="/protocol/gate/1" replace />} />
      <Route path="/protocol/print-qrs" element={<PrintableQRsPage />} />

      <Route path="/" element={<MainLayout />}>
        {/* Public Scoreboard route - accessible to all */}
        <Route path="scoreboard" element={<ScoreboardPage />} />

        {/* Staff-only operational routes - non-staff redirected to /scoreboard */}
        <Route index element={<StaffOnlyRoute><OverviewPage /></StaffOnlyRoute>} />
        <Route path="overview" element={<Navigate to="/" replace />} />
        <Route path="teams" element={<StaffOnlyRoute><TeamsPage /></StaffOnlyRoute>} />
        <Route path="participants" element={<StaffOnlyRoute><ParticipantsPage /></StaffOnlyRoute>} />
        <Route path="rounds" element={<StaffOnlyRoute><RoundsPage /></StaffOnlyRoute>} />
        <Route path="round-1" element={<StaffOnlyRoute><Round1ExpeditionPage /></StaffOnlyRoute>} />
        <Route path="expedition" element={<Navigate to="/round-1" replace />} />
        <Route path="round-2" element={<StaffOnlyRoute><Round2CaboPage /></StaffOnlyRoute>} />
        <Route path="cabo" element={<Navigate to="/round-2" replace />} />
        <Route path="round-3" element={<StaffOnlyRoute><BlackMarketPage /></StaffOnlyRoute>} />
        <Route path="black-market" element={<Navigate to="/round-3" replace />} />
        <Route path="round-4" element={<StaffOnlyRoute><Round4LegalBattlePage /></StaffOnlyRoute>} />
        <Route path="legal-battle" element={<Navigate to="/round-4" replace />} />
        <Route path="secret-agents" element={<StaffOnlyRoute><SecretAgentsPage /></StaffOnlyRoute>} />
        <Route path="code-fragments" element={<StaffOnlyRoute><CodeFragmentsPage /></StaffOnlyRoute>} />
        <Route path="judges" element={<StaffOnlyRoute><Round4LegalBattlePage /></StaffOnlyRoute>} />
        <Route path="finale" element={<StaffOnlyRoute><FinalePage /></StaffOnlyRoute>} />
        <Route path="settings" element={<StaffOnlyRoute><SettingsPage /></StaffOnlyRoute>} />

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
