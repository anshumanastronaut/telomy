import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { createContext, useContext, useEffect, useState } from 'react';

export type Role = 'user' | 'doctor' | 'centre';
type Ctx = { role: Role | null; ready: boolean; setRole: (r: Role | null) => Promise<void> };
const RoleCtx = createContext<Ctx>({ role: null, ready: false, setRole: async () => {} });
const KEY = 'telomy.role';

export function RoleProvider({ children }: { children: React.ReactNode }) {
  const [role, set] = useState<Role | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((v) => set((v as Role) || null))
      .catch(() => {})
      .finally(() => setReady(true));
  }, []);
  const setRole = async (r: Role | null) => {
    set(r);
    try {
      if (r) await AsyncStorage.setItem(KEY, r);
      else await AsyncStorage.removeItem(KEY);
    } catch {}
  };
  return <RoleCtx.Provider value={{ role, ready, setRole }}>{children}</RoleCtx.Provider>;
}

export const useRole = () => useContext(RoleCtx);

export const ROLE_HOME: Record<Role, string> = { user: '/', doctor: '/doctor', centre: '/centre' };
