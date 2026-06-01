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
  getMyEmails,
  getEmailDetail,
  getEmailsByCategory,
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
  const [isLiveMode, setIsLiveMode] = useState(false);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  const [loadingEmails, setLoadingEmails] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('todos');
  const [selectedEmail, setSelectedEmail] = useState(null);

  const loadAccounts = async () => {
    setLoadingAccounts(true);
    try {
      const data = await getMicrosoftAccounts();
      setAccounts(data);
    } finally {
      setLoadingAccounts(false);
    }
  };

  const loadEmails = async () => {
    setLoadingEmails(true);
    try {
      setIsLiveMode(false);
      setLiveEmails([]);
      const data = await getMyEmails();
      setEmails(data);
    } finally {
      setLoadingEmails(false);
    }
  };

  useEffect(() => {
    loadAccounts();
    loadEmails();
  }, []);

  const handleConnect = async () => {
    const data = await getMicrosoftConnectUrl();
    window.location.href = data.authorization_url;
  };

  const handleDisconnect = async (accountId) => {
    await disconnectMicrosoftAccount(accountId);
    await loadAccounts();

    if (isLiveMode) {
      setLiveEmails([]);
      setEmails([]);
      setIsLiveMode(false);
    }
  };

  const applyCategoryFilter = (items, category) => {
    if (category === 'todos') return items;
    return items.filter((email) => email.predicted_category === category);
  };

  const handleSync = async (accountId) => {
    setLoadingEmails(true);
    setSelectedCategory('todos');

    try {
      const data = await getLiveEmailsByAccount(accountId, PER_ACCOUNT_LIMIT);
      setLiveEmails(data);
      setEmails(data);
      setIsLiveMode(true);
    } finally {
      setLoadingEmails(false);
    }
  };

  const handleCategoryFilter = async (category) => {
    setSelectedCategory(category);
    setLoadingEmails(true);

    try {
      if (isLiveMode) {
        setEmails(applyCategoryFilter(liveEmails, category));
        return;
      }

      const data =
        category === 'todos' ? await getMyEmails() : await getEmailsByCategory(category);
      setEmails(data);
    } finally {
      setLoadingEmails(false);
    }
  };

  const handleViewDetail = async (email) => {
    setSelectedEmail(email);

    try {
      if (email.is_live) {
        const detail = await getLiveEmailDetail(
          email.linked_account_id,
          email.graph_message_id
        );

        setSelectedEmail({
          ...email,
          ...detail,
          is_live: true,
        });
        return;
      }

      const detail = await getEmailDetail(email.id);
      setSelectedEmail(detail);
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
      item.linked_account_id === updatedEmail.linked_account_id
    );
  };

  const handleEmailUpdated = (updatedEmail) => {
    if (!updatedEmail) return;

    if (updatedEmail.is_live) {
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

      setSelectedEmail(updatedEmail);
      return;
    }

    setEmails((prev) =>
      prev.map((item) => (item.id === updatedEmail.id ? updatedEmail : item))
    );
    setSelectedEmail(updatedEmail);
  };

  const stats = useMemo(() => {
    return {
      connectedAccounts: accounts.filter((item) => item.is_active).length,
      processedEmails: emails.length,
    };
  }, [accounts, emails]);

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
          label={isLiveMode ? 'Correos en vivo' : 'Correos procesados'}
          value={stats.processedEmails}
          hint={
            isLiveMode
              ? 'Consultados temporalmente desde Microsoft Graph'
              : 'Correos almacenados en tu historial'
          }
        />
      </section>

      <ConnectedAccounts
        accounts={accounts}
        onConnect={handleConnect}
        onSync={handleSync}
        onDisconnect={handleDisconnect}
        loading={loadingAccounts}
      />

      {isLiveMode && (
        <div className="rounded-2xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900">
          Estás viendo correos en vivo desde Microsoft Graph. Si corriges una
          categoría, se guardará solo el asunto y la categoría corregida para
          proteger la privacidad del contenido.
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <EmailCategoriesSidebar selected={selectedCategory} onSelect={handleCategoryFilter} />

        {loadingEmails ? (
          <p className="text-sm text-slate-500">Cargando correos...</p>
        ) : (
          <EmailTable emails={emails} onViewDetail={handleViewDetail} />
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
