import { Link } from 'react-router-dom';
import Button from '../../components/common/Button';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
      <div className="max-w-lg rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-soft">
        <p className="text-sm uppercase tracking-[0.35em] text-slate-400">404</p>
        <h1 className="mt-3 text-3xl font-bold text-slate-950">Página no encontrada</h1>
        <p className="mt-3 text-sm text-slate-500">La ruta que intentaste abrir no existe en este frontend.</p>
        <div className="mt-6">
          <Link to="/"><Button>Volver al inicio</Button></Link>
        </div>
      </div>
    </div>
  );
}
