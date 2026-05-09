import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { LoginPage } from './pages/LoginPage';
import { ClassSelectPage } from './pages/ClassSelectPage';
import { RosterPage } from './pages/RosterPage';
import { DestinationPage } from './pages/DestinationPage';
import { PassActivePage } from './pages/PassActivePage';

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/classes" element={<ClassSelectPage />} />
          <Route path="/roster/:sessionId" element={<RosterPage />} />
          <Route path="/destination/:studentId" element={<DestinationPage />} />
          <Route path="/pass-active" element={<PassActivePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppProvider>
    </BrowserRouter>
  );
}
