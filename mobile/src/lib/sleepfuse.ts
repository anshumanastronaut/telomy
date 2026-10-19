// Sleep from every device, fused into one night per date, plus sleep need, sleep debt and the Sleep Regularity Index.
//
// Source priority (best evidence first, one night per date, never double-counted):
//   1. Telomy patch: ECG staging (Conv1d + BiGRU on HRV + ECG-derived breathing, KYSleepStager) — 4 stages.
//   2. Apple Watch stages from Apple Health: independent PSG studies put Apple's 4-stage kappa at ≈ 0.53–0.60
//      (Schyvens et al. 2025; Robbins et al. 2024), the most independently validated consumer stager.
//   3. Ring only: sleep/wake from the ring's own 5-minute heart-rate log + iPhone motion (no stages — a 5-minute HR
//      series cannot stage sleep honestly), with the night's lowest HR and the ring's overnight HRV.
//   4. Other Apple Health sleep (iPhone schedule, third-party apps): duration and timing only.
// The ring's 5-min HR fills lowest HR / HRV into Watch nights when the ring was worn too.
//
// Sleep need follows WHOOP's published idea (need = baseline + strain + debt − naps), with transparent terms:
//   baseline 8 h (NSF 7–9 h) until 14 nights, then personal (mean of your longer half of nights, the sleep-extension
//   asymptote, Klerman & Dijk 2005), clamped 7–9 h; strain adds up to 45 min; the carried sleep debt is added.
// Sleep debt: need = base + strain + debt; next debt = 0.55 × max(0, need − slept) (fitted by NOOP on 853 WHOOP
//   nights; Van Dongen 2003 / Banks 2010 for why deficits carry over partially).
// Sleep Regularity Index (Phillips et al. 2017): −100 + 200 · P(same sleep/wake state 24 h apart), 5-min bins.
import type { HealthSleepSegment, PhoneActivity, RingHistorySample, RingSleepRecord } from '../../modules/ky-ecg';
import type { Night } from './wellness-core';

export type SleepSource = 'patch' | 'whoop' | 'watch' | 'ring' | 'health';
export const SOURCE_LABEL: Record<SleepSource, string> = {
  patch: 'Telomy patch · ECG stages', whoop: 'WHOOP · motion + heart rate, staged by Telomy', watch: 'Apple Watch · stages', ring: 'Telomy ring · heart rate + phone motion', health: 'Apple Health · duration',
};

const EPOCH = 30;
const localDate = (t: number) => { const d = new Date(t * 1000); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
const mean = (a: number[]) => a.reduce((s, v) => s + v, 0) / a.length;
const median = (a: number[]) => { const s = [...a].sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : NaN; };
const pct = (a: number[], q: number) => { const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(q * s.length))]; };

/** Night summary from a 30-s stage grid (0 wake, 1 light, 2 deep, 3 REM, 4 asleep-unstaged, -1 no data). */
function summarise(grid: number[], t0: number, staged: boolean): Omit<Night, 'id' | 'date' | 'hr5' | 'hrv5' | 'events'> | null {
  const asleep = grid.map((s) => s > 0);
  const first = asleep.indexOf(true), last = asleep.lastIndexOf(true);
  if (first < 0) return null;
  const span = grid.slice(first, last + 1).filter((s) => s >= 0);
  const tst = span.filter((s) => s > 0).length / 2;
  let awak = 0, run = 0;
  for (const s of span) { if (s === 0) run++; else { if (run >= 2) awak++; run = 0; } }
  const n = (c: number) => span.filter((s) => s === c).length / 2;
  const known = grid.filter((s) => s >= 0).length;
  const remAt = staged ? grid.indexOf(3) : -1;
  // REM cycles: REM bouts ≥ 5 min separated by ≥ 15 min of non-REM
  let cycles = 0, remRun = 0, gap = 99, gapBefore = 99;
  if (staged) for (const s of span) {
    if (s === 3) { if (remRun === 0) gapBefore = gap; remRun++; if (remRun === 10 && gapBefore >= 30) cycles++; gap = 0; }
    else { remRun = 0; gap++; }
  }
  return {
    start: t0, end: t0 + grid.length * EPOCH, tstMin: tst, efficiency: known ? tst / (known / 2) : 0,
    onsetMin: grid.slice(0, first).filter((s) => s >= 0).length / 2, wasoMin: n(0), awakenings: awak,
    hypnogram: grid.map((s) => (s < 0 ? 0 : s > 0 ? 1 : 0)), epochSec: EPOCH,
    midpoint: t0 + ((first + last + 1) / 2) * EPOCH,
    ...(staged ? { stages: grid.map((s) => (s === 4 ? 1 : s)), lightMin: n(1) + n(4), deepMin: n(2), remMin: n(3),
      remLatencyMin: remAt >= 0 ? (remAt - first) / 2 : undefined, remCycles: cycles } : {}),
  };
}

