// Longitudinal store for the ring's flash log. The ring measures itself every few minutes and we sync the log
// (see KYRing.swift / Ring.syncHistory); this collects those samples into one timeline, deduped by timestamp, kept
// on the phone only (nothing uploaded — the stock app's cloud upload is exactly what Telomy avoids). The paired
// HR+HRV samples here are what feed the HR↔HRV comparison and the recovery age clock over time.
import { useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ring, type RingHistorySample, type RingSleepRecord } from '../../modules/ky-ecg';
import { bandAvailable } from './band';

const KEY = 'telomy.ring.history.v2';
const OLD_KEY = 'telomy.ring.history.v1';   // v1: timestamps 1 tz-offset late (ring clock is local time) + duplicates
const MAX = 20000;                       // ~70 days at 5-min cadence across metrics; trims oldest beyond this
let samples: RingHistorySample[] = [];
let loaded = false;
const listeners = new Set<() => void>();

function emit() { listeners.forEach((l) => l()); }

async function persist() {
  try { await AsyncStorage.setItem(KEY, JSON.stringify(samples.slice(-MAX))); } catch {}
}

/** Dedup key: timestamp + the SORTED metric names (native dictionaries arrive in random key order — v1 keyed on
 *  that order and kept up to 24 copies of the same reading). */
const keyOf = (s: RingHistorySample) => `${s.t}|${Object.keys(s).filter((k) => k !== 't').sort().join(',')}`;
const plausible = (s: RingHistorySample) => s.t >= 1577836800000 && s.t <= Date.now() + 86400000 && (s.hr == null || (s.hr >= 30 && s.hr <= 220)) && (s.spo2 == null || (s.spo2 >= 70 && s.spo2 <= 100));

/** v1 → v2: shift to real time (the ring logged local wall-clock seconds; we read them as UTC), dedupe, drop junk. */
function migrate(old: RingHistorySample[]): RingHistorySample[] {
  const seen = new Set<string>(); const out: RingHistorySample[] = [];
  for (const s of old) {
    const t = s.t + new Date(s.t).getTimezoneOffset() * 60000;   // IST: −330 min → t − 5 h 30 min
    const f = { ...s, t };
    const k = keyOf(f);
    if (!seen.has(k) && plausible(f)) { seen.add(k); out.push(f); }
  }
  return out.sort((a, b) => a.t - b.t);
}

/** Merge a freshly synced dump into the timeline, deduping by (timestamp, metric set). */
function merge(incoming: RingHistorySample[]) {
  if (!incoming.length) return;
  const seen = new Set(samples.map(keyOf));
  let added = 0;
  for (const s of incoming) {
    const k = keyOf(s);
    if (!seen.has(k) && plausible(s)) { samples.push(s); seen.add(k); added++; }
  }
  if (!added) return;
  samples.sort((a, b) => a.t - b.t);
  if (samples.length > MAX) samples = samples.slice(-MAX);
  persist();
  emit();
}

let loading: Promise<void> | null = null;
/** Load v2, or migrate v1 once (kept until v2 is written, so nothing is lost if the app is killed mid-way). */
function load() {
  return (loading ??= (async () => {
    try {
      const raw = await AsyncStorage.getItem(KEY);
      if (raw) samples = JSON.parse(raw);
      else {
        const old = await AsyncStorage.getItem(OLD_KEY);
        if (old) { samples = migrate(JSON.parse(old)); await AsyncStorage.setItem(KEY, JSON.stringify(samples)); await AsyncStorage.removeItem(OLD_KEY); }
      }
    } catch {}
    loaded = true;
  })());
}

let started = false;
/** Called once at app start (from the root layout) to begin collecting. Safe to call when no ring is present. */
export function startRingHistory() {
  if (started || !bandAvailable) return;
  started = true;
  load().then(() => emit());
  Ring.onHistory((h) => merge(h.samples));
  Ring.onSleep((s) => mergeSleep(s.nights));
}

export type RingHistoryView = {
  loaded: boolean;
  count: number;
  /** Paired HR+HRV samples, newest first — the data for HR↔HRV comparison against the patch. */
  paired: RingHistorySample[];
  last24h: RingHistorySample[];
};

export function useRingHistory(): RingHistoryView {
  const [, setN] = useState(0);
  useEffect(() => { const l = () => setN((n) => n + 1); listeners.add(l); return () => { listeners.delete(l); }; }, []);
  const now = Date.now();
  return {
    loaded,
    count: samples.length,
    paired: samples.filter((s) => s.hr != null && s.hrv != null).slice().reverse(),
    last24h: samples.filter((s) => now - s.t <= 24 * 3600 * 1000),
  };
}

/** Pearson r between HR and HRV across all paired samples — the within-ring coupling, for the Devices comparison view. */
export function hrHrvCorrelation(): { r: number | null; n: number } {
  const pts = samples.filter((s) => s.hr != null && s.hrv != null).map((s) => [s.hr as number, s.hrv as number]);
  const n = pts.length;
  if (n < 5) return { r: null, n };
  const mx = pts.reduce((s, p) => s + p[0], 0) / n, my = pts.reduce((s, p) => s + p[1], 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (const [x, y] of pts) { sxy += (x - mx) * (y - my); sxx += (x - mx) ** 2; syy += (y - my) ** 2; }
  const den = Math.sqrt(sxx * syy);
  return { r: den ? sxy / den : null, n };
}

/** Ring samples with t (ms) in [fromMs, toMs) — loads the store on first use so engines can run before the UI mounts. */
export async function ringSamples(fromMs: number, toMs: number): Promise<RingHistorySample[]> {
  await load();
  return samples.filter((s) => s.t >= fromMs && s.t < toMs);
}

// ------------------------------------------------------------------ the ring's own sleep records

const SLEEP_KEY = 'telomy.ring.sleep.v1';
let sleepRecs: RingSleepRecord[] | null = null;
async function loadSleep() {
  if (sleepRecs) return sleepRecs;
  try { sleepRecs = JSON.parse((await AsyncStorage.getItem(SLEEP_KEY)) ?? '[]'); } catch { sleepRecs = []; }
  return sleepRecs!;
}
/** Keep one record per night start; a re-sync that arrives more complete (higher coverage) replaces the cut one. */
async function mergeSleep(incoming: RingSleepRecord[]) {
  const recs = await loadSleep();
  let changed = false;
  for (const r of incoming) {
    const i = recs.findIndex((x) => Math.abs(x.start - r.start) < 60);
    if (i < 0) { recs.push(r); changed = true; }
    else if (r.coverage > recs[i].coverage + 0.01 || r.end > recs[i].end + 60) { recs[i] = r; changed = true; }
  }
  if (!changed) return;
  recs.sort((a, b) => a.start - b.start);
  sleepRecs = recs.slice(-120);
  try { await AsyncStorage.setItem(SLEEP_KEY, JSON.stringify(sleepRecs)); } catch {}
  emit();
}
/** Ring sleep records overlapping [fromMs, toMs). */
export async function ringSleepRecords(fromMs: number, toMs: number) {
  return (await loadSleep()).filter((r) => r.end * 1000 >= fromMs && r.start * 1000 < toMs);
}
