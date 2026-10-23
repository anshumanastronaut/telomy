// Apple Health (read-only): daily steps, activity, vitals, sleep and workouts the iPhone / Watch already record.
// Read on the phone; never written back. Connection state is remembered on the device.
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useCallback, useEffect, useState } from 'react';
import { Platform } from 'react-native';
import { Band, bandAvailable } from './band';
import type { HealthDay } from '../../modules/ky-ecg';

const KEY = 'telomy.health.connected';

// Phone health sync (steps/activity/sleep from the OS) is implemented for Apple Health on iOS only. There is no
// Android (Health Connect / Samsung Health) integration yet, so we gate the UI off this flag rather than show a
// non-functional "Connect Apple Health" card on Android.
export const HEALTH_AVAILABLE = Platform.OS === 'ios';

export async function connectHealth(): Promise<{ ok: boolean; error?: string }> {
  if (!HEALTH_AVAILABLE) return { ok: false, error: 'Phone health sync is available on iPhone only for now.' };
  const r = await Band.healthAuthorize();
  if (r.ok) await AsyncStorage.setItem(KEY, '1');
  return r;
}

export function useHealth(days = 30) {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [data, setData] = useState<HealthDay[]>([]);
  const load = useCallback(async () => {
    if (!bandAvailable) return setConnected(false);
    const c = (await AsyncStorage.getItem(KEY)) === '1';
    setConnected(c);
    if (c) setData(await Band.healthDaily(days));
  }, [days]);
  useEffect(() => { load(); }, [load]);
  const today = data[data.length - 1];
  const week = data.slice(-7);
  const avg = (k: keyof HealthDay) => {
    const v = week.map((d) => d[k]).filter((x): x is number => typeof x === 'number');
    return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
  };
  return { connected, data, today, stepsAvg7: avg('steps'), reload: load,
    connect: async () => { const r = await connectHealth(); await load(); return r; } };
}

/** Whether the person has connected Apple Health on this phone. */
export const healthConnected = async () => (await AsyncStorage.getItem(KEY)) === '1';
