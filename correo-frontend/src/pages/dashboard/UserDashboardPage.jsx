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

    // Si se desconecta una cuenta, limpiamos la vista en vivo.
    if (isLiveMode) {
      setLiveEmails([]);
      setEmails([]);
      setIsLiveMode(false);
    }
  };

  // IMPORTANTE:
  // Este botón antes sincronizaba y guardaba correos en la BD.
  // Ahora carga correos EN VIVO desde Microsoft Graph y NO guarda subject/body/sender reales.
  const handleSync = async (accountId) => {
    setLoadingEmails(true);
    setSelectedCategory('todos');

     try {
    const PER_ACCOUNT_LIMIT = 1000;
    const activeAccounts = accounts.filter((account) => account.is_active);

    const responses = await Promise.all(
      activeAccounts.map((account) =>
        getLiveEmailsByAccount(account.id, PER_ACCOUNT_LIMIT)
      )
    );

      const allEmails = responses.flat();

      setLiveEmails(allEmails);
      setEmails(allEmails);
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
        const filtered =
          category === 'todos'
            ? liveEmails
            : liveEmails.filter((email) => email.predicted_category === category);

        setEmails(filtered);
        return;
      }

      const data =
        category === 'todos'
          ? await getMyEmails()
          : await getEmailsByCategory(category);
      setEmails(data);
    } finally {
      setLoadingEmails(false);
    }
  };

  const handleViewDetail = async (email) => {
    // Primero abrimos el modal con lo que ya está en la tabla
    // para que la interfaz responda rápido.
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

  const handleEmailUpdated = (updatedEmail) => {
    // Las correcciones solo aplican para correos guardados en BD.
    // En modo en vivo no persistimos el contenido ni las correcciones.
    if (updatedEmail?.is_live) {
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
          Estás viendo correos en vivo desde Microsoft Graph. El asunto y el contenido se muestran temporalmente y no se guardan en la base de datos.
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <EmailCategoriesSidebar
          selected={selectedCategory}
          onSelect={handleCategoryFilter}
        />

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
