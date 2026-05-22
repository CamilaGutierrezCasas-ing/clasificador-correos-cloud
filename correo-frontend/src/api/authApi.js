import api from './client';

export const loginRequest = async ({ email, password }) => {
  const form = new URLSearchParams();
  form.append('username', email);
  form.append('password', password);

  const { data } = await api.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  return data;
};

export const registerRequest = async (payload) => {
  const { data } = await api.post('/auth/register', payload);
  return data;
};

export const meRequest = async () => {
  const { data } = await api.get('/auth/me');
  return data;
};