/** Ring HR/HRV during a night: mean sleeping HR, lowest 15-min HR (and where in the night), median HRV. */
function ringOverlay(n: Night, ring: RingHistorySample[], dayHr: number | null): Partial<Night> {
  const inN = ring.filter((s) => s.t / 1000 >= n.start && s.t / 1000 < n.end);
  const hr = inN.filter((s) => s.hr).map((s) => ({ t: s.t / 1000, v: s.hr! }));
  const out: Partial<Night> = {};
  if (hr.length >= 12) {
    out.sleepHr = mean(hr.map((x) => x.v));
    let lo = Infinity, at = 0;
    for (let i = 1; i + 1 < hr.length; i++) { const m = (hr[i - 1].v + hr[i].v + hr[i + 1].v) / 3; if (m < lo) { lo = m; at = hr[i].t; } }
    if (isFinite(lo)) { out.lowestHr = lo; out.lowestHrAt = at; out.lowestHrPos = (at - n.start) / Math.max(1, n.end - n.start); }
    if (dayHr) out.hrDropPct = 100 * (1 - out.sleepHr / dayHr);
    out.hr5 = hr.map((x) => [x.t, x.v, x.v] as [number, number, number]);
  }
  const temp = inN.filter((s) => s.temp && s.temp >= 30 && s.temp <= 42).map((s) => s.temp!);
  if (temp.length >= 6) { out.skinTemp = median(temp); out.tempSrc = 'ring'; }
  const hrv = inN.filter((s) => s.hrv).map((s) => s.hrv!);
  if (hrv.length >= 6) { out.sleepRmssd = median(hrv); out.hrvSrc = 'ring'; }
  return out;
}

/** Daytime mean ring HR (10:00–20:00) the day before a night, for the nocturnal dip. */
function dayHrBefore(start: number, ring: RingHistorySample[]) {
  const d = new Date(start * 1000); d.setHours(10, 0, 0, 0);
  let a = d.getTime() / 1000; if (a > start) a -= 86400;
  const v = ring.filter((s) => s.hr && s.t / 1000 >= a && s.t / 1000 < a + 10 * 3600).map((s) => s.hr!);
  return v.length >= 24 ? mean(v) : null;
}

// ------------------------------------------------------------------ Apple Health nights

/** Cluster segments into nights (gaps < 2 h), one source per night (Watch stages preferred), ≥ 3 h asleep. */
export function healthNights(segs: HealthSleepSegment[]): Night[] {
  const out: Night[] = [];
  const sorted = [...segs].sort((a, b) => a.start - b.start);
  const clusters: HealthSleepSegment[][] = [];
  for (const s of sorted) {
    const c = clusters[clusters.length - 1];
    if (c && s.start - Math.max(...c.map((x) => x.end)) < 2 * 3600) c.push(s); else clusters.push([s]);
  }
  for (const c of clusters) {
    const staged = c.filter((s) => s.stage >= 1 && s.stage <= 3);
    const bySrc = new Map<string, HealthSleepSegment[]>();
    for (const s of c) bySrc.set(s.source, [...(bySrc.get(s.source) ?? []), s]);
    const asleepMin = (a: HealthSleepSegment[]) => a.filter((s) => s.stage >= 1 && s.stage <= 4).reduce((m, s) => m + (s.end - s.start) / 60, 0);
    // the source with staged segments wins; otherwise the one with the most sleep
    const stagedSrc = staged.length ? staged[0].source : null;
    const src = stagedSrc ?? [...bySrc.entries()].sort((a, b) => asleepMin(b[1]) - asleepMin(a[1]))[0][0];
    const use = bySrc.get(src)!;
    if (asleepMin(use) < 180) continue;
    const t0 = Math.min(...use.map((s) => s.start)), t1 = Math.max(...use.map((s) => s.end));
    const grid = new Array(Math.ceil((t1 - t0) / EPOCH)).fill(-1);
    // in-bed first (as wake), then sleep stages over it, awake last
    for (const pass of [5, 4, 1, 2, 3, 0]) for (const s of use) if (s.stage === pass) {
      for (let i = Math.floor((s.start - t0) / EPOCH); i < Math.ceil((s.end - t0) / EPOCH) && i < grid.length; i++) grid[i] = pass === 5 ? 0 : pass;
    }
    const isStaged = !!stagedSrc;
    const sm = summarise(grid, t0, isStaged);
    if (!sm) continue;
    const watch = isStaged || use.some((s) => s.watch);
    out.push({ ...sm, id: `hk-${Math.round(t0)}`, date: localDate(sm.end), hr5: [], hrv5: [], events: [],
      source: watch && isStaged ? 'watch' : 'health', sourceName: src });
  }
  return out;
}

