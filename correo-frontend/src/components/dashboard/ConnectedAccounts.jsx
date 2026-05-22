import Button from '../common/Button';
import Card from '../common/Card';
import Badge from '../common/Badge';
import EmptyState from '../common/EmptyState';

export default function ConnectedAccounts({
  accounts,
  onConnect,
  onDisconnect,
  onSync,
  loading,
}) {
  return (
    <Card
      title="Cuentas Microsoft conectadas"
      subtitle="Gestiona las cuentas vinculadas con Microsoft Graph."
      actions={<Button onClick={onConnect}>Conectar cuenta</Button>}
    >
      {loading ? (
        <p className="text-sm text-slate-500">Cargando cuentas...</p>
      ) : accounts.length === 0 ? (
        <EmptyState
          title="No hay cuentas conectadas"
          description="Conecta una cuenta Microsoft para sincronizar correos."
        />
      ) : (
        <div className="space-y-4">
          {accounts.map((account) => (
            <div
              key={account.id}
              className="flex flex-col gap-4 rounded-2xl border border-slate-200 p-4 md:flex-row md:items-center md:justify-between"
            >
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-slate-900">{account.display_name}</h3>
                  <Badge color={account.is_active ? 'green' : 'rose'}>
                    {account.is_active ? 'Activa' : 'Inactiva'}
                  </Badge>
                </div>
                <p className="text-sm text-slate-600">{account.account_email}</p>
              </div>

              <div className="flex gap-2">
                <Button onClick={() => onSync(account.id)}>Sincronizar</Button>
                <Button variant="danger" onClick={() => onDisconnect(account.id)}>
                  Desconectar
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}