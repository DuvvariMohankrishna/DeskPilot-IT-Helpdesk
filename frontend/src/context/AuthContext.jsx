import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import api, { tokens } from '../api';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);

  const logout = useCallback(() => {
    tokens.clear();
    setUser(null);
  }, []);

  const login = useCallback(async (username, password) => {
    const { data } = await api.post('/auth/login/', { username, password });
    tokens.set(data.access, data.refresh);
    const me = await api.get('/auth/me/');
    setUser(me.data);
  }, []);

  useEffect(() => {
    if (!tokens.access) { setChecking(false); return; }
    api.get('/auth/me/').then((r) => setUser(r.data)).catch(() => tokens.clear()).finally(() => setChecking(false));
  }, []);

  useEffect(() => {
    window.addEventListener('auth:expired', logout);
    return () => window.removeEventListener('auth:expired', logout);
  }, [logout]);

  const value = {
    user, checking, login, logout,
    isAdmin: user?.role === 'ADMIN',
    isAgent: user?.role === 'AGENT',
    isStaff: user?.role === 'ADMIN' || user?.role === 'AGENT',
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