// ------------------------------------------------------------------ WHOOP nights (server: NOOP push → /whoop/nights)

export type WhoopNightIn = { start: number; end: number; stages?: { start: number; end: number; stage: string }[] | null;
  restingHr?: number; restingHrAt?: number; sleepHr?: number; skinTemp?: number; hr5?: [number, number, number][] };
const WSTAGE: Record<string, number> = { wake: 0, light: 1, deep: 2, rem: 3 };

/**
 * WHOOP sessions as Telomy nights. Sleep/wake comes from NOOP's motion-first detection (κ 0.84 vs our ring's 0.62 on
 * 2026-10-18), resting HR from the strap's 1 Hz HR (matches ECG within ~1 bpm). WHOOP HRV is NOT used (WHOOP 4.0
 * history R-R is re-delivered; inflated vs ECG). A daytime session (centre 10:00–19:00) counts as a nap only when its
 *  mean HR is within 5 bpm of the night-time sleeping HR — a still sofa afternoon is not sleep (seen 2026-10-18:
 * daytime HR ~15 % above the overnight sleeping HR).
 */
export function whoopNights(list: WhoopNightIn[]): Night[] {
  const nightHr = list.filter((w) => { const h = new Date(((w.start + w.end) / 2) * 1000).getHours(); return h < 10 || h >= 19; })
    .map((w) => w.sleepHr).filter((x): x is number => x != null);
  const ref = nightHr.length ? median(nightHr) : null;
  const out: Night[] = [];
  for (const w of list) {
    if (!w.end || w.end - w.start < 20 * 60) continue;
    const h = new Date(((w.start + w.end) / 2) * 1000).getHours();
    if (h >= 10 && h < 19 && (ref == null || w.sleepHr == null || w.sleepHr > ref + 5)) continue;
    const grid = new Array(Math.ceil((w.end - w.start) / EPOCH)).fill(-1);
    const staged = !!w.stages?.length;
    for (const seg of w.stages ?? []) {
      const c = WSTAGE[seg.stage] ?? 1;
      for (let i = Math.max(0, Math.floor((seg.start - w.start) / EPOCH)); i < Math.min(grid.length, Math.ceil((seg.end - w.start) / EPOCH)); i++) grid[i] = c;
    }
    if (!staged) grid.fill(4);
    const sm = summarise(grid, w.start, staged);
    if (!sm) continue;
    out.push({ ...sm, id: `whoop-${w.start}`, date: localDate(sm.end), hr5: w.hr5 ?? [], hrv5: [], events: [], source: 'whoop', sourceName: 'WHOOP',
      lowestHr: w.restingHr, lowestHrAt: w.restingHrAt, lowestHrPos: w.restingHrAt ? (w.restingHrAt - w.start) / (w.end - w.start) : undefined,
      sleepHr: w.sleepHr, skinTemp: w.skinTemp, tempSrc: w.skinTemp != null ? 'whoop' : undefined });
  }
  return out;
}

// ------------------------------------------------------------------ the ring's own sleep (its accelerometer)

const RSTAGE: Record<number, number> = { 241: 2, 242: 1, 243: 3, 244: 0 };
/**
 * The ring firmware's own sleep records → nights. Onset matched WHOOP within 1 min on 2026-10-18; its stage
 * accuracy is unknown (never validated against PSG), so stages are shown but the vendor's labels are trusted less
 * than the patch's. Records cut by a BLE drop: if ≥ 50 % of the span has segments the gaps count as unstaged sleep
 * (the ring only writes a record while it believes you are asleep); below 50 % the record is skipped and the
 * heart-rate method covers the night instead. Consecutive records < 90 min apart are merged by mergeFragments.
 */
