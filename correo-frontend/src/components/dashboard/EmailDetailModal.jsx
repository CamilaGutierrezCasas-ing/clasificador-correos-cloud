import { useEffect, useState } from 'react';
import Button from '../common/Button';
import Badge from '../common/Badge';
import { updateEmailCategory, updateLiveEmailCategory } from '../../api/emailApi';

const categories = ['urgente', 'trabajo', 'educacion', 'spam', 'salud', 'otros'];

export default function EmailDetailModal({ email, onClose, onUpdated }) {
  const [category, setCategory] = useState(email?.predicted_category || 'otros');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    setCategory(email?.predicted_category || 'otros');
    setMessage('');
    setError('');
  }, [email]);

  if (!email) return null;

  const handleSave = async () => {
    try {
      setSaving(true);
      setMessage('');
      setError('');

      let updated;

      if (email.is_live) {
        updated = await updateLiveEmailCategory({
          accountId: email.linked_account_id,
          messageId: email.graph_message_id,
          subject: email.subject || 'Sin asunto',
          sender: email.sender || 'desconocido',
          category,
        });

        updated = {
          ...email,
          ...updated,
          id: email.id,
          is_live: true,
          predicted_category: category,
          confidence: 1.0,
        };
      } else {
        updated = await updateEmailCategory(email.id, category);
      }

      onUpdated?.(updated);
      setMessage('Categoría actualizada correctamente.');
    } catch (saveError) {
      console.error('No se pudo actualizar la categoría:', saveError);
      setError(
        saveError?.response?.data?.detail ||
          'No se pudo actualizar la categoría. Intenta nuevamente.'
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4">
      <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl bg-white p-6 shadow-soft">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-brand-blueDark">
              {email.subject || 'Sin asunto'}
            </h2>
            <p className="mt-2 text-base text-slate-500">
              {email.sender || 'Sin remitente'}
            </p>
          </div>
          <Button variant="secondary" onClick={onClose}>
            Cerrar
          </Button>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl bg-brand-cream p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Cuenta de origen
            </p>
            <p className="mt-2 break-words text-sm text-brand-blueDark">
              {email.source_account}
            </p>
          </div>

          <div className="rounded-2xl bg-brand-cream p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Fecha
            </p>
            <p className="mt-2 text-sm text-brand-blueDark">
              {email.received_at
                ? new Date(email.received_at).toLocaleString('es-CO')
                : 'Sin fecha'}
            </p>
          </div>

          <div className="rounded-2xl bg-brand-cream p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Categoría actual
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Badge color="blue">{email.predicted_category}</Badge>
              {email.is_live && (
                <span className="rounded-full bg-blue-100 px-2 py-1 text-xs font-semibold text-blue-700">
                  En vivo
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="mt-6">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Contenido del correo
          </p>
          <div className="min-h-[180px] rounded-2xl border border-slate-200 p-5 text-base leading-7 text-slate-700 whitespace-pre-wrap">
            {email.body || 'Sin contenido'}
          </div>
          {email.is_live && (
            <p className="mt-2 text-xs text-slate-500">
              Si corriges la categoría, el sistema guardará solo el asunto y la
              categoría corregida para privacidad. No se almacena el cuerpo completo.
            </p>
          )}
        </div>

        <div className="mt-6">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Cambiar categoría
          </p>
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <select
              className="rounded-xl border border-slate-200 px-3 py-2"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              {categories.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>

            <Button onClick={handleSave} disabled={saving}>
              {saving ? 'Guardando...' : 'Actualizar categoría'}
            </Button>
          </div>

          {message && (
            <p className="mt-3 rounded-xl bg-green-50 px-3 py-2 text-sm font-medium text-green-700">
              {message}
            </p>
          )}

          {error && (
            <p className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
              {error}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
