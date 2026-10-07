import { Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from '../live/LoginPage';
import { ParticipantPage } from '../live/ParticipantPage';
import { AdminPage, SuperAdminPage } from '../live/StaffPages';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/play" element={<ParticipantPage />} />
      <Route path="/scan/:location" element={<ParticipantPage />} />
      <Route path="/station" element={<AdminPage />} />
      <Route path="/control" element={<SuperAdminPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
