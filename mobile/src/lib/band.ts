// Live ECG band state for the whole app: one native subscription set, an ECG ring buffer for the monitor,
// recent beats and HR history, per-minute summaries uploaded to the backend, and session sample capture.
import { useEffect, useSyncExternalStore } from 'react';
import { AppState } from 'react-native';
import { Band, isAvailable, type BandMetrics, type BandStatus, type EcgFrame, type FoundDevice, type RecordingEvent, type RhythmEvent } from '../../modules/ky-ecg';
import { api } from './api';

export { isAvailable as bandAvailable };
export type { BandMetrics, BandStatus, FoundDevice, RecordingEvent, RhythmEvent };

const FS = 100;
const RING_SECONDS = 12;

/** ECG display samples (filtered, µV) in a ring; `ecgEnd` is the absolute index one past the newest sample. */
export const ecg = {
  data: new Float32Array(FS * RING_SECONDS),
  end: 0,
  /** unix time of absolute sample index 0 */
  t0: 0,
  lastArrival: 0,
  at(i: number) {
    return this.data[((i % this.data.length) + this.data.length) % this.data.length];
  },
};

type Snapshot = {
  status: BandStatus | null;
  metrics: BandMetrics | null;
  devices: FoundDevice[];
  recording: RecordingEvent | null;
  lastBeatAt: number;
  rr: { t: number; rr: number }[];          // last 300 beats
  hr: { t: number; hr: number }[];          // last 30 min, ~1/s
  frames: number;
  rhythm: RhythmEvent[];                     // this session's rhythm/signal events (newest last)
};

let snap: Snapshot = { status: null, metrics: null, devices: [], recording: null, lastBeatAt: 0, rr: [], hr: [], frames: 0, rhythm: [] };
const listeners = new Set<() => void>();
// No re-renders while the app is in the background (screen locked overnight): iOS kills apps that use > 80 % CPU there.
// Data keeps flowing into the store; screens catch up once when the app comes back.
let foreground = AppState.currentState === 'active';
AppState.addEventListener('change', (s) => {
  foreground = s === 'active';
  if (foreground) listeners.forEach((l) => l());
});
export const isForeground = () => foreground;
function set(patch: Partial<Snapshot>) {
  snap = { ...snap, ...patch };
  if (foreground) listeners.forEach((l) => l());
}

// ------------------------------------------------------------------ minute summaries → backend

type Minute = {
  ts: string; hr: number[]; beats: number; rmssd?: number; sdnn?: number; quality: Record<string, number>; artefact?: number;
  activity: Record<string, number>; sleep: Record<string, number>; motion: number[]; resting?: number;
};
const top = (c: Record<string, number>) => Object.entries(c).sort((a, b) => b[1] - a[1])[0]?.[0];
let minute: Minute | null = null;
let outbox: object[] = [];

