import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { LoginPage } from './pages/LoginPage';
import { ClassSelectPage } from './pages/ClassSelectPage';
import { RosterPage } from './pages/RosterPage';
import { DestinationPage } from './pages/DestinationPage';
import { PassActivePage } from './pages/PassActivePage';
import AdminDashboard from './pages/AdminDashboard';
import { RequireAuth } from './components/RequireAuth';

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route
            path="/classes"
            element={
              <RequireAuth role="TEACHER">
                <ClassSelectPage />
              </RequireAuth>
            }
          />
          <Route
            path="/roster/:sessionId"
            element={
              <RequireAuth role="TEACHER">
                <RosterPage />
              </RequireAuth>
            }
          />
          <Route
            path="/destination/:studentId"
            element={
              <RequireAuth role="TEACHER">
                <DestinationPage />
              </RequireAuth>
            }
          />
          <Route
            path="/pass-active"
            element={
              <RequireAuth role="TEACHER">
                <PassActivePage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin"
            element={
              <RequireAuth role="ADMIN">
                <AdminDashboard />
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppProvider>
    </BrowserRouter>
  );
}
