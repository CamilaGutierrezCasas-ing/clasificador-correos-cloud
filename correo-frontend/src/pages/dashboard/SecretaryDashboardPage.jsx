import { useEffect, useMemo, useState } from 'react';
import DashboardLayout from '../../layouts/DashboardLayout';
import { getMyEmails, updateEmailCategory } from '../../api/emailApi';

const categories = ['urgente', 'trabajo', 'educacion', 'spam', 'salud', 'otros'];

export default function SecretaryDashboardPage() {
  const [emails, setEmails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [selectedCategories, setSelectedCategories] = useState({});
  const [message, setMessage] = useState('');

  const loadEmails = async () => {
    setLoading(true);
    setMessage('');
    try {
      const data = await getMyEmails();
      setEmails(data);
    } catch (error) {
      console.error('Error cargando correos:', error);
      setMessage('No se pudieron cargar los correos.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEmails();
  }, []);

  const sortedEmails = useMemo(() => {
    return [...emails].sort((a, b) => {
      const dateA = new Date(a.received_at || a.received_datetime || a.created_at || 0);
      const dateB = new Date(b.received_at || b.received_datetime || b.created_at || 0);
      return dateB - dateA;
    });
  }, [emails]);

  const handleCategoryChange = (emailId, value) => {
    setSelectedCategories((prev) => ({
      ...prev,
      [emailId]: value,
    }));
  };

  const handleSaveCategory = async (emailId) => {
    const newCategory = selectedCategories[emailId];
    if (!newCategory) return;

    setSavingId(emailId);
    setMessage('');

    try {
      await updateEmailCategory(emailId, newCategory);
      setSelectedCategories((prev) => ({
        ...prev,
        [emailId]: '',
      }));
      setMessage('Categoría actualizada correctamente.');
      await loadEmails();
    } catch (error) {
      console.error('Error actualizando categoría:', error);
      setMessage('No se pudo actualizar la categoría.');
    } finally {
      setSavingId(null);
    }
  };

  const formatDate = (value) => {
    if (!value) return 'Sin fecha';
    return new Date(value).toLocaleString('es-CO', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <DashboardLayout
      title="Dashboard secretaria"
      subtitle="Revisa y corrige la clasificación automática de correos."
    >
      {message && (
        <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
          {message}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Cargando correos...</p>
      ) : sortedEmails.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm text-slate-500">No hay correos disponibles para revisar.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 px-6 py-4">
            <h2 className="text-lg font-semibold text-slate-800">Corrección manual</h2>
            <p className="text-sm text-slate-500">
              Los correos se muestran del más reciente al más antiguo.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-sm text-left">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-6 py-3 font-medium">Asunto</th>
                  <th className="px-6 py-3 font-medium">Fecha</th>
                  <th className="px-6 py-3 font-medium">Categoría actual</th>
                  <th className="px-6 py-3 font-medium">Nueva categoría</th>
                  <th className="px-6 py-3 font-medium">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sortedEmails.map((email) => {
                  const currentCategory =
                    email.final_category ||
                    email.corrected_category ||
                    email.predicted_category ||
                    email.category ||
                    'Sin clasificar';

                  const selectedValue = selectedCategories[email.id] || '';

                  return (
                    <tr key={email.id} className="hover:bg-slate-50">
                      <td className="px-6 py-4 text-slate-800">
                        {email.subject || 'Sin asunto'}
                      </td>

                      <td className="px-6 py-4 text-slate-600">
                        {formatDate(
                          email.received_at ||
                            email.received_datetime ||
                            email.created_at
                        )}
                      </td>

                      <td className="px-6 py-4 text-slate-700">
                        {currentCategory}
                      </td>

                      <td className="px-6 py-4">
                        <select
                          className="rounded-lg border border-slate-300 px-3 py-2"
                          value={selectedValue}
                          onChange={(e) =>
                            handleCategoryChange(email.id, e.target.value)
                          }
                        >
                          <option value="">Selecciona</option>
                          {categories.map((category) => (
                            <option key={category} value={category}>
                              {category}
                            </option>
                          ))}
                        </select>
                      </td>

                      <td className="px-6 py-4">
                        <button
                          onClick={() => handleSaveCategory(email.id)}
                          disabled={!selectedValue || savingId === email.id}
                          className="rounded-lg bg-slate-900 px-4 py-2 text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {savingId === email.id ? 'Guardando...' : 'Guardar'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}