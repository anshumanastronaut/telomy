import Constants from 'expo-constants';
import { useCallback, useEffect, useRef, useState } from 'react';

// Simulator: localhost. Physical device on the same Wi-Fi: the Metro host's LAN IP.
function baseUrl() {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL;
  if (fromEnv) return fromEnv;
  const host = Constants.expoConfig?.hostUri?.split(':')[0];
  return `http://${host && host !== 'localhost' ? host : '127.0.0.1'}:8787`;
}

export const API = baseUrl();

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: any; form?: FormData } = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(API + path, {
      method: opts.method ?? (opts.body || opts.form ? 'POST' : 'GET'),
      headers: opts.form ? undefined : { 'Content-Type': 'application/json' },
      body: opts.form ?? (opts.body ? JSON.stringify(opts.body) : undefined),
    });
  } catch {
    throw new ApiError(0, "We couldn't reach the Telomy server. Check your connection; we'll retry when you pull to refresh.");
  }
  if (!res.ok) {
    let msg = `Something on our side failed (${res.status}). Try again in a moment.`;
    try {
      const j = await res.json();
      if (j?.detail) msg = typeof j.detail === 'string' ? j.detail : msg;
    } catch {}
    throw new ApiError(res.status, msg);
  }
  return res.json();
}

export function useApi<T = any>(path: string | null, deps: any[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const alive = useRef(true);
  const load = useCallback(async () => {
    if (!path) return;
    setLoading(true);
    setError(null);
    try {
      const d = await api<T>(path);
      if (alive.current) setData(d);
    } catch (e: any) {
      if (alive.current) setError(e.message);
    } finally {
      if (alive.current) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps]);
  useEffect(() => {
    alive.current = true;
    load();
    return () => {
      alive.current = false;
    };
  }, [load]);
  return { data, error, loading, reload: load, setData };
}

export function fmtDate(d?: string | null, withYear = false) {
  if (!d) return '—';
  const dt = new Date(d.length === 10 ? d + 'T00:00:00' : d);
  return dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', ...(withYear ? { year: 'numeric' } : {}) });
}

export function fmtTime(d: string) {
  return new Date(d).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

export function ago(d?: string | null, ref?: string) {
  if (!d) return '';
  const base = ref ? new Date(ref + 'T12:00:00') : new Date();
  const days = Math.round((base.getTime() - new Date(d.length === 10 ? d + 'T12:00:00' : d).getTime()) / 86400000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days} d ago`;
  if (days < 365) return `${Math.round(days / 30)} mo ago`;
  return `${(days / 365).toFixed(1)} y ago`;
}
