import { createContext, useEffect, useMemo, useState } from 'react';
import { loginRequest, meRequest, registerRequest } from '../api/authApi';
import { storage } from '../utils/storage';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(storage.getUser());
  const [token, setToken] = useState(storage.getToken());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const boot = async () => {
      if (!storage.getToken()) {
        setLoading(false);
        return;
      }

      try {
        const profile = await meRequest();
        setUser(profile);
        storage.setUser(profile);
      } catch {
        storage.clearSession();
        setUser(null);
        setToken(null);
      } finally {
        setLoading(false);
      }
    };

    boot();
  }, []);

  const persistSession = (authData) => {
  storage.setToken(authData.access_token);
  setToken(authData.access_token);
};

const login = async (credentials) => {
  const data = await loginRequest(credentials);
  persistSession(data);

  const profile = await meRequest();
  setUser(profile);
  storage.setUser(profile);

  return profile;
};

  const register = async (payload) => {
    const data = await registerRequest(payload);
    persistSession(data);
    return data.user;
  };

  const logout = () => {
    storage.clearSession();
    setUser(null);
    setToken(null);
  };

  const refreshUser = async () => {
    const profile = await meRequest();
    setUser(profile);
    storage.setUser(profile);
    return profile;
  };

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      isAuthenticated: Boolean(token),
      login,
      register,
      logout,
      refreshUser,
    }),
    [user, token, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
