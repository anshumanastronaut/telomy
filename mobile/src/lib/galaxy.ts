// Galaxy Watch / Samsung Health reader (Android only) via Health Connect.
//
// Phase 1 channel: Samsung Health syncs a SUBSET of the watch's computed data into Android Health Connect (HR, SpO2,
// sleep + stages, steps, VO2max, body fat %, BMR, weight/lean mass). We read only records whose data origin is Samsung
// Health, and POST them to /vitals/ingest with source 'galaxy'. NOT available this way: skeletal muscle, body water,
// HRV, Energy Score, skin temp, AFib/apnea flags — those need the Samsung Health Data SDK (see research/intel/GALAXY_WATCH8.md).
// Health Connect has a ~30-60 min lag and no backfill beyond 30 days before first grant.
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

import { api } from '@/lib/api';

export const GALAXY_AVAILABLE = Platform.OS === 'android';
const SHEALTH = 'com.sec.android.app.shealth';
const CURSOR = 'telomy.galaxy.cursor.v1';
const LAST = 'telomy.galaxy.last.v1';
const MIN_INTERVAL_MS = 5 * 60 * 1000;
const BACKFILL_DAYS = 3;

const RECORDS = ['HeartRate', 'RestingHeartRate', 'OxygenSaturation', 'SleepSession', 'Steps', 'Vo2Max', 'BodyFat', 'BasalMetabolicRate', 'Weight', 'LeanBodyMass'] as const;
const PERMS = RECORDS.map((recordType) => ({ accessType: 'read' as const, recordType }));

type Row = { ts: number; metric: string; value: number; step_s?: number };
export type GalaxyStatus = 'unsupported' | 'unavailable' | 'update-required' | 'needs-permission' | 'ready';
export type GalaxyLast = { at: number; sent: number; byMetric: Record<string, number>; error?: string };

// eslint-disable-next-line @typescript-eslint/no-require-imports
const hc = () => require('react-native-health-connect') as typeof import('react-native-health-connect');
let inited = false;

async function init(): Promise<GalaxyStatus> {
  if (!GALAXY_AVAILABLE) return 'unsupported';
  const m = hc();
  const s = await m.getSdkStatus();
  if (s === m.SdkAvailabilityStatus.SDK_UNAVAILABLE) return 'unavailable';
  if (s === m.SdkAvailabilityStatus.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED) return 'update-required';
  if (!inited) inited = await m.initialize();
  return inited ? 'ready' : 'unavailable';
}

async function hasAll(): Promise<boolean> {
  const g = await hc().getGrantedPermissions();
  const have = new Set(g.map((p: any) => p.recordType));
  return RECORDS.every((r) => have.has(r));
}