export function ringOwnNights(recs: RingSleepRecord[]): Night[] {
  const out: Night[] = [];
  for (const r of recs) {
    if (r.end - r.start < 20 * 60 || r.coverage < 0.5) continue;
    const grid = new Array(Math.ceil((r.end - r.start) / EPOCH)).fill(4);
    for (const s of r.segments) {
      const c = RSTAGE[s.type];
      if (c == null) continue;
      for (let i = Math.max(0, Math.floor((s.start - r.start) / EPOCH)); i < Math.min(grid.length, Math.ceil((s.start + s.len - r.start) / EPOCH)); i++) grid[i] = c;
    }
    const staged = r.coverage >= 0.8;
    const sm = summarise(staged ? grid.map((x) => (x === 4 ? 1 : x)) : grid.map((x) => (x > 0 ? 4 : x)), r.start, staged);
    if (sm) out.push({ ...sm, id: `ringsleep-${r.start}`, date: localDate(sm.end), hr5: [], hrv5: [], events: [], source: 'ring', sourceName: 'Telomy ring (its own sleep sensor)' });
  }
  return out;
}

// ------------------------------------------------------------------ ring-only nights

/**
 * Sleep/wake from the ring's 5-min HR log + iPhone motion, for nights with no patch, WHOOP or Watch.
 * v2 (2026-10-19, after the virtual-population run showed −112 min bias and shift-work sleep invisible):
 *  • searches the whole timeline (any hour), not only 20:00–12:00;
 *  • a sample is asleep-like when HR ≤ personal sleep floor + max(10 bpm, 15 %) (band widened to the ring's measured
 *    ±5 bpm noise), OR when the phone is lying still and HR ≤ floor + max(16 bpm, 25 %) — the phone resting on the
 *    nightstand is strong evidence of being in bed (motion first, heart second);
 *  • the phone walking always means awake; 3-sample median smoothing; gaps ≤ 30 min bridged; runs ≥ 3 h are nights,
 *    runs of 30 min–3 h in the daytime are naps only when HR dips ≥ 8 % below the day's median AND the phone lay still.
 * Floor = 10th percentile of the trailing 7 days' HR (personal, robust to one hot night). No stages are claimed.
 */
/**
 * Coarse 4-stage estimate for a ring-only night, from the 5-minute heart-rate curve + phone motion. No ring gives
 * beat-to-beat HRV to the phone, so this can't match the patch or a watch — it is the cardiac-only method the first
 * consumer rings used (de Zambotti 2019; Oura's pre-PPG-HRV generation). Rules grounded in sleep physiology:
 *   • Deep (SWS): heart rate near its nightly trough with little 5-min-to-5-min change; parasympathetic dominance,
 *     front-loaded into the first half of the night (Carskadon & Dement).
 *   • REM: heart rate lifts back toward waking level and becomes variable, with the body still (atonia → phone not
 *     moving); clustered, and essentially absent in the first ~15 min after onset (normal REM latency 70–120 min).
 *   • Light (N1/N2): everything else — the bulk of the night.
 * Returned at 5-min resolution (each sample fills its 10 epochs); marked low-confidence so the app labels it and the
 * sleep score trusts it less than the patch.
 */
function ringStageGrid(samples: { t: number; v: number; still: boolean }[], t0: number, nEpoch: number): number[] {
  const grid = new Array(nEpoch).fill(0);                         // 0 wake until proven asleep
  if (samples.length < 6) { for (const s of samples) fill(grid, s.t, t0, 4); return grid; }
  const vals = samples.map((s) => s.v);
  const trough = pct(vals, 0.08), p40 = pct(vals, 0.40), p60 = pct(vals, 0.60);
  const span = Math.max(4, p60 - trough);
  const vrOf = (i: number) => {                                   // local |Δ| to neighbours: variability proxy
    const a = i > 0 ? Math.abs(samples[i].v - samples[i - 1].v) : 0;
    const b = i < samples.length - 1 ? Math.abs(samples[i + 1].v - samples[i].v) : 0;
    return (a + b) / (i > 0 && i < samples.length - 1 ? 2 : 1);
  };
  const vr = samples.map((_, i) => vrOf(i));
  const vrHi = pct(vr, 0.6);
  const onset = samples[0].t;
  const stageAt = samples.map((s, i) => {
    const sinceOnset = (s.t - onset) / 60;
    const low = (s.v - trough) / span;                            // 0 at trough … 1 near p60
    if (s.v <= p40 && vr[i] <= vrHi && sinceOnset > 5) return 2;  // deep: low, steady HR
    if (s.v >= p60 && vr[i] >= vrHi && s.still && sinceOnset > 15) return 3;  // REM: raised, variable, still, not at onset
    void low;
    return 1;                                                     // light
  });
  // median-3 smoothing, then cap deep after the first half (SWS is front-loaded; late "deep" is usually light)
  const sm = stageAt.map((_, i) => median(stageAt.slice(Math.max(0, i - 1), i + 2)));
  const halfT = (samples[0].t + samples[samples.length - 1].t) / 2;
  samples.forEach((s, i) => { let st = sm[i]; if (st === 2 && s.t > halfT && s.v > trough + 0.5 * span) st = 1; fill(grid, s.t, t0, st); });
  return grid;
}

