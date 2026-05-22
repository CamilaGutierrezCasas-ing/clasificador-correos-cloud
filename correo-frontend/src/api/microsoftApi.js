import api from './client';

export const getMicrosoftConnectUrl = async () => {
  const { data } = await api.get('/microsoft/connect');
  return data;
};

export const getMicrosoftAccounts = async () => {
  const { data } = await api.get('/microsoft/accounts');
  return data;
};

export const disconnectMicrosoftAccount = async (accountId) => {
  const { data } = await api.post(`/microsoft/accounts/${accountId}/disconnect`);
  return data;
};

export const completeMicrosoftCallback = async ({ code, state, error }) => {
  const { data } = await api.get('/microsoft/callback', {
    params: { code, state, error },
  });
  return data;
};
