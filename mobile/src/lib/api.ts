import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { AppState } from 'react-native';
import { useCallback, useEffect, useRef, useState } from 'react';

// Candidate servers, in order. EXPO_PUBLIC_API_URL may list several (comma-separated) — put the Mac's Bonjour name
// (e.g. http://Kumars-MacBook-Air.local:8787) first: it resolves on any network, including the phone's hotspot, so a
// changed IP never bricks a Release build. Then the Metro host (dev builds), then localhost (simulator).
function candidates(): string[] {
  const out = (process.env.EXPO_PUBLIC_API_URL ?? '').split(',').map((s) => s.trim()).filter(Boolean);
  const host = Constants.expoConfig?.hostUri?.split(':')[0];
  if (host && host !== 'localhost') out.push(`http://${host}:8787`);
  out.push('http://127.0.0.1:8787');
  return [...new Set(out)];
}
const CANDIDATES = candidates();

/** The server currently in use. A live binding: switches to whichever candidate answers when the current one fails. */
export let API = CANDIDATES[0];

async function fetchWithTimeout(url: string, init: RequestInit, ms: number) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), ms);
  try { return await fetch(url, { ...init, signal: ctl.signal }); } finally { clearTimeout(t); }
}

// ---------------------------------------------------------------- access password (hosted server)
// A hosted Telomy server can be locked with a password; the app asks once, keeps the token, and sends it on every call.
const TOKEN_KEY = 'telomy.accessToken';
let token: string | null = null;
const tokenReady = AsyncStorage.getItem(TOKEN_KEY).then((t) => { token = t; }).catch(() => {});
let locked = false;
const lockListeners = new Set<(l: boolean) => void>();
function setLocked(l: boolean) { if (l !== locked) { locked = l; lockListeners.forEach((f) => f(l)); } }
export function onLockChange(f: (l: boolean) => void) { lockListeners.add(f); f(locked); return () => { lockListeners.delete(f); }; }
/** Exchange the password for a token. Returns an error message, or null on success. */
export async function unlock(password: string): Promise<string | null> {
  try {
    const res = await reach('/auth/password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }) });
    const j = await res.json().catch(() => ({}));
    if (!res.ok) return j?.detail ?? "That password isn't right.";
    token = j.token || null;
    if (token) await AsyncStorage.setItem(TOKEN_KEY, token); else await AsyncStorage.removeItem(TOKEN_KEY);
    setLocked(false);
    return null;
  } catch { return "Couldn't reach the Telomy server."; }
}

/** Multi-user: sign up (first account inherits any existing single-user Vault) and log in. Both store the token. */
export async function signup(email: string, password: string, name: string): Promise<string | null> {
  return _authExchange('/auth/signup', { email, password, name });
}
export async function login(email: string, password: string): Promise<string | null> {
  return _authExchange('/auth/login', { email, password });
}
async function _authExchange(path: string, body: any): Promise<string | null> {
  try {
    const res = await reach(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const j = await res.json().catch(() => ({}));
    if (!res.ok) return j?.detail ?? 'That did not work.';
    token = j.token || null;
    if (token) await AsyncStorage.setItem(TOKEN_KEY, token); else await AsyncStorage.removeItem(TOKEN_KEY);
    setLocked(false);
    return null;
  } catch { return "Couldn't reach the Telomy server."; }
}
export async function logout() {
  try { await reach('/auth/logout', { method: 'POST' }); } catch {}
  token = null;
  await AsyncStorage.removeItem(TOKEN_KEY).catch(() => {});
  setLocked(true);
}
export async function authStatus(): Promise<{ password_required: boolean; accounts_enabled: boolean; accounts_available: boolean }> {
  try { const res = await reach('/auth/status', { method: 'GET' }); return await res.json(); }
  catch { return { password_required: false, accounts_enabled: false, accounts_available: false }; }
}

// ---------------------------------------------------------------- staff session (doctor / centre / super-admin)
// The management plane (/mgmt/*) uses a SEPARATE staff token from the consumer Vault token, so a consumer login can
// never reach management and vice-versa. Set on staff login; sent only on /mgmt requests.
const STAFF_KEY = 'telomy.staffToken';
let staffToken: string | null = null;
const staffReady = AsyncStorage.getItem(STAFF_KEY).then((t) => { staffToken = t; }).catch(() => {});
export async function setStaffToken(t: string | null) {
  staffToken = t;
  try { if (t) await AsyncStorage.setItem(STAFF_KEY, t); else await AsyncStorage.removeItem(STAFF_KEY); } catch {}
}
export function hasStaffToken() { return !!staffToken; }

/** Try the current server, then the others; remember the first that answers. Throws only if none do. */
async function reach(path: string, init: RequestInit, primaryMs = 12000): Promise<Response> {
  await tokenReady; await staffReady;
  const isMgmt = path.startsWith('/mgmt');
  const authTok = isMgmt ? staffToken : token;             // /mgmt uses the staff token; everything else the Vault token
  if (authTok) init = { ...init, headers: { ...(init.headers as any), Authorization: `Bearer ${authTok}` } };
  const order = [API, ...CANDIDATES.filter((c) => c !== API)];
  for (const base of order) {
    try {
      // the primary gets the full budget; fallbacks are probed briefly, but never below a file upload's needs
      const res = await fetchWithTimeout(base + path, init, base === API ? primaryMs : Math.min(primaryMs, 4000));
      if (base !== API) API = base;
      return res;
    } catch {}
  }
  throw new Error('unreachable');
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// ---------------------------------------------------------------- durable outbox
// Device data must never be lost because the Mac/server was unreachable. Uploads marked `queue: true` are written to
// the phone when they can't be delivered and re-sent, in order, when the server answers again or the app returns to
// the foreground. Capped so a long offline stretch can't grow without bound (oldest dropped first).
const OUTBOX = 'telomy.outbox.v1';
const OUTBOX_MAX = 2000;
type Pending = { path: string; method: string; body: any; t: number };
let flushing = false;

async function enqueue(p: Pending) {
  try {
    const q: Pending[] = JSON.parse((await AsyncStorage.getItem(OUTBOX)) ?? '[]');
    q.push(p);
    await AsyncStorage.setItem(OUTBOX, JSON.stringify(q.slice(-OUTBOX_MAX)));
  } catch {}
}

/** Re-send everything queued. Stops at the first network failure; drops items the server rejects as invalid (4xx). */
export async function flushOutbox(): Promise<number> {
  if (flushing) return 0;
  flushing = true;
  let sent = 0;
  try {
    let q: Pending[] = JSON.parse((await AsyncStorage.getItem(OUTBOX)) ?? '[]');
    while (q.length) {
      const p = q[0];
      let res: Response;
      try { res = await reach(p.path, { method: p.method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p.body) }); }
      catch { break; }                                    // still offline — keep the rest for later
      if (!res.ok && (res.status >= 500 || res.status === 401)) { if (res.status === 401) setLocked(true); break; }  // retry later; never drop data on a lock
      q = q.slice(1); sent++;
      await AsyncStorage.setItem(OUTBOX, JSON.stringify(q));
    }
  } catch {} finally { flushing = false; }
  return sent;
}
export async function outboxCount(): Promise<number> {
  try { return (JSON.parse((await AsyncStorage.getItem(OUTBOX)) ?? '[]') as Pending[]).length; } catch { return 0; }
}
AppState.addEventListener('change', (s) => { if (s === 'active') flushOutbox(); });

export async function api<T = any>(path: string, opts: { method?: string; body?: any; form?: FormData; queue?: boolean } = {}): Promise<T> {
  let res: Response;
  const method = opts.method ?? (opts.body || opts.form ? 'POST' : 'GET');
  try {
    res = await reach(path, {
      method,
      headers: opts.form ? undefined : { 'Content-Type': 'application/json' },
      body: opts.form ?? (opts.body ? JSON.stringify(opts.body) : undefined),
    }, opts.form ? 60000 : 12000);                          // file uploads (lab PDFs) need a much longer budget than JSON calls
  } catch {
    if (opts.queue && opts.body && !opts.form) {           // keep it on the phone; it goes up when the server is back
      await enqueue({ path, method, body: opts.body, t: Date.now() });
      return { queued: true } as T;
    }
    throw new ApiError(0, "We couldn't reach the Telomy server. Check your connection; we'll retry when you pull to refresh.");
  }
  if (res.status === 401 && path !== '/auth/password' && !path.startsWith('/mgmt')) setLocked(true);   // locked Vault → unlock screen (a /mgmt 401 is a staff-session issue, handled by the staff flow)
  if (res.ok) flushOutbox();                                // the server is reachable — deliver anything waiting
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
