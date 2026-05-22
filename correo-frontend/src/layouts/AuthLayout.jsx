import { Link } from 'react-router-dom';

export default function AuthLayout({ title, subtitle, children }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden bg-slate-950 p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.25em] text-slate-300">Proyecto de grado</p>
          <h1 className="mt-4 max-w-xl text-4xl font-bold leading-tight">
            Clasificador de Correos con Microsoft Graph
          </h1>
          <p className="mt-4 max-w-lg text-slate-300">
            Plataforma para autenticar usuarios, vincular cuentas Microsoft, sincronizar correos y apoyar la clasificación automática.
          </p>
        </div>
        <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
          <p className="text-sm text-slate-300">
            Frontend desarrollado con React, Vite, Tailwind, Axios y React Router, con separación clara por roles y consumo de API REST.
          </p>
        </div>
      </div>
      <div className="flex items-center justify-center p-6 md:p-10">
        <div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-soft">
          <div className="mb-8">
            <Link to="/" className="text-sm font-semibold text-slate-500">Clasificador de Correos</Link>
            <h2 className="mt-3 text-3xl font-bold text-slate-950">{title}</h2>
            <p className="mt-2 text-sm text-slate-500">{subtitle}</p>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