function fill(grid: number[], t: number, t0: number, stage: number) {
  for (let e = 0; e < 10; e++) { const j = Math.floor((t - t0) / EPOCH) + e; if (j >= 0 && j < grid.length) grid[j] = stage; }
}

export function ringNights(ring: RingHistorySample[], phone: PhoneActivity[], days = 14): Night[] {
  const now = Date.now() / 1000;
  // one reading per timestamp: the heart log (type 6) and the combined log (type 9) both carry HR at the same instant
  const byT = new Map<number, number>();
  for (const s of ring) if (s.hr && s.t / 1000 >= now - days * 86400) byT.set(s.t, s.hr);
  const hr = [...byT].map(([t, v]) => ({ t: t / 1000, v })).sort((a, b) => a.t - b.t);
  if (hr.length < 36) return [];
  // O(n log n): phone intervals sorted once and looked up by binary search; HR floor computed once per day
  const ph = [...phone].sort((a, b) => a.start - b.start);
  const typeAt = (t: number) => {
    let lo = 0, hi = ph.length - 1, hit: PhoneActivity | null = null;
    while (lo <= hi) { const m = (lo + hi) >> 1; if (ph[m].start <= t) { hit = ph[m]; lo = m + 1; } else hi = m - 1; }
    for (let k = hit ? ph.indexOf(hit) : -1; k >= 0 && k > (hit ? ph.indexOf(hit) - 4 : 0); k--) if (t >= ph[k].start && t < ph[k].end) return ph[k].type;
    return null;
  };
  const dayFloor = new Map<number, number>();
  const floorAt = (t: number) => {
    const d = Math.floor(t / 86400);
    if (!dayFloor.has(d)) {
      const w = hr.filter((x) => x.t >= t - 7 * 86400 && x.t < t + 86400).map((x) => x.v);
      dayFloor.set(d, pct(w.length >= 36 ? w : hr.map((x) => x.v), 0.1));
    }
    return dayFloor.get(d)!;
  };
  const raw = hr.map((x) => {
    const ty = typeAt(x.t);
    if (ty && ty !== 'still' && ty !== 'unknown') return 0;
    const f = floorAt(x.t);
    return x.v <= f + Math.max(10, 0.15 * f) || (ty === 'still' && x.v <= f + Math.max(16, 0.25 * f)) ? 1 : 0;
  });
  const sm = raw.map((_, i) => median(raw.slice(Math.max(0, i - 1), i + 2)));
  // runs of asleep-like samples, bridging gaps ≤ 30 min
  const runs: [number, number][] = [];
  let s0 = -1, last = -1;
  for (let i = 0; i < hr.length; i++) {
    if (!sm[i]) continue;
    if (s0 < 0 || hr[i].t - hr[last].t > 1800) { if (s0 >= 0) runs.push([s0, last]); s0 = i; }
    last = i;
  }
  if (s0 >= 0) runs.push([s0, last]);
  const out: Night[] = [];
  for (const [i0, i1] of runs) {
    const t0 = hr[i0].t, t1 = hr[i1].t + 300, dur = t1 - t0;
    if (dur < 30 * 60) continue;
    const mid = new Date(((t0 + t1) / 2) * 1000).getHours();
    if (dur < 3 * 3600) {
      if (mid < 10 || mid >= 20) continue;                      // short night-time runs are fragments, not naps
      const day = hr.filter((x) => Math.abs(x.t - (t0 + t1) / 2) < 6 * 3600).map((x) => x.v);
      const inRun = hr.slice(i0, i1 + 1).map((x) => x.v);
      if (!day.length || median(inRun) > 0.92 * median(day)) continue;   // no real HR dip → resting, not napping
      // and the phone must corroborate: lying still for most of it (a ring-only daytime dip is too often a sofa)
      const pts = hr.slice(i0, i1 + 1).map((x) => typeAt(x.t));
      if (pts.filter((ty) => ty === 'still').length < 0.8 * pts.length) continue;
    }
    const nEpoch = Math.ceil((t1 - t0) / EPOCH);
    // full nights (≥ 3 h) get the coarse cardiac stage estimate; shorter naps stay asleep/awake only
    const isFullNight = dur >= 3 * 3600;
    let grid: number[];
    if (isFullNight) {
      const asleep = hr.slice(i0, i1 + 1).map((x, k) => ({ x, k })).filter(({ k }) => sm[i0 + k])
        .map(({ x }) => ({ t: x.t, v: x.v, still: typeAt(x.t) === 'still' || typeAt(x.t) === null }));
      grid = ringStageGrid(asleep, t0, nEpoch);
      hr.slice(i0, i1 + 1).forEach((x, k) => { if (!sm[i0 + k]) for (let e = 0; e < 10; e++) { const j = Math.floor((x.t - t0) / EPOCH) + e; if (j >= 0 && j < grid.length) grid[j] = 0; } });
    } else {
      grid = new Array(nEpoch).fill(4);
      hr.slice(i0, i1 + 1).forEach((x, k) => {
        if (sm[i0 + k]) return;
        for (let e = 0; e < 10; e++) { const j = Math.floor((x.t - t0) / EPOCH) + e; if (j < grid.length) grid[j] = 0; }
      });
    }
    const sumr = summarise(grid, t0, isFullNight);
    if (!sumr) continue;
    out.push({ ...sumr, onsetMin: undefined, id: `ring-${Math.round(t0)}`, date: localDate(sumr.end), hr5: [], hrv5: [], events: [],
      source: 'ring', sourceName: isFullNight ? 'Telomy ring · heart-rate stage estimate' : 'Telomy ring', ...(isFullNight ? { stageConfidence: 'low' as const } : {}) });
  }
  return out;
}

