import { useEffect, useMemo, useState } from 'react';

import DashboardLayout from '../../layouts/DashboardLayout';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import Button from '../../components/common/Button';
import { getAdvancedStats, retrainModel, reclassifyAllEmails } from '../../api/emailApi';


function StatItem({ label, value, color = 'default', badge }) {
  return (
    <div className="rounded-2xl border border-brand-blueSoft/15 bg-white p-4 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <Badge color={color}>{badge || label}</Badge>
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

const formatPercent = (value) => `${Number(value || 0).toFixed(1)}%`;

const formatConfidencePercent = (value) => {
  const numericValue = Number(value || 0);
  return `${(numericValue * 100).toFixed(1)}%`;
};

const formatUserLabel = (key) => {
  const text = String(key || '').trim();
  if (!text) return 'Usuario sin identificar';
  if (/^\d+$/.test(text)) return `Usuario #${text}`;
  return text;
};

const formatAccountLabel = (key) => {
  const text = String(key || '').trim();
  return text || 'Cuenta Microsoft sin identificar';
};


function MetricsExplanation({ result }) {
  if (!result) return null;

  const accuracy = result.accuracy ?? 0;
  const recallMacro = result.recall_macro ?? 0;
  const mcc = result.mcc_multiclass ?? 0;

  const testSamples = result.test_samples ?? 0;
  const correctPredictions = Math.round(accuracy * testSamples);

  const rows = [
    {
      name: 'Accuracy',
      formula: 'Predicciones correctas / Total de muestras de prueba',
      calculation: `${correctPredictions} / ${testSamples}`,
      value: accuracy.toFixed(4),
      interpretation:
        'Mide el porcentaje general de correos clasificados correctamente.',
    },
    {
      name: 'Recall Macro',
      formula: 'Promedio del recall de todas las categorías',
      calculation: 'Recall de cada categoría / número de categorías',
      value: recallMacro.toFixed(4),
      interpretation:
        'Mide qué tan bien el modelo identifica los correos reales de cada categoría, dando el mismo peso a todas.',
    },
    {
      name: 'MCC Multiclase',
      formula: 'Coeficiente de Matthews aplicado a varias categorías',
      calculation: 'Se calcula a partir de la matriz de confusión completa',
      value: mcc.toFixed(4),
      interpretation:
        'Evalúa la calidad global del clasificador. Va de -1 a 1, donde 1 es perfecto, 0 es aleatorio y -1 es incorrecto.',
    },
  ];

  return (
    <section className="rounded-3xl border border-brand-blueSoft/20 bg-white p-6 shadow-sm">
      <div className="mb-5">
        <h2 className="text-2xl font-bold text-brand-blueDark">
          Detalle de métricas de evaluación
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Esta tabla explica cómo se interpreta cada métrica obtenida durante el entrenamiento.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-y-3">
          <thead>
            <tr className="text-left text-sm text-slate-500">
              <th className="px-4 py-2">Métrica</th>
              <th className="px-4 py-2">Fórmula</th>
              <th className="px-4 py-2">Cálculo / origen</th>
              <th className="px-4 py-2">Resultado</th>
              <th className="px-4 py-2">Interpretación</th>
            </tr>
          </thead>

          <tbody>
            {rows.map((row) => (
              <tr
                key={row.name}
                className="rounded-2xl bg-brand-cream text-sm text-brand-blueDark"
              >
                <td className="rounded-l-2xl px-4 py-4 font-bold">
                  {row.name}
                </td>
                <td className="px-4 py-4">
                  {row.formula}
                </td>
                <td className="px-4 py-4">
                  {row.calculation}
                </td>
                <td className="px-4 py-4 text-lg font-bold">
                  {row.value}
                </td>
                <td className="rounded-r-2xl px-4 py-4 text-slate-600">
                  {row.interpretation}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function SimpleBarList({
  title,
  subtitle,
  data,
  scale = 'total',
  itemLabelFormatter = (key) => CATEGORY_LABELS[key] || key,
  totalLabel = 'Total analizado',
  totalSuffix = 'muestras',
}) {
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
              {totalLabel}
            </p>
            <p className="text-2xl font-bold text-brand-blueDark">
              {total.toLocaleString('es-CO')} {totalSuffix}
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
                    {itemLabelFormatter(key)}
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

function ConfusionMatrix({
  matrix,
  title = 'Matriz de confusión',
  subtitle = 'Compara categoría original vs categoría final',
}) {
  const rows = Object.keys(matrix || {});
  const columns = Array.from(
    new Set(rows.flatMap((row) => Object.keys(matrix[row] || {})))
  );

  if (rows.length === 0 || columns.length === 0) {
    return (
      <Card title={title} subtitle={subtitle}>
        <p className="text-sm text-slate-500">No hay datos disponibles.</p>
      </Card>
    );
  }

  const maxValue = Math.max(
    ...rows.flatMap((row) => columns.map((col) => Number(matrix[row]?.[col]) || 0)),
    1
  );

  const getOpacity = (value) => {
    const normalized = (Number(value) || 0) / maxValue;
    return Math.max(0.08, normalized);
  };

  return (
    <Card title={title} subtitle={subtitle}>
      <div className="overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-2">
          <thead>
            <tr>
              <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                Original \ Final
              </th>

              {columns.map((col) => (
                <th
                  key={col}
                  className="px-3 py-2 text-center text-xs font-semibold uppercase tracking-wide text-slate-500"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.map((row) => (
              <tr key={row}>
                <td className="rounded-xl bg-brand-cream px-3 py-2 text-sm font-semibold text-brand-blueDark">
                  {row}
                </td>

                {columns.map((col) => {
                  const value = Number(matrix[row]?.[col]) || 0;

                  return (
                    <td
                      key={`${row}-${col}`}
                      className="rounded-xl px-3 py-4 text-center text-sm font-bold text-brand-blueDark"
                      style={{
                        backgroundColor: `rgba(53, 93, 110, ${getOpacity(value)})`,
                      }}
                    >
                      {value}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function TrainingResultPanel({ result }) {
  if (!result) {
    return (
      <p className="text-sm text-slate-500">
        Aún no se ha ejecutado un reentrenamiento desde este panel.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <div className="rounded-2xl bg-brand-cream p-4">
          <p className="text-sm font-medium text-slate-500">Accuracy</p>
          <p className="mt-2 text-3xl font-bold text-brand-blueDark">
            {Number(result.accuracy || 0).toFixed(4)}
          </p>
        </div>

        <div className="rounded-2xl bg-brand-cream p-4">
          <p className="text-sm font-medium text-slate-500">Recall Macro</p>
          <p className="mt-2 text-3xl font-bold text-brand-blueDark">
            {Number(result.recall_macro || 0).toFixed(4)}
          </p>
        </div>

        <div className="rounded-2xl bg-brand-cream p-4">
          <p className="text-sm font-medium text-slate-500">MCC Multiclase</p>
          <p className="mt-2 text-3xl font-bold text-brand-blueDark">
            {Number(result.mcc_multiclass || 0).toFixed(4)}
          </p>
        </div>

        <div className="rounded-2xl bg-brand-cream p-4">
          <p className="text-sm font-medium text-slate-500">Total muestras</p>
          <p className="mt-2 text-3xl font-bold text-brand-blueDark">
            {result.total_samples}
          </p>
        </div>

        <div className="rounded-2xl bg-brand-cream p-4">
          <p className="text-sm font-medium text-slate-500">Entrenamiento</p>
          <p className="mt-2 text-3xl font-bold text-brand-blueDark">
            {result.train_samples}
          </p>
        </div>

        <div className="rounded-2xl bg-brand-cream p-4">
          <p className="text-sm font-medium text-slate-500">Prueba</p>
          <p className="mt-2 text-3xl font-bold text-brand-blueDark">
            {result.test_samples}
          </p>
        </div>
      </div>

      <SimpleBarList
        title="Muestras usadas por categoría"
        subtitle="Distribución del dataset usado para entrenar. La barra representa el porcentaje frente al total de muestras."
        data={result.categories || {}}
        scale="total"
      />
      
      <MetricsExplanation result={result} />

      <ConfusionMatrix
        title="Matriz de confusión del entrenamiento"
        subtitle="Compara categoría real del conjunto de prueba vs categoría predicha por el modelo"
        matrix={result.confusion_matrix || {}}
      />
    </div>
  );
}

export default function AdminDashboardPage() {
  const [stats, setStats] = useState(null);
  const [trainingResult, setTrainingResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [trainingLoading, setTrainingLoading] = useState(false);
  const [error, setError] = useState('');

  const loadStats = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await getAdvancedStats();
      setStats(data);
    } catch (err) {
      console.error(err);
      setError('No se pudieron cargar las métricas administrativas.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  const handleRetrainModel = async () => {
  try {
    setTrainingLoading(true);
    setError('');

    const result = await retrainModel();
    setTrainingResult(result);

    await reclassifyAllEmails();

    const freshStats = await getAdvancedStats();
    setStats(freshStats);
  } catch (err) {
    console.error(err);
    setError(
      err?.response?.data?.detail ||
        'No se pudo reentrenar y actualizar los correos.'
    );
  } finally {
    setTrainingLoading(false);
  }
};

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
      title="Panel administrativo"
      subtitle="Métricas globales, seguimiento del modelo y reentrenamiento del sistema"
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
          <Card
            title="Entrenamiento del modelo"
            subtitle="Ejecuta el reentrenamiento usando el dataset base y los correos corregidos."
            actions={
              <Button onClick={handleRetrainModel} disabled={trainingLoading}>
                {trainingLoading ? 'Reentrenando...' : 'Reentrenar modelo'}
              </Button>
            }
          >
            <TrainingResultPanel result={trainingResult} />
          </Card>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatItem
              label="Correos analizados"
              value={(stats?.total_emails ?? 0).toLocaleString('es-CO')}
              color="blue"
              badge="Metadatos"
            />
            <StatItem
              label="Score promedio del modelo"
              value={formatConfidencePercent(stats?.average_confidence)}
              color="green"
              badge="Confianza"
            />
            <StatItem
              label="Revisión sugerida"
              value={(stats?.low_confidence_count ?? 0).toLocaleString('es-CO')}
              color="amber"
              badge="Baja confianza"
            />
            <StatItem
              label="Correcciones manuales"
              value={(stats?.manual_corrections ?? 0).toLocaleString('es-CO')}
              color="red"
              badge="Correcciones"
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <Card title="Resumen del sistema">
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
                    Porcentaje corregido manualmente
                  </p>
                  <p className="mt-2 text-2xl font-bold text-brand-blueDark">
                    {manualCorrectionPercent}%
                  </p>
                </div>
              </div>
            </Card>

            <SimpleBarList
              title="Correos por categoría"
              subtitle="Distribución general según la categoría final asignada por el sistema o por corrección manual."
              data={stats?.by_category || {}}
              scale="total"
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <SimpleBarList
              title="Cuentas Microsoft analizadas"
              subtitle="Cantidad de correos analizados por cada cuenta vinculada. Solo se guardan metadatos técnicos, no el contenido del correo."
              data={stats?.by_account || {}}
              scale="total"
              itemLabelFormatter={formatAccountLabel}
              totalLabel="Correos analizados entre cuentas"
              totalSuffix="correos"
            />
            <SimpleBarList
              title="Usuarios con correos analizados"
              subtitle="Distribución de correos procesados por cada usuario registrado en el sistema."
              data={stats?.by_user || {}}
              scale="total"
              itemLabelFormatter={formatUserLabel}
              totalLabel="Correos analizados entre usuarios"
              totalSuffix="correos"
            />
          </div>

          <ConfusionMatrix
            title="Matriz de confusión del sistema"
            subtitle="Compara categoría original guardada vs categoría final después de correcciones"
            matrix={stats?.confusion_matrix || {}}
          />
        </>
      )}
    </DashboardLayout>
  );
}
