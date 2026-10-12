import React, { createContext, ReactNode, useCallback, useContext, useEffect, useState } from 'react';
import { api, getRefreshToken, loadTokens, saveTokens, setLogoutHandler } from './api/client';
import { Me } from './api/types';

type AuthState = {
  me: Me | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: Record<string, any>) => Promise<void>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
};

const Ctx = createContext<AuthState>(null as any);

export function useAuth() {
  return useContext(Ctx);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [ready, setReady] = useState(false);

  const refreshMe = useCallback(async () => {
    try {
      setMe(await api<Me>('/auth/me/'));
    } catch {
      setMe(null);
    }
  }, []);

  useEffect(() => {
    setLogoutHandler(() => setMe(null));
    (async () => {
      if (await loadTokens()) await refreshMe();
      setReady(true);
    })();
  }, [refreshMe]);

  const login = async (email: string, password: string) => {
    const data = await api('/auth/login/', { method: 'POST', body: { email: email.trim().toLowerCase(), password } });
    await saveTokens(data.access, data.refresh);
    await refreshMe();
  };

  const register = async (body: Record<string, any>) => {
    const data = await api('/auth/register/', { method: 'POST', body });
    await saveTokens(data.access, data.refresh);
    setMe(data.user);
  };

  const logout = async () => {
    const r = getRefreshToken();
    try {
      if (r) await api('/auth/logout/', { method: 'POST', body: { refresh: r } });
    } catch {
      // ignore: we clear the local session anyway
    }
    await saveTokens(null, null);
    setMe(null);
  };

  return <Ctx.Provider value={{ me, ready, login, register, logout, refreshMe }}>{children}</Ctx.Provider>;
}
