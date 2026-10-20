import AsyncStorage from '@react-native-async-storage/async-storage';
import { api, setStaffToken } from '@/lib/api';

// A logged-in staff member (doctor / clinic admin / centre admin / therapist / … / super-admin). Separate from the
// consumer Vault account — this is the management plane. Persisted so the console survives relaunch.
export type Staff = { token: string; name: string; role: string; workspace: 'doctor' | 'centre' | 'platform'; org: string; label: string };
const KEY = 'telomy.staff';

let current: Staff | null = null;
let loaded = false;

async function ensureLoaded() {
  if (loaded) return;
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (raw) { current = JSON.parse(raw); if (current) await setStaffToken(current.token); }
  } catch {}
  loaded = true;
}

export async function getStaff(): Promise<Staff | null> { await ensureLoaded(); return current; }
export function staffSync(): Staff | null { return current; }
export function staffOrg(): string { return current?.org || 'default'; }

/** Log a staff member in against /mgmt/auth/login. Returns an error string, or null on success. */
export async function staffLogin(email: string, password: string): Promise<string | null> {
  try {
    const r = await api<any>('/mgmt/auth/login', { body: { email: email.trim().toLowerCase(), password } });
    if (!r?.token) return 'That did not work.';
    current = { token: r.token, name: r.name, role: r.role, workspace: r.workspace, org: r.org, label: r.label };
    await setStaffToken(current.token);
    await AsyncStorage.setItem(KEY, JSON.stringify(current)).catch(() => {});
    loaded = true;
    return null;
  } catch (e: any) {
    return e?.message || "Couldn't reach the Telomy server.";
  }
}

/** Create the first staff account (bootstrap super-admin / centre-admin) or, if an admin is signed in, add staff. */
export async function staffSignup(body: { org?: string; role: string; name: string; email: string; password: string }): Promise<string | null> {
  try {
    await api('/mgmt/auth/signup', { body: { org: body.org || 'default', ...body, email: body.email.trim().toLowerCase() } });
    return null;
  } catch (e: any) { return e?.message || 'Could not create the account.'; }
}

export async function staffStatus(): Promise<{ has_staff: boolean; roles: Record<string, any> }> {
  try { return await api('/mgmt/auth/status'); } catch { return { has_staff: true, roles: {} }; }
}

export async function staffLogout() {
  try { await api('/mgmt/auth/logout'); } catch {}
  current = null;
  await setStaffToken(null);
  await AsyncStorage.removeItem(KEY).catch(() => {});
}