// ------------------------------------------------------------------ fusion

const overlap = (a: Night, b: Night) => Math.max(0, Math.min(a.end, b.end) - Math.max(a.start, b.start)) / Math.max(1, Math.min(a.end - a.start, b.end - b.start));

/** Parts of `n` (≥ 30 min, with ≥ 20 min asleep) not covered by any already-chosen night. */
function uncovered(n: Night, chosen: Night[]): Night[] {
  const grid = n.stages?.length ? n.stages : n.hypnogram.map((h) => (h ? 4 : 0));
  const covered = (t: number) => chosen.some((c) => t >= c.start && t < c.end);
  const out: Night[] = [];
  let i = 0;
  while (i < grid.length) {
    if (covered(n.start + i * EPOCH)) { i++; continue; }
    let j = i;
    while (j < grid.length && !covered(n.start + j * EPOCH)) j++;
    const g = grid.slice(i, j);
    if (g.length >= 60 && g.filter((s) => s > 0).length >= 40) {
      const sm = summarise(g, n.start + i * EPOCH, !!n.stages?.length);
      if (sm) out.push({ ...n, ...sm, onsetMin: undefined, id: `${n.id}@${i}`, date: localDate(sm.end), hr5: [], hrv5: [], events: [] });
    }
    i = j;
  }
  return out;
}

