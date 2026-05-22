import { useMemo, useState } from 'react';
import Card from '../common/Card';
import EmptyState from '../common/EmptyState';
import Badge from '../common/Badge';
import Button from '../common/Button';

const PAGE_SIZE = 8;

export default function EmailTable({
  emails = [],
  title = 'Correos procesados',
  subtitle = 'Listado de correos clasificados por el sistema.',
  onViewDetail,
}) {
  const [page, setPage] = useState(1);

  const sortedEmails = useMemo(() => {
    return [...emails].sort((a, b) => {
      const dateA = new Date(a.received_at || a.created_at || 0);
      const dateB = new Date(b.received_at || b.created_at || 0);
      return dateB - dateA;
    });
  }, [emails]);

  const totalPages = Math.max(1, Math.ceil(sortedEmails.length / PAGE_SIZE));

  const paginatedEmails = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return sortedEmails.slice(start, start + PAGE_SIZE);
  }, [sortedEmails, page]);

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

  const getBadgeColor = (category) => {
    switch ((category || '').toLowerCase()) {
      case 'spam':
        return 'red';
      case 'urgente':
        return 'amber';
      case 'trabajo':
        return 'blue';
      case 'salud':
        return 'green';
      default:
        return 'default';
    }
  };

  return (
    <Card title={title} subtitle={subtitle}>
      {sortedEmails.length === 0 ? (
        <EmptyState
          title="Aún no hay correos clasificados"
          description="Cuando sincronices correos, aparecerán aquí."
        />
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="pb-3 font-medium">Asunto</th>
                  <th className="pb-3 font-medium">Remitente</th>
                  <th className="pb-3 font-medium">Cuenta</th>
                  <th className="pb-3 font-medium">Fecha</th>
                  <th className="pb-3 font-medium">Categoría</th>
                  <th className="pb-3 font-medium">Acción</th>
                </tr>
              </thead>
              <tbody>
                {paginatedEmails.map((email) => (
                  <tr key={email.id} className="border-b border-slate-100 align-top last:border-b-0">
                    <td className="py-4 pr-4">
                      <p className="font-medium text-slate-900">{email.subject || 'Sin asunto'}</p>
                    </td>
                    <td className="py-4 pr-4 text-slate-600">{email.sender || 'Sin remitente'}</td>
                    <td className="py-4 pr-4 text-slate-600">{email.source_account || 'Sin cuenta'}</td>
                    <td className="py-4 pr-4 text-slate-600">
                      {formatDate(email.received_at || email.created_at)}
                    </td>
                    <td className="py-4 pr-4">
                      <Badge color={getBadgeColor(email.predicted_category)}>
                        {email.predicted_category || 'sin clasificar'}
                      </Badge>
                    </td>
                    
                    <td className="py-4 pr-4">
                      <Button
                        variant="secondary"
                        className="px-3 py-2 text-xs"
                        onClick={() => onViewDetail?.(email)}
                      >
                        Ver detalle
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-5 flex items-center justify-between">
            <p className="text-sm text-slate-500">
              Página {page} de {totalPages}
            </p>

            <div className="flex gap-2">
              <Button
                variant="secondary"
                onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                disabled={page === 1}
              >
                ← Anterior
              </Button>
              <Button
                variant="secondary"
                onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                disabled={page === totalPages}
              >
                Siguiente →
              </Button>
            </div>
          </div>
        </>
      )}
    </Card>
  );
}