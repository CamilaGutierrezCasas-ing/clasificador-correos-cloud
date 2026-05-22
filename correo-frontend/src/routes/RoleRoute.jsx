import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function RoleRoute({ allowedRoles = [] }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <p className="p-6 text-sm text-slate-500">Verificando permisos...</p>;
  }

  const roleName = (user?.role?.name || user?.role || '').toLowerCase();

  if (!allowedRoles.includes(roleName)) {
    return <Navigate to="/403" replace />;
  }

  return <Outlet />;
}