/** One night per sleep period: patch > WHOOP > Watch > ring's own sleep > ring HR > other Health; ring HR/HRV filled into nights that lack it. */
export function fuseNights(patch: Night[], health: Night[], ring: RingHistorySample[], phone: PhoneActivity[], whoop: Night[] = [], ringOwn: Night[] = []): Night[] {
  const ringOnly = ringNights(ring, phone);
  const order: Night[] = [
    ...patch.map((n) => ({ ...n, source: 'patch' as const, sourceName: 'Telomy patch', hrvSrc: n.hrvSrc ?? ('ecg' as const) })),
    ...whoop, ...health.filter((n) => n.source === 'watch'), ...ringOwn, ...ringOnly, ...health.filter((n) => n.source !== 'watch'),
  ];
  const chosen: Night[] = [];
  for (const n of order) {
    if (!chosen.some((c) => overlap(c, n) > 0.3)) { chosen.push(n); continue; }
    // a lower-priority device that covered MORE of the night: keep the part the better device missed
    // (2026-10-18: the patch stopped early while WHOOP/ring showed ~4 more hours of sleep → that tail is kept and merged)
    for (const piece of uncovered(n, chosen)) chosen.push(piece);
  }
  const fused = chosen.map((n) => {
    if (n.source === 'patch' && n.sleepRmssd && n.lowestHr) return n;
    const o = ringOverlay(n, ring, dayHrBefore(n.start, ring));
    const fill: Partial<Night> = {};
    for (const k of Object.keys(o) as (keyof Night)[]) if ((n as any)[k] == null || (Array.isArray((n as any)[k]) && !(n as any)[k].length)) (fill as any)[k] = (o as any)[k];
    return { ...n, ...fill };
  }).sort((a, b) => a.end - b.end);
  return mergeFragments(fused);
}

/**
 * Join pieces of one sleep period (gap < 90 min) into a single night, like NOOP's bridged nights. 2026-10-18 showed
 * a patch night that stopped early and the rest of the night as a separate piece, so the app displayed
 * only the last fragment. The gap between pieces is "no data" (-1): never counted as sleep or as wake.
 */
export function mergeFragments(nights: Night[]): Night[] {
  const out: Night[] = [];
  for (const n of [...nights].sort((a, b) => a.start - b.start)) {
    const p = out[out.length - 1];
    if (!p || n.start - p.end >= 90 * 60) { out.push(n); continue; }
    const grid = (x: Night) => (x.stages?.length ? x.stages.map((s) => s) : x.hypnogram.map((h) => (h ? 4 : 0)));
    const a = grid(p), b = grid(n);
    const gap = Math.max(0, Math.round((n.start - (p.start + a.length * EPOCH)) / EPOCH));
    const staged = !!(p.stages?.length && n.stages?.length);
    const g = [...a, ...new Array(gap).fill(-1), ...b].map((s) => (!staged && s > 0 ? 4 : s));
    const sm = summarise(g, p.start, staged);
    if (!sm) { out.push(n); continue; }
    const w = (x?: number, y?: number) => (x != null && y != null ? (x * p.tstMin + y * n.tstMin) / Math.max(1, p.tstMin + n.tstMin) : x ?? y);
    const lo = [p, n].filter((x) => x.lowestHr != null).sort((x, y) => x.lowestHr! - y.lowestHr!)[0];
    out[out.length - 1] = {
      ...p, ...sm, id: `${p.id}+${n.id}`, date: localDate(sm.end), end: Math.max(p.end, n.end),
      onsetMin: p.onsetMin, source: p.tstMin >= n.tstMin ? p.source : n.source,
      sourceName: p.sourceName === n.sourceName ? p.sourceName : `${p.sourceName ?? p.source} + ${n.sourceName ?? n.source}`,
      sleepHr: w(p.sleepHr, n.sleepHr), sleepRmssd: p.hrvSrc === n.hrvSrc ? w(p.sleepRmssd, n.sleepRmssd) : p.sleepRmssd ?? n.sleepRmssd,
      lowestHr: lo?.lowestHr, lowestHrAt: lo?.lowestHrAt,
      ...(p.skinTemp != null ? { skinTemp: p.skinTemp, tempSrc: p.tempSrc } : n.skinTemp != null ? { skinTemp: n.skinTemp, tempSrc: n.tempSrc } : {}), hr5: [...p.hr5, ...n.hr5], hrv5: [...p.hrv5, ...n.hrv5], events: [...p.events, ...n.events],
    };
  }
  return out.sort((a, b) => a.end - b.end);
}

// ------------------------------------------------------------------ need, debt, regularity

export type SleepNeed = {
  needMin: number; baselineMin: number; strainMin: number; debtMin: number; repayMin: number; personal: boolean;
  lastNightPct: number | null;           // last night's sleep as a share of that night's need (WHOOP "sleep performance")
  bedtime: number | null; wake: number | null;   // suggested tonight (unix s) from your usual wake time
};

const strainAdd = (strain: number) => (strain <= 10 ? 0 : strain >= 21 ? 45 : strain <= 14 ? (strain - 10) * 3.75 : strain <= 18 ? 15 + (strain - 14) * 5 : 35 + (strain - 18) * 3.33);

