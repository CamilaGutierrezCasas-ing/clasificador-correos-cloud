import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function ProtectedRoute() {
  const { token, loading } = useAuth();

  if (loading) {
    return <p className="p-6 text-sm text-slate-500">Verificando sesión...</p>;
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}