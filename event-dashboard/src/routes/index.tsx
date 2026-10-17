import { Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from '../live/LoginPage';
import { ParticipantEntryPage } from '../live/ParticipantEntryPage';
import { AdminPage, SuperAdminPage } from '../live/StaffPagesV2';
import { LandingPage, ResultsPage } from '../live/PublicPages';
import { AccountManagementPage } from '../live/AccountManagementPage';
import { Round2AdminPage, Round2SuperPage } from '../live/Round2Pages';
import { Round3SuperPage } from '../live/Round3Pages';
import { Round3PuzzleParticipantPage, Round3PuzzleStationPage } from '../live/Round3PuzzlePages';

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
      <Route path="/round3/play" element={<Round3PuzzleParticipantPage />} />
      <Route path="/round3/control" element={<Round3SuperPage />} />
      <Route path="/round3/station" element={<Round3PuzzleStationPage />} />
      <Route path="/round3/games/*" element={<Navigate to="/round3/play" replace />} />
      <Route path="/results" element={<ResultsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
