// Smart sync of the longitudinal vitals record. The patch stores a compact vital summary continuously on-device
// (KYBand.publish → KYWellnessStore "vitals", ~10 s while connected); the ring keeps a 5-minute HR/SpO₂/temp log.
// This queue batches whatever is new into POST /vitals/ingest, idempotently (the server upserts), advancing a cursor so
// re-runs are cheap. WHOOP isn't synced here — NOOP already pushes it to the server continuously. Runs throttled on app
// load/foreground; a gap (device was off, or offline) is simply backfilled next time the data is available.
import AsyncStorage from '@react-native-async-storage/async-storage';

import { api } from '@/lib/api';
import { Band, type RingHistorySample } from '../../modules/ky-ecg';
import { ringSamples } from '@/lib/ringhistory';
import { JCVital } from '@/lib/jcvitalsource';

const CURSOR = 'telomy.vitals.cursor.v1';   // { patch: lastTs, ring: lastTs }
const MIN_INTERVAL_MS = 2 * 60 * 1000;
let lastRun = 0;
let running = false;

type Row = { ts: number; metric: string; value: number; step_s?: number };

async function cursor(): Promise<Record<string, number>> {
  try { return JSON.parse((await AsyncStorage.getItem(CURSOR)) || '{}'); } catch { return {}; }
}
async function setCursor(c: Record<string, number>) {
  try { await AsyncStorage.setItem(CURSOR, JSON.stringify(c)); } catch {}
}

/** Patch vitals from the native all-day store → ingest rows (hr, hrv, motion). */
async function patchRows(since: number): Promise<Row[]> {
  const recs = await Band.wellnessRead('vitals', 3).catch(() => [] as Record<string, any>[]);
  const out: Row[] = [];
  for (const r of recs) {
    const ts = Number(r.ts);
    if (!ts || ts <= since) continue;
    const step = Number(r.step_s) || 10;
    if (r.hr != null) out.push({ ts, metric: 'hr', value: Number(r.hr), step_s: step });
    if (r.hrv != null) out.push({ ts, metric: 'hrv', value: Number(r.hrv), step_s: step });
    if (r.motion != null) out.push({ ts, metric: 'motion', value: Number(r.motion), step_s: step });
  }
  return out;
}

/** Ring 5-minute history → ingest rows (hr, spo2, temp). */
async function ringRows(since: number): Promise<Row[]> {
  const now = Date.now();
  const samples: RingHistorySample[] = await ringSamples(now - 3 * 86400000, now).catch(() => []);
  const out: Row[] = [];
  for (const s of samples) {
    const ts = Math.floor(s.t / 1000);
    if (!ts || ts <= since) continue;
    if (s.hr != null) out.push({ ts, metric: 'hr', value: s.hr, step_s: 300 });
    if (s.hrv != null) out.push({ ts, metric: 'hrv', value: s.hrv, step_s: 300 });
    if (s.spo2 != null) out.push({ ts, metric: 'spo2', value: s.spo2, step_s: 300 });
    if (s.temp != null) out.push({ ts, metric: 'skin_temp', value: s.temp, step_s: 300 });
  }
  return out;
}

async function push(source: string, rows: Row[]): Promise<number> {
  if (!rows.length) return 0;
  let maxTs = 0;
  // chunk to keep requests small; idempotent so partial success is safe
  for (let i = 0; i < rows.length; i += 2000) {
    const chunk = rows.slice(i, i + 2000);
    await api('/vitals/ingest', { body: { samples: chunk, source } });
    for (const r of chunk) maxTs = Math.max(maxTs, r.ts);
  }
  return maxTs;
}

/** JCVital V8 continuous buffer → ingest rows (hr, spo2, skin_temp). Source lib/jcvitalsource.ts. */
function jcvitalRows(since: number): Row[] {
  const out: Row[] = [];
  for (const b of JCVital.rows(since)) {
    if (!b.ts || b.ts <= since) continue;
    if (b.hr != null) out.push({ ts: b.ts, metric: 'hr', value: b.hr, step_s: 10 });
    if (b.spo2 != null) out.push({ ts: b.ts, metric: 'spo2', value: b.spo2, step_s: 10 });
    if (b.temp != null) out.push({ ts: b.ts, metric: 'skin_temp', value: b.temp, step_s: 10 });
  }
  return out;
}

/** Sync the longitudinal vitals. Throttled; safe to call often (on load, on foreground). */
export async function syncVitals(force = false): Promise<void> {
  if (running) return;
  if (!force && Date.now() - lastRun < MIN_INTERVAL_MS) return;
  running = true; lastRun = Date.now();
  try {
    const c = await cursor();
    const [pr, rr] = await Promise.all([patchRows(c.patch ?? 0), ringRows(c.ring ?? 0)]);
    const jr = jcvitalRows(c.jcvital ?? 0);
    const next = { ...c };
    const pMax = await push('patch', pr); if (pMax) next.patch = pMax;
    const rMax = await push('ring', rr); if (rMax) next.ring = rMax;
    const jMax = await push('jcvital', jr); if (jMax) next.jcvital = jMax;
    if (pMax || rMax || jMax) await setCursor(next);
  } catch { /* offline or no device — try again next time; nothing is lost */ }
  finally { running = false; }
}
