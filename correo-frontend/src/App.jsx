import { Navigate, Route, Routes } from 'react-router-dom';

import HomePage from './pages/shared/HomePage';
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import MicrosoftCallbackPage from './pages/shared/MicrosoftCallbackPage';
import ForbiddenPage from './pages/shared/ForbiddenPage';
import NotFoundPage from './pages/shared/NotFoundPage';

import ProtectedRoute from './routes/ProtectedRoute';
import RoleRoute from './routes/RoleRoute';

import UserDashboardPage from './pages/dashboard/UserDashboardPage';
import SecretaryDashboardPage from './pages/dashboard/SecretaryDashboardPage';
import AdminDashboardPage from './pages/dashboard/AdminDashboardPage';

export default function App() {
  return (
    <Routes>
      {/* 🔥 IMPORTANTE: esta ruta NO debe ser protegida */}
      <Route path="/microsoft/callback" element={<MicrosoftCallbackPage />} />

      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/registro" element={<RegisterPage />} />
      <Route path="/403" element={<ForbiddenPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<RoleRoute allowedRoles={['usuario']} />}>
          <Route path="/usuario" element={<UserDashboardPage />} />
        </Route>

        <Route element={<RoleRoute allowedRoles={['secretaria']} />}>
          <Route path="/secretaria" element={<SecretaryDashboardPage />} />
        </Route>

        <Route element={<RoleRoute allowedRoles={['admin']} />}>
          <Route path="/admin" element={<AdminDashboardPage />} />
        </Route>
      </Route>

      <Route path="/dashboard" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}