function localMinute(t: number) {
  const d = new Date(t * 1000);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

function closeMinute() {
  if (!minute) return;
  if (!minute.hr.length) { Band.log(`minute ${minute.ts} skipped: no clean heart rate (${JSON.stringify(minute.quality)})`); return; }
  const q = top(minute.quality);
  const rec = {
    ts: minute.ts,
    hr: Math.round((minute.hr.reduce((a, b) => a + b, 0) / minute.hr.length) * 10) / 10,
    rmssd: minute.rmssd, sdnn: minute.sdnn, beats: minute.beats, quality: q, artefact_pct: minute.artefact,
  };
  outbox.push(rec);
  // on-phone copy for offline scores (strain, stress, zones): see lib/wellness.ts
  Band.wellnessAppend('minutes', {
    ...rec, activity: top(minute.activity), sleep: top(minute.sleep), resting: minute.resting,
    motion: minute.motion.length ? Math.round((minute.motion.reduce((a, b) => a + b, 0) / minute.motion.length) * 100) / 100 : null,
  });
  flush();
}

async function flush() {
  if (!outbox.length) return;
  const items = outbox;
  outbox = [];
  try {
    await api('/band/minutes', { body: { items } });
    Band.log(`uploaded ${items.length} minute(s)`);
  } catch (e: any) {
    Band.log(`upload failed: ${e?.message ?? e}`);
    outbox = [...items, ...outbox].slice(-1440); // keep up to a day and retry with the next minute
  }
}

// HRV values on screen refresh every 10 s (they describe the last 1–5 min; per-beat updates only add twitch).
let hrvShownAt = 0;
let hrvShown: Partial<BandMetrics> = {};
const HRV_KEYS = ['rmssd60', 'sdnn60', 'pnn50', 'rmssd300', 'sdnn300', 'meanNN60', 'artefactPercent', 'irregularBeats60', 'hrvReliable', 'rmssdSmooth', 'rmssd5', 'hrvState'] as const;

function onMetrics(m: BandMetrics) {
  try { handleMetrics(m); } catch (e: any) { Band.log(`onMetrics error: ${e?.message ?? e}`); }
}

function handleMetrics(raw: BandMetrics) {
  if (raw.t - hrvShownAt >= 10 || (raw.hrvReliable && !hrvShown.hrvReliable)) {
    hrvShownAt = raw.t;
    hrvShown = Object.fromEntries(HRV_KEYS.map((k) => [k, raw[k]])) as Partial<BandMetrics>;
  }
  const m = { ...raw, ...hrvShown } as BandMetrics;
  const key = localMinute(raw.t);
  if (!minute || minute.ts !== key) {
    closeMinute();
    minute = { ts: key, hr: [], beats: 0, quality: {}, activity: {}, sleep: {}, motion: [] };
  }
  if (m.hr && (m.quality === 'good' || m.quality === 'acceptable')) minute.hr.push(m.hr);
  minute.quality[m.quality] = (minute.quality[m.quality] ?? 0) + 1;
  if (raw.hrvReliable) { minute.rmssd = raw.rmssd60; minute.sdnn = raw.sdnn60; }
  minute.artefact = raw.artefactPercent;
  if (raw.activity) minute.activity[raw.activity] = (minute.activity[raw.activity] ?? 0) + 1;
  if (raw.sleep) minute.sleep[raw.sleep] = (minute.sleep[raw.sleep] ?? 0) + 1;
  if (raw.motionIndex != null) minute.motion.push(raw.motionIndex);
  if (raw.restingHr) minute.resting = Math.round(raw.restingHr * 10) / 10;
  const hr = m.hr ? [...snap.hr.filter((p) => p.t > m.t - 1800), { t: m.t, hr: m.hr }] : snap.hr;
  set({ metrics: m, hr });
  sessionCapture.forEach((c) => c.onMetrics(raw));
}

// ------------------------------------------------------------------ session capture (therapy sessions)

type Capture = { onMetrics: (m: BandMetrics) => void; onBeat: (t: number, rr: number) => void };
const sessionCapture = new Set<Capture>();

/** Collects 5-second samples {t, hr, rr_ms} for a therapy session while active. */
export function startSessionCapture() {
  const start = Date.now() / 1000;
  const samples: { t: number; hr?: number; rr_ms: number[] }[] = [];
  let bucket: { t: number; hr?: number; rr_ms: number[] } = { t: 0, rr_ms: [] };
  const cap: Capture = {
    onMetrics(m) {
      const t = Math.floor((m.t - start) / 5) * 5;
      if (t !== bucket.t) {
        if (bucket.rr_ms.length || bucket.hr) samples.push(bucket);
        bucket = { t, rr_ms: [] };
      }
      if (m.hr && m.quality !== 'no_contact' && m.quality !== 'poor') bucket.hr = Math.round(m.hr * 10) / 10;
    },
    onBeat(_t, rr) { bucket.rr_ms.push(Math.round(rr)); },
  };
  sessionCapture.add(cap);
  return {
    count: () => samples.length,
    stop() {
      sessionCapture.delete(cap);
      if (bucket.rr_ms.length || bucket.hr) samples.push(bucket);
      return samples.filter((s) => s.hr || s.rr_ms.length >= 3);
    },
  };
}

// ------------------------------------------------------------------ native subscriptions (once)

let started = false;
function start() {
  if (started || !isAvailable) return;
  started = true;
  Band.on('onStatus', (s) => set({ status: s }));
  Band.on('onDevice', (d) => set({ devices: [...snap.devices.filter((x) => x.id !== d.id), d].sort((a, b) => b.rssi - a.rssi) }));
  Band.on('onEcg', (f: EcgFrame) => {
    if (!ecg.end || Math.abs(f.t - (ecg.t0 + ecg.end / FS)) > 2) {
      // first frame, or a gap/restart: re-anchor the ring's clock
      ecg.t0 = f.t - ecg.end / FS;
    }
    for (const v of f.display) { ecg.data[ecg.end % ecg.data.length] = v; ecg.end += 1; }
    ecg.lastArrival = Date.now() / 1000;
    set({ frames: snap.frames + 1 });
  });
  Band.on('onBeat', (b) => {
    if (b.rr) {
      if (minute) minute.beats += 1;
      set({ lastBeatAt: Date.now(), rr: [...snap.rr.slice(-299), { t: b.t, rr: b.rr }] });
      sessionCapture.forEach((c) => c.onBeat(b.t, b.rr!));
    } else set({ lastBeatAt: Date.now() });
  });
  Band.on('onMetrics', onMetrics);
  Band.on('onRhythm', (e) => {
    // update in place when an open episode extends; send each finished/updated episode to the server
    const rhythm = [...snap.rhythm.filter((x) => !(x.type === e.type && Math.abs(x.start - e.start) < 1)), e].slice(-100);
    set({ rhythm });
    api('/band/events', { body: { items: [{ type: e.type, start: e.start, end: e.end, detail: e.detail }] } }).catch(() => Band.log(`event upload failed: ${e.type}`));
  });
  Band.on('onRecording', (r) => {
    set({ recording: r });
    if (r.phase === 'completed' && r.durationSec && r.durationSec > 30) {
      const d = new Date(r.start * 1000).toISOString().slice(0, 19);
      api('/band/recordings', { body: { start_ts: d, duration_s: r.durationSec, beats: r.beats, mean_hr: r.meanHr, rmssd: r.rmssd, sdnn: r.sdnn, artefact_pct: r.artefactPercent, rr: r.rr, sleep: r.sleep } }).catch(() => {});
      if (r.events?.length) api('/band/events', { body: { items: r.events.map((e) => ({ ...e, source: 'recording' })) } }).catch(() => {});
    }
  });
  set({ status: Band.getStatus() });
  Band.autoConnect();
}

/** Subscribe a component to the band snapshot. Starts the native subscriptions on first use. */
export function useBand(): Snapshot {
  useEffect(start, []);
  return useSyncExternalStore((cb) => { listeners.add(cb); return () => listeners.delete(cb); }, () => snap);
}

export function clearDevices() { set({ devices: [] }); }

// Live streaming is shared: the monitor and a running therapy session can both need it.
let streamUsers = 0;
/** Ask the band to stream live ECG; call the returned function when done. */
export function acquireStream(): () => void {
  if (!isAvailable) return () => {};
  start();
  if (streamUsers++ === 0) Band.startStream();
  let released = false;
  return () => {
    if (released) return;
    released = true;
    if (--streamUsers === 0) Band.stopStream();
  };
}

export { Band };