/** `strainByDate`: day strain (0–21) keyed by local date (the day before each night ends). */
export function sleepNeed(allNights: Night[], strainToday: number, strainByDate: Record<string, number> = {}): SleepNeed {
  // ONE main night per calendar day for the debt recurrence: a nap or a split fragment must not count as its own
  // under-slept night (that compounds the debt and blows the need up to 14 h+). Keep the longest sleep per date.
  const byDate = new Map<string, Night>();
  for (const n of allNights) {
    const key = localDate(n.end);
    const cur = byDate.get(key);
    if (!cur || n.tstMin > cur.tstMin) byDate.set(key, n);
  }
  const nights = [...byDate.values()].sort((a, b) => a.end - b.end);
  const recent = nights.slice(-30);
  const personal = recent.length >= 14;
  const longer = [...recent].map((n) => n.tstMin).sort((a, b) => b - a).slice(0, Math.ceil(recent.length / 2));
  const baselineMin = personal ? Math.max(420, Math.min(540, mean(longer))) : 480;
  // Debt recurrence fitted by NOOP on 853 consecutive WHOOP nights (within 15 min of WHOOP's next-day debt on 93 %):
  //   need_n = base + strain + debt_n;  debt_{n+1} = 0.55 · max(0, need_n − slept_n);  < 10 min = balanced.
  // Surplus sleep never banks; only usable nights step the recurrence (a missing night is unknown, not zero sleep).
  let debt = 0, lastNeed = baselineMin;
  for (const n of nights.slice(-14)) {
    const prevDay = localDate(n.start - 6 * 3600);   // the day before the night (a 01:00 bedtime counts as the previous day)
    const need = baselineMin + strainAdd(strainByDate[prevDay] ?? 0) + debt;
    lastNeed = need;
    debt = 0.55 * Math.max(0, need - n.tstMin);
    if (debt < 10) debt = 0;
  }
  const last = nights[nights.length - 1];
  const strainMin = strainAdd(strainToday);
  // repay at most ~2 h of debt in one night (you can't usefully recover 8 h of debt tonight), and cap the night's
  // target at 11 h — a sane upper bound so a run of poor nights never shows an impossible "need 14 h".
  const repayMin = Math.min(debt, 120);
  const needMin = Math.min(660, baselineMin + strainMin + repayMin);
  const wakes = nights.slice(-7).map((n) => { const d = new Date(n.end * 1000); return d.getHours() * 60 + d.getMinutes(); });
  let wake: number | null = null, bedtime: number | null = null;
  if (wakes.length >= 3) {
    const w = median(wakes);
    const t = new Date(); t.setHours(0, 0, 0, 0);
    wake = t.getTime() / 1000 + 86400 + w * 60;
    const latency = median(nights.slice(-7).map((n) => n.onsetMin ?? 15));
    bedtime = wake - (needMin + latency) * 60;
  }
  return { needMin, baselineMin, strainMin, debtMin: debt, repayMin, personal,
    lastNightPct: last ? Math.min(1.2, last.tstMin / lastNeed) : null, bedtime, wake };
}

/** Phillips 2017 SRI from consecutive nights (5-min bins over the 24 h from 18:00); null until 4 day-pairs. */
export function sleepRegularity(nights: Night[]): number | null {
  const byDate = new Map(nights.map((n) => [n.date, n]));
  const mask = (n: Night) => {
    const d = new Date(n.end * 1000); d.setHours(18, 0, 0, 0);
    const a = d.getTime() / 1000 - 86400;
    const m = new Array(288).fill(0);
    n.hypnogram.forEach((h, i) => { if (h) { const j = Math.floor((n.start + i * n.epochSec - a) / 300); if (j >= 0 && j < 288) m[j] = 1; } });
    return m;
  };
  let same = 0, total = 0, pairs = 0;
  for (const n of nights.slice(-8)) {
    const prev = new Date(n.end * 1000 - 86400000);
    const p = byDate.get(localDate(prev.getTime() / 1000));
    if (!p) continue;
    const a = mask(p), b = mask(n);
    for (let i = 0; i < 288; i++) { total++; if (a[i] === b[i]) same++; }
    pairs++;
  }
  return pairs >= 4 ? Math.round(-100 + (200 * same) / total) : null;
}
