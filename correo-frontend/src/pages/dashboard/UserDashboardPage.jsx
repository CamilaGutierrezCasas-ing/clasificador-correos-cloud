import { useEffect, useMemo, useState } from 'react';
import {
  getMicrosoftAccounts,
  getMicrosoftConnectUrl,
  disconnectMicrosoftAccount,
} from '../../api/microsoftApi';
import DashboardLayout from '../../layouts/DashboardLayout';
import ConnectedAccounts from '../../components/dashboard/ConnectedAccounts';
import EmailTable from '../../components/dashboard/EmailTable';
import StatCard from '../../components/common/StatCard';
import {
  getLiveEmailsByAccount,
  getLiveEmailDetail,
} from '../../api/emailApi';
import EmailCategoriesSidebar from '../../components/dashboard/EmailCategoriesSidebar';
import EmailDetailModal from '../../components/dashboard/EmailDetailModal';
import ChatbotWidget from '../../components/dashboard/ChatbotWidget';
import { useAuth } from '../../hooks/useAuth';

const PER_ACCOUNT_LIMIT = 1000;

export default function UserDashboardPage() {
  const { user } = useAuth();
  const [accounts, setAccounts] = useState([]);
  const [emails, setEmails] = useState([]);
  const [liveEmails, setLiveEmails] = useState([]);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [loadingEmails, setLoadingEmails] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('todos');
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [syncMessage, setSyncMessage] = useState('');
  const [syncError, setSyncError] = useState('');

  const applyCategoryFilter = (items, category) => {
    if (category === 'todos') return items;
    return items.filter((email) => email.predicted_category === category);
  };

  const getEmailKey = (email) => {
    if (email?.linked_account_id && email?.graph_message_id) {
      return `${email.linked_account_id}-${email.graph_message_id}`;
    }

    return String(email?.id || '');
  };

  const mergeAccountLiveEmails = (currentItems, accountId, newItems) => {
    const withoutCurrentAccount = currentItems.filter(
      (email) => Number(email.linked_account_id) !== Number(accountId)
    );

    const merged = new Map();

    [...withoutCurrentAccount, ...newItems].forEach((email) => {
      merged.set(getEmailKey(email), { ...email, is_live: true });
    });

    return Array.from(merged.values());
  };

  const loadAccounts = async () => {
    setLoadingAccounts(true);
    try {
      const data = await getMicrosoftAccounts();
      setAccounts(data);
    } finally {
      setLoadingAccounts(false);
    }
  };

  useEffect(() => {
    loadAccounts();
  }, []);

  const handleConnect = async () => {
    const data = await getMicrosoftConnectUrl();
    window.location.href = data.authorization_url;
  };

  const handleDisconnect = async (accountId) => {
    await disconnectMicrosoftAccount(accountId);
    await loadAccounts();

    setLiveEmails((prev) => {
      const remaining = prev.filter(
        (email) => Number(email.linked_account_id) !== Number(accountId)
      );
      setEmails(applyCategoryFilter(remaining, selectedCategory));
      return remaining;
    });
  };

  const handleSync = async (accountId) => {
    setLoadingEmails(true);
    setSyncMessage('');
    setSyncError('');

    try {
      const data = await getLiveEmailsByAccount(accountId, PER_ACCOUNT_LIMIT);

      setLiveEmails((prev) => {
        const merged = mergeAccountLiveEmails(prev, accountId, data);
        setEmails(applyCategoryFilter(merged, selectedCategory));
        return merged;
      });

      setSyncMessage(
        `Cuenta sincronizada en vivo. Se consultaron ${data.length} correos temporalmente desde Microsoft Graph.`
      );
    } catch (error) {
      console.error('No se pudo sincronizar la cuenta:', error);
      setSyncError(
        error?.response?.data?.detail ||
          'No se pudo sincronizar la cuenta. Revisa la conexión con Microsoft Graph.'
      );
    } finally {
      setLoadingEmails(false);
    }
  };

  const handleSyncAll = async () => {
    const activeAccounts = accounts.filter((account) => account.is_active);

    if (activeAccounts.length === 0) {
      setSyncError('No hay cuentas Microsoft activas para sincronizar.');
      return;
    }

    setLoadingEmails(true);
    setSyncMessage('');
    setSyncError('');

    try {
      let merged = liveEmails;
      let totalLoaded = 0;

      for (const account of activeAccounts) {
        const data = await getLiveEmailsByAccount(account.id, PER_ACCOUNT_LIMIT);
        totalLoaded += data.length;
        merged = mergeAccountLiveEmails(merged, account.id, data);
      }

      setLiveEmails(merged);
      setEmails(applyCategoryFilter(merged, selectedCategory));
      setSyncMessage(
        `Sincronización en vivo completada. Se consultaron ${totalLoaded} correos de ${activeAccounts.length} cuenta(s).`
      );
    } catch (error) {
      console.error('No se pudieron sincronizar todas las cuentas:', error);
      setSyncError(
        error?.response?.data?.detail ||
          'No se pudieron sincronizar todas las cuentas. Intenta cuenta por cuenta.'
      );
    } finally {
      setLoadingEmails(false);
    }
  };

  const handleCategoryFilter = (category) => {
    setSelectedCategory(category);
    setEmails(applyCategoryFilter(liveEmails, category));
  };

  const handleViewDetail = async (email) => {
    setSelectedEmail(email);

    try {
      const detail = await getLiveEmailDetail(
        email.linked_account_id,
        email.graph_message_id
      );

      setSelectedEmail({
        ...email,
        ...detail,
        id: email.id,
        is_live: true,
      });
    } catch (error) {
      console.error('No se pudo cargar el detalle del correo:', error);
    }
  };

  const sameEmail = (item, updatedEmail) => {
    if (item.id === updatedEmail.id) return true;

    return (
      item.graph_message_id &&
      updatedEmail.graph_message_id &&
      item.graph_message_id === updatedEmail.graph_message_id &&
      Number(item.linked_account_id) === Number(updatedEmail.linked_account_id)
    );
  };

  const handleEmailUpdated = (updatedEmail) => {
    if (!updatedEmail) return;

    setLiveEmails((prev) => {
      const updatedLiveEmails = prev.map((item) =>
        sameEmail(item, updatedEmail)
          ? {
              ...item,
              ...updatedEmail,
              id: item.id,
              is_live: true,
            }
          : item
      );

      setEmails(applyCategoryFilter(updatedLiveEmails, selectedCategory));
      return updatedLiveEmails;
    });

    setSelectedEmail((prev) =>
      prev
        ? {
            ...prev,
            ...updatedEmail,
            id: prev.id,
            is_live: true,
          }
        : updatedEmail
    );
  };

  const stats = useMemo(() => {
    return {
      connectedAccounts: accounts.filter((item) => item.is_active).length,
      liveCount: liveEmails.length,
      visibleCount: emails.length,
    };
  }, [accounts, emails, liveEmails]);

  return (
    <DashboardLayout
      title={`Bienvenida, ${user?.name || 'usuario'}`}
      subtitle="Gestiona tus cuentas, revisa tus correos y organiza tu bandeja inteligente."
    >
      <section className="grid gap-4 md:grid-cols-2">
        <StatCard
          label="Cuentas activas"
          value={stats.connectedAccounts}
          hint="Cuentas Microsoft vinculadas"
        />
        <StatCard
          label="Correos en vivo"
          value={stats.visibleCount}
          hint={
            selectedCategory === 'todos'
              ? 'Consultados temporalmente desde Microsoft Graph'
              : `Filtrados por categoría. Total en vivo: ${stats.liveCount}`
          }
        />
      </section>

      <ConnectedAccounts
        accounts={accounts}
        onConnect={handleConnect}
        onSync={handleSync}
        onSyncAll={handleSyncAll}
        onDisconnect={handleDisconnect}
        loading={loadingAccounts}
        syncing={loadingEmails}
      />

      <div className="rounded-2xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900">
        Vista en vivo desde Microsoft Graph: el asunto, remitente y contenido se muestran temporalmente en pantalla, pero no se guardan en la base de datos. Al recargar, vuelve a sincronizar para consultarlos otra vez.
      </div>

      {syncMessage && (
        <div className="rounded-2xl border border-green-100 bg-green-50 px-4 py-3 text-sm font-medium text-green-800">
          {syncMessage}
        </div>
      )}

      {syncError && (
        <div className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
          {syncError}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <EmailCategoriesSidebar selected={selectedCategory} onSelect={handleCategoryFilter} />

        {loadingEmails ? (
          <p className="text-sm text-slate-500">Consultando correos en vivo...</p>
        ) : (
          <EmailTable
            emails={emails}
            title="Correos en vivo"
            subtitle="Listado temporal consultado desde Microsoft Graph. No se almacena asunto, remitente ni contenido."
            onViewDetail={handleViewDetail}
          />
        )}
      </div>

      <ChatbotWidget />

      {selectedEmail && (
        <EmailDetailModal
          email={selectedEmail}
          onClose={() => setSelectedEmail(null)}
          onUpdated={handleEmailUpdated}
        />
      )}
    </DashboardLayout>
  );
}
