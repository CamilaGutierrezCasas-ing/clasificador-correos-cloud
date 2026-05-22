import { Link } from 'react-router-dom';
import Button from '../../components/common/Button';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-slate-950 px-6 py-12 text-white">
      <div className="mx-auto max-w-6xl">
        <div className="flex justify-end gap-3">
          <Link to="/login"><Button variant="secondary">Iniciar sesión</Button></Link>
          <Link to="/registro"><Button>Registrarse</Button></Link>
        </div>
        <div className="mt-20 grid gap-10 lg:grid-cols-[1.4fr_1fr] lg:items-center">
          <div>
            <p className="text-sm uppercase tracking-[0.35em] text-slate-400">Proyecto de grado</p>
            <h1 className="mt-4 text-5xl font-bold leading-tight">Clasificador de Correos con Microsoft Graph</h1>
            <p className="mt-6 max-w-2xl text-lg text-slate-300">
              Frontend modular para autenticar usuarios, conectar cuentas Microsoft, visualizar correos clasificados y administrar el sistema por roles.
            </p>
          </div>
          <div className="rounded-3xl border border-slate-800 bg-slate-900 p-8">
            <ul className="space-y-4 text-sm text-slate-300">
              <li>Autenticación JWT</li>
              <li>Panel por roles: usuario, secretaria y administrador</li>
              <li>Consumo de API FastAPI con Axios</li>
              <li>UI limpia con Tailwind</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
