import { Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from '../live/LoginPage';
import { ParticipantEntryPage } from '../live/ParticipantEntryPage';
import { AdminPage, SuperAdminPage } from '../live/StaffPagesV2';
import { LandingPage, ResultsPage } from '../live/PublicPages';
import { AccountManagementPage } from '../live/AccountManagementPage';
import { Round2AdminPage, Round2SuperPage } from '../live/Round2Pages';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/play" element={<ParticipantEntryPage />} />
      <Route path="/scan/:location" element={<ParticipantEntryPage />} />
      <Route path="/station" element={<AdminPage />} />
      <Route path="/control" element={<SuperAdminPage />} />
      <Route path="/accounts" element={<AccountManagementPage />} />
      <Route path="/round2/control" element={<Round2SuperPage />} />
      <Route path="/round2/station" element={<Round2AdminPage />} />
      <Route path="/results" element={<ResultsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
