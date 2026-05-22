import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import Button from '../components/common/Button';

export default function DashboardLayout({ title, subtitle, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const roleName = (user?.role?.name || user?.role || '').toLowerCase();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-brand-cream">
      <header className="border-b border-brand-blueSoft/20 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-5 md:flex-row md:items-center md:justify-between md:px-6">
          <div>
            <Link
              to="/"
              className="text-sm font-semibold uppercase tracking-[0.2em] text-brand-blue"
            >
              Clasificador de Correos
            </Link>
            <h1 className="mt-2 text-2xl font-bold text-brand-blueDark">{title}</h1>
            <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-sm font-semibold text-brand-blueDark">
                {user?.name || 'Usuario'}
              </p>
              <p className="text-xs uppercase tracking-wide text-brand-blue">
                Rol: {roleName || 'Sin rol'}
              </p>
            </div>
            <Button variant="secondary" onClick={handleLogout}>
              Salir
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 md:px-6">{children}</main>
    </div>
  );
}