export const Galaxy = {
  /** Where the integration stands, without prompting the user. */
  async status(): Promise<GalaxyStatus> {
    try {
      const s = await init();
      if (s !== 'ready') return s;
      return (await hasAll()) ? 'ready' : 'needs-permission';
    } catch { return 'unavailable'; }
  },
  /** Opens Health Connect's consent sheet (the user taps Allow). Resolves true when everything was granted. */
  async connect(): Promise<{ ok: boolean; error?: string }> {
    try {
      const s = await init();
      if (s !== 'ready') return { ok: false, error: s === 'update-required' ? 'Update Health Connect in the Play Store first.' : 'Health Connect is not available on this phone.' };
      await hc().requestPermission(PERMS as any);
      return (await hasAll()) ? { ok: true } : { ok: false, error: 'Some permissions were not allowed. Allow all to sync everything.' };
    } catch (e: any) { return { ok: false, error: e?.message ?? 'Could not open Health Connect.' }; }
  },
  openSettings() { try { hc().openHealthConnectSettings(); } catch {} },
  async last(): Promise<GalaxyLast | null> {
    try { const v = await AsyncStorage.getItem(LAST); return v ? JSON.parse(v) : null; } catch { return null; }
  },
  /** Read Samsung Health records from Health Connect since `sinceMs` and map them to Telomy metric rows. */
  async read(sinceMs: number): Promise<Row[]> {
    const m = hc();
    const timeRangeFilter = { operator: 'between' as const, startTime: new Date(sinceMs).toISOString(), endTime: new Date().toISOString() };
    const all = async (recordType: (typeof RECORDS)[number]) => {
      const out: any[] = []; let pageToken: string | undefined;
      for (let i = 0; i < 40; i++) {
        const r: any = await m.readRecords(recordType as any, { timeRangeFilter, dataOriginFilter: [SHEALTH], pageSize: 1000, pageToken });
        out.push(...(r.records ?? [])); pageToken = r.pageToken;
        if (!pageToken) break;
      }
      return out;
    };
    const sec = (iso: string) => Math.floor(new Date(iso).getTime() / 1000);
    const rows: Row[] = [];

    // heart rate: bucket to 1-minute means (watch can emit 1 Hz during workouts)
    const buckets = new Map<number, number[]>();
    for (const r of await all('HeartRate')) for (const s of r.samples ?? []) {
      const t = Math.floor(sec(s.time) / 60) * 60; (buckets.get(t) ?? buckets.set(t, []).get(t)!).push(s.beatsPerMinute);
    }
    buckets.forEach((v, ts) => rows.push({ ts, metric: 'hr', value: Math.round(v.reduce((a, b) => a + b, 0) / v.length), step_s: 60 }));

    for (const r of await all('RestingHeartRate')) rows.push({ ts: sec(r.time), metric: 'rhr', value: r.beatsPerMinute, step_s: 86400 });
    for (const r of await all('OxygenSaturation')) rows.push({ ts: sec(r.time), metric: 'spo2', value: r.percentage, step_s: 60 });
    for (const r of await all('Steps')) {
      const a = sec(r.startTime), b = sec(r.endTime);
      rows.push({ ts: b, metric: 'steps', value: r.count, step_s: Math.max(60, b - a) });
    }
    for (const r of await all('Vo2Max')) rows.push({ ts: sec(r.time), metric: 'vo2max', value: r.vo2MillilitersPerMinuteKilogram, step_s: 86400 });
    for (const r of await all('BodyFat')) rows.push({ ts: sec(r.time), metric: 'body_fat_pct', value: r.percentage, step_s: 86400 });
    for (const r of await all('BasalMetabolicRate')) {
      const p = r.basalMetabolicRate; if (!p) continue;
      rows.push({ ts: sec(r.time), metric: 'bmr', value: Math.round(p.unit === 'watts' ? p.value * 20.6 : p.value), step_s: 86400 });
    }
    const kg = (x: any) => (x ? (x.unit === 'kilograms' ? x.value : x.unit === 'grams' ? x.value / 1000 : x.unit === 'pounds' ? x.value * 0.45359237 : null) : null);
    for (const r of await all('Weight')) { const v = kg(r.weight); if (v != null) rows.push({ ts: sec(r.time), metric: 'weight_kg', value: +v.toFixed(2), step_s: 86400 }); }
    for (const r of await all('LeanBodyMass')) { const v = kg(r.mass); if (v != null) rows.push({ ts: sec(r.time), metric: 'lean_mass_kg', value: +v.toFixed(2), step_s: 86400 }); }

    // sleep: one nightly summary per session, stamped at wake time (minutes per stage)
    for (const r of await all('SleepSession')) {
      const end = sec(r.endTime), start = sec(r.startTime);
      const mins: Record<string, number> = { sleep_deep_min: 0, sleep_rem_min: 0, sleep_light_min: 0, sleep_awake_min: 0 };
      for (const st of r.stages ?? []) {
        const d = (sec(st.endTime) - sec(st.startTime)) / 60;
        const k = st.stage === 5 ? 'sleep_deep_min' : st.stage === 6 ? 'sleep_rem_min' : st.stage === 4 || st.stage === 2 ? 'sleep_light_min' : st.stage === 1 || st.stage === 3 ? 'sleep_awake_min' : null;
        if (k) mins[k] += d;
      }
      const asleep = mins.sleep_deep_min + mins.sleep_rem_min + mins.sleep_light_min;
      const tst = asleep > 0 ? asleep : (end - start) / 60;   // no stages → the whole session
      rows.push({ ts: end, metric: 'sleep_tst_min', value: Math.round(tst), step_s: 86400 });
      if (asleep > 0) for (const [metric, v] of Object.entries(mins)) rows.push({ ts: end, metric, value: Math.round(v), step_s: 86400 });
    }
    return rows;
  },
  /** Read new Samsung Health data and POST it to /vitals/ingest (source 'galaxy'). Throttled unless forced. */
  async sync(force = false): Promise<GalaxyLast | null> {
    if (!GALAXY_AVAILABLE) return null;
    if (running) return null;
    if (!force && Date.now() - lastRun < MIN_INTERVAL_MS) return null;
    running = true; lastRun = Date.now();
    try {
      if ((await Galaxy.status()) !== 'ready') return null;
      let cur = 0; try { cur = Number(JSON.parse((await AsyncStorage.getItem(CURSOR)) || '{}').ts) || 0; } catch {}
      // re-read the last hour each time: Health Connect records can land late (30-60 min sync lag); server upserts
      const since = cur ? Math.max(cur - 3600, 0) * 1000 : Date.now() - BACKFILL_DAYS * 86400000;
      const rows = await Galaxy.read(since);
      let maxTs = cur; const byMetric: Record<string, number> = {};
      for (let i = 0; i < rows.length; i += 2000) {
        const chunk = rows.slice(i, i + 2000);
        await api('/vitals/ingest', { body: { samples: chunk, source: 'galaxy' } });
        for (const r of chunk) { maxTs = Math.max(maxTs, r.ts); byMetric[r.metric] = (byMetric[r.metric] ?? 0) + 1; }
      }
      const res: GalaxyLast = { at: Date.now(), sent: rows.length, byMetric };
      if (maxTs) await AsyncStorage.setItem(CURSOR, JSON.stringify({ ts: maxTs }));
      await AsyncStorage.setItem(LAST, JSON.stringify(res));
      return res;
    } catch (e: any) {
      const res: GalaxyLast = { at: Date.now(), sent: 0, byMetric: {}, error: e?.message ?? 'Sync failed' };
      try { await AsyncStorage.setItem(LAST, JSON.stringify(res)); } catch {}
      return res;
    } finally { running = false; }
  },
};
let lastRun = 0;
let running = false;
