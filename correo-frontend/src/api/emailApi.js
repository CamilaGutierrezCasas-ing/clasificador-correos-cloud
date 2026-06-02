import api from './client';

export const getMyEmails = async () => {
  const { data } = await api.get('/emails/mine');
  return data;
};

export const getEmailDetail = async (emailId) => {
  const { data } = await api.get(`/emails/${emailId}`);
  return data;
};

export const getEmailsByAccount = async (accountId) => {
  const { data } = await api.get(`/emails/mine/account/${accountId}`);
  return data;
};

export const getEmailsByCategory = async (category) => {
  const { data } = await api.get(`/emails/mine/category/${category}`);
  return data;
};

export const syncEmails = async (accountId) => {
  const { data } = await api.post(`/emails/sync/${accountId}`);
  return data;
};

export const updateEmailCategory = async (emailId, category) => {
  const { data } = await api.put(`/emails/${emailId}/category`, { category });
  return data;
};

export const updateLiveEmailCategory = async ({
  accountId,
  messageId,
  category,
}) => {
  const { data } = await api.put('/emails/live/category', {
    account_id: accountId,
    message_id: messageId,
    category,
  });

  return data;
};

export const getAdvancedStats = async () => {
  const { data } = await api.get('/emails/stats/advanced');
  return data;
};

export const chatbotQuery = async (query) => {
  const { data } = await api.post('/emails/chatbot/query', { query });
  return data;
};

export const classifyEmail = async (payload) => {
  const { data } = await api.post('/emails/classify', payload);
  return data;
};

export const retrainModel = async () => {
  const { data } = await api.post('/admin/retrain-model');
  return data;
};

export const reclassifyAllEmails = async () => {
  const { data } = await api.post('/emails/reclassify-all');
  return data;
};

export async function getLiveEmailsByAccount(accountId, top = 1000) {
  const { data } = await api.get(`/emails/live/account/${accountId}`, {
    params: { top },
  });

  return data;
}

export async function getLiveEmailDetail(accountId, messageId) {
  const { data } = await api.get('/emails/live/detail', {
    params: {
      account_id: accountId,
      message_id: messageId,
    },
  });

  return data;
}
