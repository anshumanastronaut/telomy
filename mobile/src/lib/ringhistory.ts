// Longitudinal store for the ring's flash log. The ring measures itself every few minutes and we sync the log
// (see KYRing.swift / Ring.syncHistory); this collects those samples into one timeline, deduped by timestamp, kept
// on the phone only (nothing uploaded — the stock app's cloud upload is exactly what Telomy avoids). The paired
// HR+HRV samples here are what feed the HR↔HRV comparison and the recovery age clock over time.
import { useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ring, type RingHistorySample } from '../../modules/ky-ecg';
import { bandAvailable } from './band';

const KEY = 'telomy.ring.history.v1';
const MAX = 20000;                       // ~70 days at 5-min cadence across metrics; trims oldest beyond this
let samples: RingHistorySample[] = [];
let loaded = false;
const listeners = new Set<() => void>();

function emit() { listeners.forEach((l) => l()); }

async function persist() {
  try { await AsyncStorage.setItem(KEY, JSON.stringify(samples.slice(-MAX))); } catch {}
}

/** Merge a freshly synced dump into the timeline, deduping by (timestamp, metric). */
function merge(incoming: RingHistorySample[]) {
  if (!incoming.length) return;
  const seen = new Set(samples.map((s) => `${s.t}|${Object.keys(s).filter((k) => k !== 't').join(',')}`));
  let added = 0;
  for (const s of incoming) {
    const k = `${s.t}|${Object.keys(s).filter((x) => x !== 't').join(',')}`;
    if (!seen.has(k)) { samples.push(s); seen.add(k); added++; }
  }
  if (!added) return;
  samples.sort((a, b) => a.t - b.t);
  if (samples.length > MAX) samples = samples.slice(-MAX);
  persist();
  emit();
}

let started = false;
/** Called once at app start (from the root layout) to begin collecting. Safe to call when no ring is present. */
export function startRingHistory() {
  if (started || !bandAvailable) return;
  started = true;
  AsyncStorage.getItem(KEY).then((raw) => {
    if (raw) { try { samples = JSON.parse(raw); } catch {} }
    loaded = true; emit();
  });
  Ring.onHistory((h) => merge(h.samples));
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
  if (!loaded) {
    try { const raw = await AsyncStorage.getItem(KEY); if (raw) samples = JSON.parse(raw); } catch {}
    loaded = true;
  }
  return samples.filter((s) => s.t >= fromMs && s.t < toMs);
}
