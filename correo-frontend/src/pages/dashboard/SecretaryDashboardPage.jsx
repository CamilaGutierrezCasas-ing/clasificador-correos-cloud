import { useEffect, useMemo, useState } from 'react';

import DashboardLayout from '../../layouts/DashboardLayout';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import Button from '../../components/common/Button';
import { getAdvancedStats } from '../../api/emailApi';

function StatItem({ label, value, color = 'default' }) {
  return (
    <div className="rounded-2xl border border-brand-blueSoft/15 bg-white p-4 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <Badge color={color}>{label}</Badge>
      </div>
      <p className="mt-4 text-3xl font-bold text-brand-blueDark">{value}</p>
    </div>
  );
}

const CATEGORY_LABELS = {
  trabajo: 'Trabajo',
  salud: 'Salud',
  otros: 'Otros',
  spam: 'Spam',
  urgente: 'Urgente',
  educacion: 'Educación',
};

function SimpleBarList({ title, subtitle, data, scale = 'total' }) {
  const entries = Object.entries(data || {}).sort(
    ([, a], [, b]) => Number(b) - Number(a)
  );

  const total = entries.reduce(
    (sum, [, value]) => sum + (Number(value) || 0),
    0
  );

  const maxValue = Math.max(
    ...entries.map(([, value]) => Number(value) || 0),
    1
  );

  return (
    <Card title={title} subtitle={subtitle}>
      {entries.length === 0 ? (
        <p className="text-sm text-slate-500">No hay datos disponibles.</p>
      ) : (
        <div className="space-y-4">
          <div className="rounded-2xl bg-brand-cream px-4 py-3">
            <p className="text-sm font-medium text-slate-500">
              Total analizado
            </p>
            <p className="text-2xl font-bold text-brand-blueDark">
              {total.toLocaleString('es-CO')} muestras
            </p>
          </div>

          {entries.map(([key, value]) => {
            const numericValue = Number(value) || 0;
            const denominator = scale === 'max' ? maxValue : total || 1;
            const percent = (numericValue / denominator) * 100;
            const width = `${Math.min(Math.max(percent, 2), 100)}%`;

            return (
              <div
                key={key}
                className="rounded-2xl border border-brand-blueSoft/10 bg-white p-4 shadow-sm"
              >
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span className="truncate text-sm font-semibold text-brand-blueDark">
                    {CATEGORY_LABELS[key] || key}
                  </span>

                  <span className="text-sm font-bold text-brand-blueDark">
                    {numericValue.toLocaleString('es-CO')}
                    {scale === 'total' && (
                      <span className="ml-2 font-medium text-slate-500">
                        ({percent.toFixed(1)}%)
                      </span>
                    )}
                  </span>
                </div>

                <div className="h-3 overflow-hidden rounded-full bg-brand-cream">
                  <div
                    className="h-full rounded-full bg-brand-blue transition-all duration-500"
                    style={{ width }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

export default function SecretaryDashboardPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadStats = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getAdvancedStats();
      setStats(data);
    } catch (err) {
      console.error(err);
      setError('No se pudieron cargar las métricas de secretaria.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  const lowConfidencePercent = useMemo(() => {
    if (!stats?.total_emails) return 0;
    return ((stats.low_confidence_count / stats.total_emails) * 100).toFixed(1);
  }, [stats]);

  const manualCorrectionPercent = useMemo(() => {
    if (!stats?.total_emails) return 0;
    return ((stats.manual_corrections / stats.total_emails) * 100).toFixed(1);
  }, [stats]);

  return (
    <DashboardLayout
      title="Panel de secretaria"
      subtitle="Consulta operativa de correos analizados, categorías, cuentas y correcciones."
    >
      {loading ? (
        <Card title="Cargando panel">
          <p className="text-sm text-slate-500">
            Estamos consultando las métricas del sistema...
          </p>
        </Card>
      ) : error ? (
        <Card title="Error" className="border-brand-red/20">
          <p className="text-sm text-brand-red">{error}</p>
          <div className="mt-4">
            <Button variant="secondary" onClick={loadStats}>
              Reintentar
            </Button>
          </div>
        </Card>
      ) : (
        <>
          <div className="rounded-3xl border border-brand-blueSoft/20 bg-white p-6 shadow-sm">
            <h2 className="text-2xl font-bold text-brand-blueDark">
              Resumen operativo
            </h2>
            <p className="mt-2 text-sm text-slate-500">
              Este panel permite visualizar estadísticas del sistema sin acceso
              a funciones críticas como el reentrenamiento del modelo.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatItem
              label="Correos analizados"
              value={stats?.total_emails ?? 0}
              color="blue"
            />
            <StatItem
              label="Score promedio"
              value={`${Number(stats?.average_confidence || 0).toFixed(2)}`}
              color="green"
            />
            <StatItem
              label="Revisión sugerida"
              value={stats?.low_confidence_count ?? 0}
              color="amber"
            />
            <StatItem
              label="Correcciones manuales"
              value={stats?.manual_corrections ?? 0}
              color="red"
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <Card title="Indicadores del sistema">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl bg-brand-cream p-4">
                  <p className="text-sm font-medium text-slate-500">
                    Porcentaje para revisión
                  </p>
                  <p className="mt-2 text-2xl font-bold text-brand-blueDark">
                    {lowConfidencePercent}%
                  </p>
                </div>

                <div className="rounded-2xl bg-brand-cream p-4">
                  <p className="text-sm font-medium text-slate-500">
                    Porcentaje de corrección manual
                  </p>
                  <p className="mt-2 text-2xl font-bold text-brand-blueDark">
                    {manualCorrectionPercent}%
                  </p>
                </div>
              </div>
            </Card>

            <SimpleBarList
              title="Correos por categoría"
              subtitle="Distribución de correos clasificados por el sistema."
              data={stats?.by_category || {}}
              scale="total"
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <SimpleBarList
              title="Cuentas Microsoft analizadas"
              subtitle="Cantidad de correos analizados por cada cuenta vinculada."
              data={stats?.by_account || {}}
              scale="total"
            />

            <SimpleBarList
              title="Usuarios con correos analizados"
              subtitle="Cantidad de correos registrados por usuario del sistema."
              data={stats?.by_user || {}}
              scale="total"
            />
          </div>
        </>
      )}
    </DashboardLayout>
  );
}