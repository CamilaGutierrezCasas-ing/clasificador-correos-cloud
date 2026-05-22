import { Link } from 'react-router-dom';
import Button from '../../components/common/Button';

export default function ForbiddenPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
      <div className="max-w-lg rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-soft">
        <p className="text-sm uppercase tracking-[0.35em] text-slate-400">403</p>
        <h1 className="mt-3 text-3xl font-bold text-slate-950">No tienes permisos para entrar aquí</h1>
        <p className="mt-3 text-sm text-slate-500">Tu rol actual no puede acceder a esta pantalla.</p>
        <div className="mt-6">
          <Link to="/"><Button>Ir al inicio</Button></Link>
        </div>
      </div>
    </div>
  );
}
