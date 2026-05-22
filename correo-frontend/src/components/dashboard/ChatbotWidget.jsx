import { useState } from 'react';
import Button from '../common/Button';
import { chatbotQuery } from '../../api/emailApi';

export default function ChatbotWidget() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    try {
      setLoading(true);
      const data = await chatbotQuery(query);
      setResult(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-20 right-6 z-40 rounded-full bg-brand-red px-5 py-4 text-sm font-bold text-white shadow-soft hover:bg-brand-redDark"
      >
        Chatbot
      </button>

      {open && (
        <div className="fixed inset-0 z-50 bg-slate-950/40 p-4">
          <div className="mx-auto flex h-full max-w-5xl items-center justify-center">
            <div className="flex max-h-[90vh] w-full flex-col overflow-hidden rounded-2xl bg-white shadow-soft">
              <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
                <div>
                  <h2 className="text-xl font-bold text-brand-blueDark">Chatbot de correos</h2>
                  <p className="text-sm text-slate-500">
                    Consulta tus correos por categoría, remitente o texto.
                  </p>
                </div>
                <Button variant="secondary" onClick={() => setOpen(false)}>
                  Cerrar
                </Button>
              </div>

              <div className="overflow-y-auto px-6 py-5">
                <form onSubmit={handleSubmit} className="flex flex-col gap-3 md:flex-row">
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="flex-1 rounded-xl border border-slate-300 px-4 py-3"
                    placeholder="Ejemplo: muéstrame mis correos spam"
                  />
                  <Button type="submit">{loading ? 'Consultando...' : 'Consultar'}</Button>
                </form>

                {result && (
                  <div className="mt-6 space-y-4">
                    <div className="rounded-2xl bg-brand-cream p-4">
                      <p className="text-sm font-semibold text-brand-blueDark">Resumen</p>
                      <p className="mt-2 text-sm text-slate-700">{result.summary}</p>
                    </div>

                    <div className="rounded-2xl border border-slate-200 p-4">
                      <p className="mb-3 text-sm font-semibold text-brand-blueDark">
                        Resultados encontrados: {result.total_results}
                      </p>

                      <div className="space-y-3">
                        {(result.emails || []).map((email) => (
                          <div key={email.id} className="rounded-xl bg-slate-50 p-3">
                            <p className="font-semibold text-slate-900">{email.subject || 'Sin asunto'}</p>
                            <p className="text-sm text-slate-600">{email.sender || 'Sin remitente'}</p>
                            <p className="mt-1 text-xs text-slate-500">
                              {email.predicted_category} · {email.source_account}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}