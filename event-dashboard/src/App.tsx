import { useEffect } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AppRoutes } from './routes';
import { warmBackend } from './live/eventApi';
import { CellCursor } from './components/CellCursor';

export default function App() {
  useEffect(() => {
    void warmBackend();
  }, []);

  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AppRoutes />
      <CellCursor />
    </BrowserRouter>
  );
}
