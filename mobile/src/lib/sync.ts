// Phone → Telomy server: daily summaries from the user's REAL devices, so every server feature (Vault timeline,
// insights / effect engine, twin, predictions, Sinc) runs on real data instead of the seeded test profile.
// What is sent: per fused night (patch > WHOOP > Watch > ring) sleep hours, deep, REM, sleep score, overnight HRV,
// resting HR; per Apple Health day steps, active energy, exercise, VO2max, weight, breathing, SpO2. Numbers only,
// labelled by source; at most every 30 min; queued while offline (lib/api outbox) so nothing is lost.
import AsyncStorage from '@react-native-async-storage/async-storage';
import type { HealthDay } from '../../modules/ky-ecg';
import { api } from './api';
import { sleepScore, type Night } from './wellness-core';

const KEY = 'telomy.sync.daily.at';
type Item = { day: string; metric: string; value: number; source: string };

const nightSource = (n: Night) => (n.source === 'patch' ? 'Telomy patch' : n.source === 'whoop' ? 'WHOOP' : n.source === 'watch' ? 'Apple Watch'
  : n.source === 'ring' ? 'Telomy ring' : 'Apple Health');

export function dailyItems(nights: Night[], health: HealthDay[], since: string): Item[] {
  const out: Item[] = [];
  const push = (day: string, metric: string, v: number | null | undefined, source: string, dp = 2) => {
    if (v != null && Number.isFinite(v) && day >= since) out.push({ day, metric, value: Math.round(v * 10 ** dp) / 10 ** dp, source });
  };
  for (const n of nights) {
    if (n.tstMin < 120) continue;                      // naps / fragments are not a night
    const src = nightSource(n);
    push(n.date, 'sleep_hours', n.tstMin / 60, src);
    if (n.deepMin != null) push(n.date, 'deep_sleep', n.deepMin / 60, src);
    if (n.remMin != null) push(n.date, 'rem_sleep', n.remMin / 60, src);
    push(n.date, 'sleep_score', sleepScore(n, nights).score, 'Telomy (fused)', 0);
    if (n.sleepRmssd) push(n.date, 'hrv', n.sleepRmssd, n.hrvSrc === 'ring' ? 'Telomy ring' : 'Telomy patch', 1);
    if (n.lowestHr) push(n.date, 'rhr', n.lowestHr, src, 1);
  }
  for (const d of health) {
    push(d.date, 'steps', d.steps, 'Apple Health', 0);
    push(d.date, 'active_kcal', d.activeKcal, 'Apple Health', 0);
    push(d.date, 'exercise_min', d.exerciseMin, 'Apple Health', 0);
    push(d.date, 'vo2max', d.vo2max, 'Apple Health', 1);
    push(d.date, 'weight', d.weightKg, 'Apple Health', 1);
    push(d.date, 'resp_rate', d.respRate, 'Apple Health', 1);
    push(d.date, 'spo2', d.spo2, 'Apple Health', 1);
  }
  return out;
}

/** Send the last 14 days; throttled to every 30 min. Never throws. */
export async function syncDaily(nights: Night[], health: HealthDay[]) {
  try {
    const last = Number((await AsyncStorage.getItem(KEY)) ?? 0);
    if (Date.now() - last < 30 * 60 * 1000) return;
    const since = new Date(Date.now() - 14 * 86400000).toISOString().slice(0, 10);
    const items = dailyItems(nights, health, since);
    if (!items.length) return;
    await api('/signals/daily', { body: { items }, queue: true });
    await AsyncStorage.setItem(KEY, String(Date.now()));
  } catch {}
}
