import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { useEffect } from 'react';
import { Platform } from 'react-native';

import { api, onLockChange } from '@/lib/api';
import { useRole } from '@/lib/role';

// Device push registration. Everything here is best-effort: Expo Go, simulators, a missing EAS projectId, denied
// permission or an unreachable server must never surface an error — the app simply runs without pushes.

const SENT_KEY = 'telomy.push.sentToken';
let handlerSet = false;
let inFlight = false;

/** Foreground notifications show a banner (and sit in the list) instead of being swallowed. */
export async function initNotificationHandler() {
  if (handlerSet || Platform.OS === 'web') return;
  try {
    const N = await import('expo-notifications');
    N.setNotificationHandler({
      handleNotification: async () => ({ shouldShowBanner: true, shouldShowList: true, shouldPlaySound: false, shouldSetBadge: false }),
    });
    handlerSet = true;
  } catch {}
}

function projectId(): string | undefined {
  const c: any = Constants;
  return c?.expoConfig?.extra?.eas?.projectId ?? c?.easConfig?.projectId ?? undefined;
}

/** Ask permission, fetch the Expo push token and POST it to the backend (skipped when unchanged since last send). */
export async function registerForPush(): Promise<void> {
  if (inFlight || Platform.OS === 'web') return;
  inFlight = true;
  try {
    const Device = await import('expo-device');
    if (!Device.isDevice) return;                                   // simulators can't receive pushes
    const N = await import('expo-notifications');
    await initNotificationHandler();
    if (Platform.OS === 'android') {
      await N.setNotificationChannelAsync('default', { name: 'Default', importance: N.AndroidImportance.DEFAULT }).catch(() => {});
    }
    let { status } = await N.getPermissionsAsync();
    if (status !== 'granted') status = (await N.requestPermissionsAsync()).status;
    if (status !== 'granted') return;
    const pid = projectId();
    const tok = (await (pid ? N.getExpoPushTokenAsync({ projectId: pid }) : N.getExpoPushTokenAsync())).data;
    if (!tok) return;
    const last = await AsyncStorage.getItem(SENT_KEY).catch(() => null);
    if (last === tok) return;
    await api('/devices/push-token', { method: 'POST', body: { token: tok, platform: Platform.OS === 'ios' ? 'ios' : 'android' } });
    await AsyncStorage.setItem(SENT_KEY, tok).catch(() => {});      // only after the server accepted it
  } catch {
    // push unavailable (Expo Go, no projectId, denied, offline, 401…) — carry on silently
  } finally {
    inFlight = false;
  }
}

/** Mount once inside RoleProvider: registers for push once the member is signed in (Vault unlocked). */
export function usePushRegistration() {
  const { role, ready } = useRole();
  useEffect(() => {
    initNotificationHandler();
  }, []);
  useEffect(() => {
    if (!ready || role !== 'user') return;                          // /devices/push-token uses the member Vault token
    // onLockChange fires immediately with the current state and again after a successful login/unlock.
    return onLockChange((locked) => { if (!locked) registerForPush(); });
  }, [ready, role]);
}
